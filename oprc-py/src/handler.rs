use std::ops::Deref;

use oprc_pb::{
    oprc_function_server::OprcFunction, InvocationRequest, InvocationResponse,
    ObjectInvocationRequest, ResponseStatus,
};
use pyo3::{intern, types::PyTuple, Py, PyAny, PyRef, PyResult, Python};
use pyo3_async_runtimes::{into_future_with_locals, TaskLocals};
use tonic::{Request, Response, Status};
use tracing::{debug, info};

pub struct InvocationHandler {
    callback: Py<PyAny>,
    task_locals: TaskLocals,
}

impl InvocationHandler {
    pub fn new(callback: Py<PyAny>, locals: TaskLocals) -> Self {
        InvocationHandler {
            callback,
            task_locals: locals,
        }
    }
}

async fn invoke_fn(
    locals: &TaskLocals,
    callback: &Py<PyAny>,
    req: oprc_pb::InvocationRequest,
) -> PyResult<oprc_pb::InvocationResponse> {
    let res = Python::with_gil(|py| {
        let req = crate::model::InvocationRequest::from(req);
        let args = PyTuple::new(py, [req])?;
        let any = into_future_with_locals(
            locals,
            callback
                .call_method1(py, intern!(py, "invoke_fn"), args)?
                .into_bound(py),
        );
        any
    });
    let res = res?.await.map(|any| {
        Python::with_gil(|py| {
            any.extract::<PyRef<crate::model::InvocationResponse>>(py)
                .map(|r| r.deref().into())
        })
    })?;
    res
}

async fn invoke_obj(
    locals: &TaskLocals,
    callback: &Py<PyAny>,
    req: oprc_pb::ObjectInvocationRequest,
) -> PyResult<oprc_pb::InvocationResponse> {
    let res = Python::with_gil(|py| {
        let req = crate::model::ObjectInvocationRequest::from(req);
        let args = PyTuple::new(py, [req])?;
        let any = into_future_with_locals(
            locals,
            callback
                .call_method1(py, intern!(py, "invoke_obj"), args)?
                .into_bound(py),
        );
        any
    });
    let res = res?.await.map(|any| {
        Python::with_gil(|py| {
            any.extract::<PyRef<crate::model::InvocationResponse>>(py)
                .map(|r| r.deref().into())
        })
    })?;
    res
}

#[tonic::async_trait]
impl OprcFunction for InvocationHandler {
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
        match invoke_fn(&self.task_locals, &self.callback, invocation_request).await {
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

        match invoke_obj(&self.task_locals, &self.callback, invocation_request).await {
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
