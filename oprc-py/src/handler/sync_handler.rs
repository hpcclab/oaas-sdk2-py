use std::ops::Deref;

use oprc_invoke::handler::InvocationExecutor;
use oprc_pb::{oprc_function_server::OprcFunction, InvocationRequest, InvocationResponse, ObjectInvocationRequest, ResponseStatus};
use pyo3::{intern, types::PyTuple, Py, PyAny, PyRef, PyResult, Python};
use tonic::{Request, Response, Status};
use tracing::{debug, info};



pub struct SyncInvocationHandler {
    callback: Py<PyAny>,
}

impl SyncInvocationHandler {
    pub fn new(callback: Py<PyAny>) -> Self {
        SyncInvocationHandler {
            callback
        }
    }
}

#[tonic::async_trait]
impl OprcFunction for SyncInvocationHandler {
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
        match invoke_fn(&self.callback, invocation_request).await {
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
                "invoke_obj: {} {} {} {}",
                invocation_request.cls_id,
                invocation_request.partition_id,
                invocation_request.object_id,
                invocation_request.fn_id
            );
        }

        match invoke_obj(&self.callback, invocation_request).await {
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
impl InvocationExecutor for SyncInvocationHandler {
    async fn invoke_fn(
        &self,
        invocation_request: oprc_pb::InvocationRequest,
    ) -> Result<oprc_pb::InvocationResponse, oprc_invoke::OffloadError> {
        if tracing::enabled!(tracing::Level::DEBUG) {
            debug!("invoke_fn: {:?}", invocation_request);
        } else {
            info!(
                "invoke_fn: {} {}",
                invocation_request.cls_id, invocation_request.fn_id
            );
        }
        match invoke_fn(&self.callback, invocation_request).await {
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
        invocation_request: oprc_pb::ObjectInvocationRequest,
    ) -> Result<oprc_pb::InvocationResponse, oprc_invoke::OffloadError> {
        if tracing::enabled!(tracing::Level::DEBUG) {
            debug!("invoke_obj: {:?}", invocation_request);
        } else {
            info!(
                "invoke_obj: {} {} {} {}",
                invocation_request.cls_id,
                invocation_request.partition_id,
                invocation_request.object_id,
                invocation_request.fn_id
            );
        }

        match invoke_obj(&self.callback, invocation_request).await {
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




async fn invoke_obj(
    callback: &Py<PyAny>,
    req: oprc_pb::ObjectInvocationRequest,
) -> PyResult<oprc_pb::InvocationResponse> {
    
    let res = Python::attach(|py| {
        let req = crate::model::ObjectInvocationRequest::from(req);
        let args = PyTuple::new(py, [req])?;
        let any = callback.call_method1(py, intern!(py, "invoke_obj"), args)?;
        any.extract::<PyRef<crate::model::InvocationResponse>>(py)
            .map(|r| r.deref().into())
    
    });

    res
}


async fn invoke_fn(
    callback: &Py<PyAny>,
    req: oprc_pb::InvocationRequest,
) -> PyResult<oprc_pb::InvocationResponse> {
    let res = Python::attach(|py| {
        let req = crate::model::InvocationRequest::from(req);
        let args = PyTuple::new(py, [req])?;
        let any = callback.call_method1(py, intern!(py, "invoke_fn"), args)?;
        any.extract::<PyRef<crate::model::InvocationResponse>>(py)
            .map(|r| r.deref().into())
    
    });
    res
}