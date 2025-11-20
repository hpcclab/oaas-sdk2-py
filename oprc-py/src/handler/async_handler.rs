use std::ops::Deref;

use oprc_invoke::handler::InvocationExecutor;
use oprc_grpc::{
    oprc_function_server::OprcFunction, InvocationRequest, InvocationResponse,
    ObjectInvocationRequest, ResponseStatus,
};
use pyo3::{intern, types::PyTuple, Py, PyAny, PyRef, PyResult, Python, PyErr};
use pyo3_async_runtimes::{into_future_with_locals, TaskLocals};
use tonic::{Request, Response, Status};
use tracing::{debug, info};

pub struct AsyncInvocationHandler {
    callback: Py<PyAny>,
    task_locals: TaskLocals,
}

impl AsyncInvocationHandler {
    pub fn new(callback: Py<PyAny>, locals: TaskLocals) -> Self {
        AsyncInvocationHandler {
            callback,
            task_locals: locals,
        }
    }
}

#[tonic::async_trait]
impl OprcFunction for AsyncInvocationHandler {
    async fn invoke_fn(
        &self,
        request: Request<InvocationRequest>,
    ) -> Result<Response<InvocationResponse>, tonic::Status> {
        let invocation_request = request.into_inner();
        if tracing::enabled!(tracing::Level::DEBUG) {
            debug!("invoke_fn: {:?}", invocation_request);
        } else {
            info!(
                "invoke_fn: {} {}",
                invocation_request.cls_id, invocation_request.fn_id
            );
        }
        match invoke_fn_async(&self.task_locals, &self.callback, invocation_request).await {
            Ok(output) => Ok(Response::new(output)),
            Err(err) => {
                let resp = InvocationResponse {
                    payload: Some(err.to_string().into_bytes()),
                    // payload: None,
                    status: ResponseStatus::AppError as i32,
                    ..Default::default()
                };
                Ok(Response::new(resp))
            }
        }
    }

    async fn invoke_obj(
        &self,
        request: Request<ObjectInvocationRequest>,
    ) -> Result<Response<InvocationResponse>, Status> {
        let invocation_request = request.into_inner();
        if tracing::enabled!(tracing::Level::DEBUG) {
            debug!("invoke_obj: {:?}", invocation_request);
        } else {
            info!(
                "invoke_obj: {} {} {:?} {}",
                invocation_request.cls_id,
                invocation_request.partition_id,
                invocation_request.object_id,
                invocation_request.fn_id
            );
        }

        match invoke_obj_async(&self.task_locals, &self.callback, invocation_request).await {
            Ok(output) => Ok(Response::new(output)),
            Err(err) => {
                let resp = InvocationResponse {
                    payload: Some(err.to_string().into_bytes()),
                    // payload: None,
                    status: ResponseStatus::AppError as i32,
                    ..Default::default()
                };
                Ok(Response::new(resp))
            }
        }
    }
}

#[async_trait::async_trait]
impl InvocationExecutor for AsyncInvocationHandler {
    async fn invoke_fn(
        &self,
    invocation_request: oprc_grpc::InvocationRequest,
    ) -> Result<oprc_grpc::InvocationResponse, oprc_invoke::OffloadError> {
        if tracing::enabled!(tracing::Level::DEBUG) {
            debug!("invoke_fn: {:?}", invocation_request);
        } else {
            info!(
                "invoke_fn: {} {}",
                invocation_request.cls_id, invocation_request.fn_id
            );
        }
        match invoke_fn_async(&self.task_locals, &self.callback, invocation_request).await {
            Ok(output) => Ok(output),
            Err(err) => {
                let resp = InvocationResponse {
                    payload: Some(err.to_string().into_bytes()),
                    // payload: None,
                    status: ResponseStatus::AppError as i32,
                    ..Default::default()
                };
                Ok(resp)
            }
        }
    }
    async fn invoke_obj(
        &self,
    invocation_request: oprc_grpc::ObjectInvocationRequest,
    ) -> Result<oprc_grpc::InvocationResponse, oprc_invoke::OffloadError> {
        if tracing::enabled!(tracing::Level::DEBUG) {
            debug!("invoke_obj: {:?}", invocation_request);
        } else {
            info!(
                "invoke_obj: {} {} {:?} {}",
                invocation_request.cls_id,
                invocation_request.partition_id,
                invocation_request.object_id,
                invocation_request.fn_id
            );
        }

        match invoke_obj_async(&self.task_locals, &self.callback, invocation_request).await {
            Ok(output) => Ok(output),
            Err(err) => {
                let resp = InvocationResponse {
                    payload: Some(err.to_string().into_bytes()),
                    // payload: None,
                    status: ResponseStatus::AppError as i32,
                    ..Default::default()
                };
                Ok(resp)
            }
        }
    }
}


async fn invoke_fn_async(
    locals: &TaskLocals,
    callback: &Py<PyAny>,
    req: oprc_grpc::InvocationRequest,
) -> PyResult<oprc_grpc::InvocationResponse> {
    // Acquire Python future within GIL, then await it, then extract response.
        let fut = Python::attach(|py| {
            let req_model = crate::model::InvocationRequest::from(req.clone());
            let args = PyTuple::new(py, [req_model])?;
            let py_future = callback
                .call_method1(py, intern!(py, "invoke_fn"), args)?
                .into_bound(py);
            into_future_with_locals(locals, py_future)
        })?;
        let any = fut.await?;
        let resp = Python::attach(|py| {
            let resp_ref: PyRef<crate::model::InvocationResponse> = any.extract(py)?;
            Ok::<oprc_grpc::InvocationResponse, PyErr>(resp_ref.deref().into())
        })?;
        Ok(resp)
}

async fn invoke_obj_async(
    locals: &TaskLocals,
    callback: &Py<PyAny>,
    req: oprc_grpc::ObjectInvocationRequest,
) -> PyResult<oprc_grpc::InvocationResponse> {
    let fut = Python::attach(|py| {
        let req_model = crate::model::ObjectInvocationRequest::from(req.clone());
        let args = PyTuple::new(py, [req_model])?;
        let py_future = callback
            .call_method1(py, intern!(py, "invoke_obj"), args)?
            .into_bound(py);
        into_future_with_locals(locals, py_future)
    })?;
    let any = fut.await?;
    let resp = Python::attach(|py| {
        let resp_ref: PyRef<crate::model::InvocationResponse> = any.extract(py)?;
        Ok::<oprc_grpc::InvocationResponse, PyErr>(resp_ref.deref().into())
    })?;
    Ok(resp)
}
