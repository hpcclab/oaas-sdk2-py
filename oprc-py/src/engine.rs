use std::net::{IpAddr, Ipv4Addr, SocketAddr};
use tokio::sync::oneshot;

use crate::{data::DataManager, handler::InvocationHandler, rpc::RpcManager};
pub use envconfig::Envconfig;
use oprc_pb::oprc_function_server::OprcFunctionServer;
use pyo3::{
    exceptions::{PyRuntimeError, PyTypeError},
    prelude::*,
};
use pyo3_async_runtimes::TaskLocals;
use tokio::runtime::Builder;
use tonic::transport::Server;

#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[pyclass]
pub struct OaasEngine {
    #[pyo3(get)]
    data_manager: Py<DataManager>,
    #[pyo3(get)]
    rpc_manager: Py<RpcManager>,
    session: zenoh::Session,
    shutdown_sender: Option<oneshot::Sender<()>>, // Add a shutdown sender
}

#[pyo3_stub_gen::derive::gen_stub_pymethods]
#[pymethods]
impl OaasEngine {
    #[new]
    fn new() -> PyResult<Self> {
        let mut builder = Builder::new_multi_thread();
        builder.enable_all();
        pyo3_async_runtimes::tokio::init(builder);
        let runtime = pyo3_async_runtimes::tokio::get_runtime();
        let conf = oprc_zenoh::OprcZenohConfig::init_from_env()
            .map_err(|e| PyErr::new::<PyTypeError, _>(e.to_string()))?;
        let session = runtime.block_on(async move {
            zenoh::open(conf.create_zenoh()).await.map_err(|e| {
                PyErr::new::<PyRuntimeError, _>(format!("Failed to open zenoh session: {}", e))
            })
        })?;
        let data_manager = Python::with_gil(|py| Py::new(py, DataManager::new(session.clone())))?;
        let rpc_manager = Python::with_gil(|py| Py::new(py, RpcManager::new(session.clone())))?;
        Ok(OaasEngine {
            data_manager,
            rpc_manager,
            session,
            shutdown_sender: None,
        })
    }

    fn serve_grpc_server(&mut self, event_loop: Py<PyAny>, callback: Py<PyAny>) -> PyResult<()> {
        let (shutdown_sender, shutdown_receiver) = oneshot::channel(); // Create a shutdown channel
        self.shutdown_sender = Some(shutdown_sender); // Store the sender for later use

        Python::with_gil(|py| {
            let l = event_loop.into_bound(py);
            let task_locals = TaskLocals::new(l);
            py.allow_threads(|| {
                let service = InvocationHandler::new(callback, task_locals);
                let runtime = pyo3_async_runtimes::tokio::get_runtime();
                runtime.spawn(async move {
                    if let Err(e) = start_tonic(service, shutdown_receiver).await {
                        eprintln!("Server error: {}", e);
                    }
                });
            });
            Ok(())
        })
    }

    fn serve_zenoh(&mut self, event_loop: Py<PyAny>, callback: Py<PyAny>) -> PyResult<()> {
        Python::with_gil(|py| {
            let l = event_loop.into_bound(py);
            let task_locals = TaskLocals::new(l);
            py.allow_threads(|| {
                let service = InvocationHandler::new(callback, task_locals);
                let runtime = pyo3_async_runtimes::tokio::get_runtime();
                let z_session = self.session.clone();
                runtime.spawn(async move {
                    if let Err(e) = start_zenoh(service, z_session).await {
                        eprintln!("Server error: {}", e);
                    }
                });
            });
            Ok(())
        })
    }

    fn stop_server(&mut self) -> PyResult<()> {
        if let Some(sender) = self.shutdown_sender.take() {
            let _ = sender.send(());
        }
        Ok(())
    }
}

// Modify the start function to accept a shutdown receiver
async fn start_tonic(
    service: InvocationHandler,
    mut shutdown_receiver: oneshot::Receiver<()>,
) -> PyResult<()> {
    let socket = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(0, 0, 0, 0)), 8080);
    let echo_function: OprcFunctionServer<InvocationHandler> = OprcFunctionServer::new(service);
    Server::builder()
        .add_service(echo_function.max_decoding_message_size(usize::MAX))
        .serve_with_shutdown(socket, async {
            tokio::select! {
                _ = shutdown_signal() => {},
                _ = &mut shutdown_receiver => {}, // Wait for the shutdown signal
            }
        })
        .await
        .map_err(|e| PyErr::new::<PyTypeError, _>(e.to_string()))?;
    Ok(())
}

async fn start_zenoh(
    service: InvocationHandler,
    z_session: zenoh::Session,
) -> PyResult<()> {
    todo!()    
}



async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }
}

// #[pyo3_stub_gen::derive::gen_stub_pyclass]
// #[pyclass]
// pub struct OaasSession{
//     #[pyo3(get)]
//     data_manager: Py<DataManager>,
//     local: HashMap<model::ObjectMetadata, Py<ObjectData>>,
//     remote: HashMap<model::ObjectMetadata, Py<ObjectData>>,
// }

// impl OaasSession {
//     pub fn new(data_manager: Py<DataManager>) -> Self {
//         OaasSession { data_manager, local: HashMap::new(), remote: HashMap::new() }
//     }
// }

// #[pyo3_stub_gen::derive::gen_stub_pymethods]
// #[pymethods]
// impl OaasSession {
//     pub async fn get_object(&mut self, meta: model::ObjectMetadata) -> PyResult<Py<PyAny>> {
//         Python::with_gil(|py| {
//             if let Some(object) = self.local.get(&meta) {
//                 return Ok(object.clone_ref(py).into_any());
//             }
//             if let Some(object) = self.remote.get(&meta) {
//                 return Ok(object.clone_ref(py).into_any());
//             }
//             // TODO : get from remote
//             Ok(py.None())
//         })
//     }

    

//     pub fn set_obj(&mut self, obj: Bound<ObjectData>) -> PyResult<()> {
//         let mut obj_ref = obj.borrow_mut();
//         obj_ref.dirty = true;
//         if obj_ref.remote {
//             self.remote.insert(obj_ref.meta.clone(), obj.clone().unbind());
//         } else {
//             self.local.insert(obj_ref.meta.clone(), obj.clone().unbind());
//         }
//         Ok(())
//     }

//     pub async fn commit(&self) -> PyResult<()> {
//         todo!()
//     }
// }