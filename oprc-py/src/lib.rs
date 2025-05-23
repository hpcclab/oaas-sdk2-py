use pyo3::prelude::*;
mod engine;
mod handler;
mod model;
mod data;
mod rpc;
use engine::OaasEngine;
use tracing_subscriber::util::SubscriberInitExt;

#[pyfunction]
#[pyo3_stub_gen::derive::gen_stub_pyfunction]
#[pyo3(signature=(level="info", raise_error=false))]
fn init_logger(level: &str, raise_error: bool) -> PyResult<()> {
    let r = tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::new(level.to_string()))
        // .with_target(false)
        // .compact()
        .with_ansi(true)
        // .with_line_number(true)
        // .with_file(true)
        .with_span_events(tracing_subscriber::fmt::format::FmtSpan::CLOSE)
        .with_timer(tracing_subscriber::fmt::time::time())
        // .with_thread_names(true)
        // .with_thread_ids(true)
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
    m.add_class::<OaasEngine>()?;
    m.add_class::<data::DataManager>()?;
    m.add_class::<rpc::RpcManager>()?;
    m.add_class::<model::InvocationRequest>()?;
    m.add_class::<model::InvocationResponseCode>()?;
    m.add_class::<model::InvocationResponse>()?;
    m.add_class::<model::ObjectInvocationRequest>()?;
    m.add_class::<model::ObjectMetadata>()?; 
    m.add_class::<model::ObjectData>()?;  
    m.add_class::<model::PyObjectEvent>()?; 
    m.add_class::<model::PyTriggerTarget>()?; 
    m.add_class::<model::FnTriggerType>()?; 
    m.add_class::<model::DataTriggerType>()?; 
    Ok(())
}


pyo3_stub_gen::define_stub_info_gatherer!(stub_info);
