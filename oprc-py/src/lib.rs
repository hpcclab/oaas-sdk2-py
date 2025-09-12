use pyo3::prelude::*;
mod engine;
mod handler;
mod model;
mod data;
mod rpc;
mod obj;
mod telemetry;
use engine::OaasEngine;
use tracing_subscriber::util::SubscriberInitExt;

#[pyfunction]
#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyfunction)]
#[pyo3(signature=(level="info", raise_error=false))]
fn init_logger(level: &str, raise_error: bool) -> PyResult<()> {
    let r = tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::new(level.to_string()))
        .with_ansi(true)
        .with_span_events(tracing_subscriber::fmt::format::FmtSpan::CLOSE)
        .with_timer(tracing_subscriber::fmt::time::time())
        .with_writer(std::io::stderr)
        .finish()
        .try_init();
    tracing::info!("Initialized tracing with level: {}", level);
    if raise_error{
        r.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to initialize tracing: {}", e)))?;
    } else {
        if let Err(e) = r {
            eprintln!("Failed to initialize tracing: {}", e);
        }
    }
    Ok(())
}

/// A Python module implemented in Rust.
#[pymodule(gil_used = false)]
fn oprc_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(init_logger, m)?)?;
    // Telemetry helpers
    #[pyfunction]
    fn init_telemetry_py(service_name: Option<String>, service_version: Option<String>) {
        telemetry::init_telemetry(service_name, service_version);
    }
    #[pyfunction]
    fn forward_log_py(level: u32, message: String, module: Option<String>, line: Option<u32>, thread: Option<String>) {
        telemetry::forward_log(level, message, module, line, thread);
    }
    m.add_function(wrap_pyfunction!(init_telemetry_py, m)?)?;
    m.add_function(wrap_pyfunction!(forward_log_py, m)?)?;
    m.add_class::<OaasEngine>()?;
    m.add_class::<data::DataManager>()?;
    m.add_class::<rpc::RpcManager>()?;
    m.add_class::<model::InvocationRequest>()?;
    m.add_class::<model::InvocationResponseCode>()?;
    m.add_class::<model::InvocationResponse>()?;
    m.add_class::<model::ObjectInvocationRequest>()?;
    m.add_class::<obj::ObjectMetadata>()?; 
    m.add_class::<obj::ObjectData>()?;  
    m.add_class::<obj::PyObjectEvent>()?; 
    m.add_class::<obj::PyTriggerTarget>()?; 
    m.add_class::<obj::FnTriggerType>()?; 
    m.add_class::<obj::DataTriggerType>()?; 
    Ok(())
}


#[cfg(feature = "stub-gen")]
pyo3_stub_gen::define_stub_info_gatherer!(stub_info);
