use oprc_invoke::proxy::ObjectProxy;
use pyo3::{exceptions::PyRuntimeError, Py, PyResult, Python};
use crate::telemetry;

use crate::model::{InvocationRequest, InvocationResponse, ObjectInvocationRequest};

/// Manages RPC invocations using an ObjectProxy.
#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyo3::pyclass]
pub struct RpcManager {
    proxy: ObjectProxy,
}

impl RpcManager {
    /// Creates a new RpcManager with a Zenoh session.
    pub fn new(z_session: zenoh::Session) -> Self {
        RpcManager {
            proxy: ObjectProxy::new(z_session),
        }
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl RpcManager {
    /// Invokes a function based on the provided InvocationRequest. (Synchronous)
    ///
    /// # Arguments
    ///
    /// * `py`: The Python GIL token.
    /// * `req`: A Python `InvocationRequest` instance.
    ///
    /// # Returns
    ///
    /// A `PyResult` containing an `InvocationResponse`.
    pub fn invoke_fn(&self, py: Python<'_>, req: Py<InvocationRequest>) -> PyResult<InvocationResponse> {
        let proxy = self.proxy.clone();
        let runtime = pyo3_async_runtimes::tokio::get_runtime();
        let proto_req = {
            let req_bound = req.into_bound(py);
            let req_borrowed = req_bound.borrow();
            req_borrowed.into_proto()
        };

    py.detach(move || {
            runtime.block_on(async move {
                telemetry::instrument(async { proxy.invoke_fn_with_req(&proto_req).await }, "rpc.invoke_fn").await
            })
        })
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
        .map(|resp| InvocationResponse::from(resp))
    }

    /// Invokes a function based on the provided InvocationRequest. (Asynchronous)
    ///
    /// # Arguments
    ///
    /// * `req`: A Python `InvocationRequest` instance.
    ///
    /// # Returns
    ///
    /// A `PyResult` containing an `InvocationResponse`.
    pub async fn invoke_fn_async(&self, req: Py<InvocationRequest>) -> PyResult<InvocationResponse> {
    let proto_req = Python::attach(|py| {
            let req = req.into_bound(py);
            let req = req.borrow();
            req.into_proto()
        });
    let result = telemetry::instrument(self.proxy.invoke_fn_with_req(&proto_req), "rpc.invoke_fn_async").await;
        result
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
            .map(|resp| InvocationResponse::from(resp))
    }

    /// Invokes an object method based on the provided ObjectInvocationRequest. (Synchronous)
    ///
    /// # Arguments
    ///
    /// * `py`: The Python GIL token.
    /// * `req`: A Python `ObjectInvocationRequest` instance.
    ///
    /// # Returns
    ///
    /// A `PyResult` containing an `InvocationResponse`.
    pub fn invoke_obj(
        &self,
        py: Python<'_>,
        req: Py<ObjectInvocationRequest>,
    ) -> PyResult<InvocationResponse> {
        let proxy = self.proxy.clone();
        let runtime = pyo3_async_runtimes::tokio::get_runtime();
        let proto_req = {
            let req_bound = req.into_bound(py);
            let req_borrowed = req_bound.borrow();
            req_borrowed.into_proto()
        };

    py.detach(move || {
            runtime.block_on(async move {
                telemetry::instrument(async { proxy.invoke_obj_with_req(&proto_req).await }, "rpc.invoke_obj").await
            })
        })
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
        .map(|resp| InvocationResponse::from(resp))
    }

    /// Invokes an object method based on the provided ObjectInvocationRequest. (Asynchronous)
    ///
    /// # Arguments
    ///
    /// * `req`: A Python `ObjectInvocationRequest` instance.
    ///
    /// # Returns
    ///
    /// A `PyResult` containing an `InvocationResponse`.
    pub async fn invoke_obj_async(
        &self,
        req: Py<ObjectInvocationRequest>,
    ) -> PyResult<InvocationResponse> {
    let proto_req = Python::attach(|py| {
            let req = req.into_bound(py);
            let req = req.borrow();
            req.into_proto()
        });
    let result = telemetry::instrument(self.proxy.invoke_obj_with_req(&proto_req), "rpc.invoke_obj_async").await;
        result
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
            .map(|resp| InvocationResponse::from(resp))
    }
}
