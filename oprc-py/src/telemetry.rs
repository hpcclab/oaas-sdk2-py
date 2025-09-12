#![allow(unused)]
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

static ENABLED: AtomicBool = AtomicBool::new(false);

#[cfg(feature = "telemetry")]
mod impls {
    use super::ENABLED;
    use opentelemetry::KeyValue;
    use opentelemetry::trace::TracerProvider as _;
    use opentelemetry_otlp::{WithExportConfig, WithHttpConfig};
    use opentelemetry_sdk::{
        Resource,
        runtime::Tokio,
        trace::{self, Sampler, SdkTracerProvider},
    };
    use opentelemetry_semantic_conventions::resource::{SERVICE_NAME, SERVICE_VERSION};
    use pyo3_async_runtimes::tokio::get_runtime;
    use std::sync::atomic::Ordering;
    use tracing_opentelemetry::OpenTelemetryLayer;
    use tracing_subscriber::{EnvFilter, Registry, layer::SubscriberExt};

    fn build_sampler() -> Sampler {
        if let Ok(kind) = std::env::var("OTEL_TRACES_SAMPLER") {
            match kind.as_str() {
                "always_off" => Sampler::AlwaysOff,
                "always_on" => Sampler::AlwaysOn,
                "parentbased_always_on" => Sampler::ParentBased(Box::new(Sampler::AlwaysOn)),
                "parentbased_always_off" => Sampler::ParentBased(Box::new(Sampler::AlwaysOff)),
                "traceidratio" => {
                    let arg = std::env::var("OTEL_TRACES_SAMPLER_ARG")
                        .ok()
                        .and_then(|v| v.parse::<f64>().ok())
                        .unwrap_or(1.0);
                    Sampler::TraceIdRatioBased(arg)
                }
                _ => Sampler::ParentBased(Box::new(Sampler::AlwaysOn)),
            }
        } else {
            Sampler::ParentBased(Box::new(Sampler::AlwaysOn))
        }
    }

    pub fn init(service_name_override: Option<String>, service_version: Option<String>) {
        if ENABLED.swap(true, Ordering::SeqCst) {
            return;
        }

        let has_runtime = tokio::runtime::Handle::try_current().is_ok();
        if has_runtime {
            init_inner(service_name_override, service_version, false);
        } else {
            // Create a lightweight ephemeral runtime so exporter build (reqwest client etc.) does not panic.
            match tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
            {
                Ok(rt) => {
                    rt.block_on(async {
                        init_inner(service_name_override, service_version, false);
                    });
                }
                Err(err) => {
                    eprintln!(
                        "[telemetry] Failed to create ephemeral runtime for telemetry init ({}).",
                        err
                    );
                }
            }
        }
    }

    use std::sync::Mutex as StdMutex;
    static PROVIDER: StdMutex<Option<SdkTracerProvider>> = StdMutex::new(None);

    fn init_inner(
        service_name_override: Option<String>,
        service_version: Option<String>,
        ephemeral: bool,
    ) {
        let endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT").ok();
        let svc_name = service_name_override
            .or_else(|| std::env::var("OTEL_SERVICE_NAME").ok())
            .unwrap_or_else(|| "unknown_service:oaas".to_string());
        let svc_version = service_version.unwrap_or_else(|| env!("CARGO_PKG_VERSION").to_string());

        let resource = Resource::builder()
            .with_attribute(KeyValue::new(SERVICE_NAME, svc_name.clone()))
            .with_attribute(KeyValue::new(SERVICE_VERSION, svc_version.clone()))
            .build();

        let tracer_provider = {
            let mut builder = SdkTracerProvider::builder()
                .with_resource(resource)
                .with_sampler(build_sampler());
            if let Some(ep) = endpoint.clone() {
                let use_grpc = matches!(
                    std::env::var("OTEL_EXPORTER_OTLP_PROTOCOL").ok().as_deref(),
                    Some("grpc")
                );
                let exporter_result = if use_grpc {
                    opentelemetry_otlp::SpanExporter::builder()
                        .with_tonic()
                        .with_endpoint(ep.clone())
                        .build()
                } else {
                    opentelemetry_otlp::SpanExporter::builder()
                        .with_http()
                        .with_endpoint(ep.clone())
                        .build()
                };
                match exporter_result {
                    Ok(exporter) => {
                        if ephemeral {
                            // Cannot safely spawn background tasks; fall back to simple exporter.
                            builder = builder.with_simple_exporter(exporter);
                            eprintln!(
                                "[telemetry] Ephemeral runtime used; simple exporter configured."
                            );
                        } else {
                            builder = builder.with_batch_exporter(exporter);
                        }
                    }
                    Err(err) => eprintln!(
                        "[telemetry] Failed to build OTLP exporter ({}). Proceeding without remote export.",
                        err
                    ),
                }
            }
            builder.build()
        };
        let tracer = tracer_provider.tracer("oprc-py");
        let otel_layer = OpenTelemetryLayer::new(tracer);
        let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
        let fmt_layer = tracing_subscriber::fmt::layer().with_target(false);
        let subscriber = Registry::default()
            .with(filter)
            .with(fmt_layer)
            .with(otel_layer);
        let _ = tracing::subscriber::set_global_default(subscriber);
        opentelemetry::global::set_tracer_provider(tracer_provider.clone());
        *PROVIDER.lock().unwrap() = Some(tracer_provider);
    }

    pub fn forward_log(
        level: u32,
        message: String,
        module: Option<String>,
        line: Option<u32>,
        thread: Option<String>,
    ) {
        if !ENABLED.load(Ordering::Relaxed) {
            return;
        }
        let m = module.unwrap_or_default();
        let t = thread.unwrap_or_default();
        let ln = line.unwrap_or(0);
        match level {
            10 => {
                tracing::trace!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message)
            }
            20 => {
                tracing::debug!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message)
            }
            30 => {
                tracing::info!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message)
            }
            40 => {
                tracing::warn!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message)
            }
            _ => {
                tracing::error!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message)
            }
        }
    }

    use std::future::Future;
    use tracing::{Instrument, Span};
    pub fn instrument<F>(fut: F, name: &'static str) -> impl Future<Output = F::Output>
    where
        F: Future + Send,
    {
        // Create span dynamically; tracing::span allows non-const name.
        let span: Span = tracing::span!(tracing::Level::INFO, "dynamic", otel.name = name);
        fut.instrument(span)
    }

    // upgrade function removed; always batch when endpoint + runtime available

    pub fn shutdown() {
        if !ENABLED.load(Ordering::Relaxed) { return; }
        let provider = {
            let mut guard = PROVIDER.lock().unwrap();
            guard.take()
        };
        if let Some(p) = provider {
            if let Err(e) = p.shutdown() {
                eprintln!("[telemetry] shutdown error: {:?}", e);
            }
        }
    }
}

#[cfg(not(feature = "telemetry"))]
mod impls {
    pub fn init(_service_name_override: Option<String>, _service_version: Option<String>) {}
    pub fn forward_log(
        _level: u32,
        _message: String,
        _module: Option<String>,
        _line: Option<u32>,
        _thread: Option<String>,
    ) {
    }
    pub fn instrument<F>(fut: F, _name: &'static str) -> F {
        fut
    }
    pub fn upgrade_batch_if_runtime() {}
    pub fn shutdown() {}
}

pub use impls::*;

pub fn enabled() -> bool {
    ENABLED.load(std::sync::atomic::Ordering::Relaxed)
}

// upgrade no-op wrapper retained for compatibility but does nothing now
pub fn upgrade_batch_if_runtime() {}

pub fn shutdown() { impls::shutdown(); }
