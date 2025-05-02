use pyo3::prelude::*;
mod engine;
mod handler;
mod model;
mod data;
use engine::OaasEngine;


#[pyfunction]
#[pyo3_stub_gen::derive::gen_stub_pyfunction]
fn rust_sleep(py: Python) -> PyResult<Bound<PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async {
        tokio::time::sleep(std::time::Duration::from_secs(1)).await;
        Ok(())
    })
}

#[pyfunction]
#[pyo3_stub_gen::derive::gen_stub_pyfunction]
async fn try_callback(callback: Py<PyAny>) -> PyResult<Py<PyAny>> {
    let res= Python::with_gil(|py| {
        pyo3_async_runtimes::tokio::into_future(callback.call0(py)?.into_bound(py))
    })?;
    res.await
}

#[pyfunction]
#[pyo3_stub_gen::derive::gen_stub_pyfunction]
fn init_logger() {
    let _ = tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .try_init();
}

/// A Python module implemented in Rust.
#[pymodule(gil_used = false)]
fn oprc_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rust_sleep, m)?)?;
    m.add_function(wrap_pyfunction!(try_callback, m)?)?;
    m.add_function(wrap_pyfunction!(init_logger, m)?)?;
    m.add_class::<OaasEngine>()?;
    m.add_class::<data::DataManager>()?;
    m.add_class::<model::InvocationRequest>()?;
    m.add_class::<model::InvocationResponse>()?;
    m.add_class::<model::ObjectInvocationRequest>()?;
    m.add_class::<model::ObjectMetadata>()?; 
    m.add_class::<model::ObjectData>()?; 
    Ok(())
}


pyo3_stub_gen::define_stub_info_gatherer!(stub_info);
