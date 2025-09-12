#![allow(unused)]
#[cfg(feature = "telemetry")]
use std::sync::atomic::{AtomicBool, Ordering};
#[cfg(feature = "telemetry")]
use std::time::Duration;

#[cfg(feature = "telemetry")]
use opentelemetry::{KeyValue};
#[cfg(feature = "telemetry")]
use opentelemetry_sdk::{runtime::Tokio, Resource};
#[cfg(feature = "telemetry")]
use opentelemetry_sdk::trace::{self, Sampler, SdkTracerProvider};
#[cfg(feature = "telemetry")]
use opentelemetry_otlp::WithExportConfig;
#[cfg(feature = "telemetry")]
use opentelemetry_semantic_conventions::resource::{SERVICE_NAME, SERVICE_VERSION};
#[cfg(feature = "telemetry")]
use opentelemetry::trace::TracerProvider as _; // bring trait into scope
#[cfg(feature = "telemetry")]
use tracing_opentelemetry::OpenTelemetryLayer;
#[cfg(feature = "telemetry")]
use tracing_subscriber::{layer::SubscriberExt, Registry, EnvFilter};

#[cfg(feature = "telemetry")]
static ENABLED: AtomicBool = AtomicBool::new(false);

#[cfg(feature = "telemetry")]
fn build_sampler() -> Sampler {
    // Basic env-driven sampler: OTEL_TRACES_SAMPLER, OTEL_TRACES_SAMPLER_ARG
    if let Ok(kind) = std::env::var("OTEL_TRACES_SAMPLER") {        
        match kind.as_str() {
            "always_off" => Sampler::AlwaysOff,
            "always_on" => Sampler::AlwaysOn,
            "parentbased_always_on" => Sampler::ParentBased(Box::new(Sampler::AlwaysOn)),
            "parentbased_always_off" => Sampler::ParentBased(Box::new(Sampler::AlwaysOff)),
            "traceidratio" => {
                let arg = std::env::var("OTEL_TRACES_SAMPLER_ARG").ok().and_then(|v| v.parse::<f64>().ok()).unwrap_or(1.0);
                Sampler::TraceIdRatioBased(arg)
            }
            _ => Sampler::ParentBased(Box::new(Sampler::AlwaysOn))
        }
    } else {
        Sampler::ParentBased(Box::new(Sampler::AlwaysOn))
    }
}

#[cfg(feature = "telemetry")]
pub fn init_telemetry(service_name_override: Option<String>, service_version: Option<String>) {
    if ENABLED.swap(true, Ordering::SeqCst) { return; }

    let endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT").ok();
    let svc_name = service_name_override
        .or_else(|| std::env::var("OTEL_SERVICE_NAME").ok())
        .unwrap_or_else(|| "unknown_service:oaas".to_string());
    let svc_version = service_version.unwrap_or_else(|| env!("CARGO_PKG_VERSION").to_string());

    let resource = Resource::builder()
        .with_attribute(KeyValue::new(SERVICE_NAME, svc_name.clone()))
        .with_attribute(KeyValue::new(SERVICE_VERSION, svc_version))
        .build();

    // Tracer provider
    let tracer_provider = {
        let mut builder = SdkTracerProvider::builder()
            .with_resource(resource)
            .with_sampler(build_sampler());
        if let Some(ep) = endpoint.clone() {
            let exporter = opentelemetry_otlp::SpanExporter::builder()
                .with_http()
                .with_endpoint(ep)
                .build()
                .expect("otlp span exporter");
            builder = builder.with_batch_exporter(exporter);
        }
        builder.build()
    };
    let tracer = tracer_provider.tracer("oprc-py");
    let otel_layer = OpenTelemetryLayer::new(tracer);

    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    let fmt_layer = tracing_subscriber::fmt::layer().with_target(false);

    let subscriber = Registry::default().with(filter).with(fmt_layer).with(otel_layer);
    if tracing::subscriber::set_global_default(subscriber).is_err() {
        // already set; ignore
    }

    opentelemetry::global::set_tracer_provider(tracer_provider);
}

#[cfg(feature = "telemetry")]
pub fn forward_log(level: u32, message: String, module: Option<String>, line: Option<u32>, thread: Option<String>) {
    use tracing::Level;
    if !ENABLED.load(Ordering::Relaxed) { return; }
    let m = module.unwrap_or_default();
    let t = thread.unwrap_or_default();
    let ln = line.unwrap_or(0);
    match level {
        10 => tracing::trace!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message),
        20 => tracing::debug!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message),
        30 => tracing::info!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message),
        40 => tracing::warn!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message),
        _ => tracing::error!(otel.name="python.log", python.module=%m, python.line=ln, python.thread=%t, message=%message),
    }
}

#[cfg(not(feature = "telemetry"))]
pub fn init_telemetry(_service_name_override: Option<String>, _service_version: Option<String>) {}
#[cfg(not(feature = "telemetry"))]
pub fn forward_log(_level: u32, _message: String, _module: Option<String>, _line: Option<u32>, _thread: Option<String>) {}
