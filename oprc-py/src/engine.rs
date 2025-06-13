use flume::Receiver;
use oprc_invoke::handler::InvocationZenohHandler;
use std::{
    collections::HashMap,
    net::{IpAddr, Ipv4Addr, SocketAddr},
    sync::Arc,
};
use tokio::sync::{oneshot, Mutex};
use zenoh::query::{Query, Queryable};

use crate::{
    data::DataManager,
    handler::{AsyncInvocationHandler, SyncInvocationHandler},
    rpc::RpcManager,
};
pub use envconfig::Envconfig;
use oprc_pb::oprc_function_server::{OprcFunction, OprcFunctionServer};
use pyo3::{
    exceptions::{PyRuntimeError, PyTypeError},
    prelude::*,
};
use pyo3_async_runtimes::{tokio::get_runtime, TaskLocals};
use tokio::runtime::Builder;
use tonic::transport::Server;

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyclass]
/// Represents the OaasEngine, which manages data, RPC, and Zenoh sessions.
pub struct OaasEngine {
    #[pyo3(get)]
    data_manager: Py<DataManager>,
    #[pyo3(get)]
    rpc_manager: Py<RpcManager>,
    session: zenoh::Session,
    shutdown_sender: Option<oneshot::Sender<()>>, // Add a shutdown sender
    queryable_table: Arc<Mutex<HashMap<String, Queryable<Receiver<Query>>>>>,
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pymethods]
impl OaasEngine {
    #[new]
    /// Creates a new instance of OaasEngine.
    /// Initializes the Tokio runtime, Zenoh session, DataManager, and RpcManager.
    fn new() -> PyResult<Self> {
        let mut builder = Builder::new_multi_thread();
        builder.enable_all();
        pyo3_async_runtimes::tokio::init(builder);
        let runtime = get_runtime();
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
            queryable_table: Arc::new(Mutex::new(HashMap::new())),
        })
    }

    /// Starts a gRPC server on the specified port.
    ///
    /// # Arguments
    ///
    /// * `port` - The port number to bind the gRPC server to.
    /// * `event_loop` - The Python event loop.
    /// * `callback` - The Python callback function to handle invocations.
    fn serve_grpc_server_async(
        &mut self,
        port: u16,
        event_loop: Py<PyAny>,
        callback: Py<PyAny>,
    ) -> PyResult<()> {
        let (shutdown_sender, shutdown_receiver) = oneshot::channel(); // Create a shutdown channel
        self.shutdown_sender = Some(shutdown_sender); // Store the sender for later use

        Python::with_gil(|py| {
            let l = event_loop.into_bound(py);
            let task_locals = TaskLocals::new(l);
            py.allow_threads(|| {
                let service = AsyncInvocationHandler::new(callback, task_locals);
                let runtime = get_runtime();
                runtime.spawn(async move {
                    if let Err(e) = start_tonic(port, service, shutdown_receiver).await {
                        eprintln!("Server error: {}", e);
                    }
                });
            });
            Ok(())
        })
    }

    /// Starts a gRPC server on the specified port.
    ///
    /// # Arguments
    ///
    /// * `port` - The port number to bind the gRPC server to.
    /// * `callback` - The Python callback function to handle invocations.
    fn serve_grpc_server(&mut self, port: u16, callback: Py<PyAny>) -> PyResult<()> {
        let (shutdown_sender, shutdown_receiver) = oneshot::channel(); // Create a shutdown channel
        self.shutdown_sender = Some(shutdown_sender); // Store the sender for later use

        Python::with_gil(|py| {
            py.allow_threads(|| {
                let service = SyncInvocationHandler::new(callback);
                let runtime = get_runtime();
                runtime.spawn(async move {
                    if let Err(e) = start_tonic(port, service, shutdown_receiver).await {
                        eprintln!("Server error: {}", e);
                    }
                });
            });
            Ok(())
        })
    }

    /// Serves a function over Zenoh.
    ///
    /// # Arguments
    ///
    /// * `key_expr` - The Zenoh key expression to serve the function on.
    /// * `event_loop` - The Python event loop.
    /// * `callback` - The Python callback function to handle invocations.
    async fn serve_function(
        &self,
        key_expr: String,
        event_loop: Py<PyAny>,
        callback: Py<PyAny>,
    ) -> PyResult<()> {
        let handler = Python::with_gil(|py| {
            let l = event_loop.into_bound(py);
            let task_locals = TaskLocals::new(l);
            let service = AsyncInvocationHandler::new(callback, task_locals);
            service
        });

        let z_session = self.session.clone();
        let ke = key_expr.clone();
        let z_handler = InvocationZenohHandler::new("".to_string(), Arc::new(handler));
        let runtime = get_runtime();
        let q = runtime
            .spawn(async move {
                oprc_zenoh::util::declare_managed_queryable(&z_session, ke, z_handler, 1, 65536)
                    .await
            })
            .await
            .map_err(|e| {
                PyErr::new::<PyRuntimeError, _>(format!("Failed to spawn queryable: {}", e))
            })?
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?;
        // let q = oprc_zenoh::util::declare_managed_queryable(
        //         &z_session,
        //         key_expr.to_owned(),
        //         z_handler,
        //         1,
        //         65536,
        //     )
        //     .await
        //     .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?;
        {
            let mut table = self.queryable_table.lock().await;
            table.insert(key_expr.clone(), q);
        }
        Ok(())
    }

    /// Stops a function being served over Zenoh.
    ///
    /// # Arguments
    ///
    /// * `key_expr` - The Zenoh key expression of the function to stop.
    async fn stop_function(&self, key_expr: String) -> PyResult<()> {
        let q = {
            let mut table = self.queryable_table.lock().await;
            table.remove(&key_expr)
        };
        if let Some(q) = q {
            q.undeclare().await.map_err(|e| {
                PyErr::new::<PyRuntimeError, _>(format!("Failed to undeclare queryable: {}", e))
            })?;
        } else {
            return Err(PyErr::new::<PyTypeError, _>(format!(
                "No queryable found for key_expr: {}",
                key_expr
            )));
        }
        Ok(())
    }

    /// Stops the gRPC server.
    fn stop_server(&mut self) -> PyResult<()> {
        if let Some(sender) = self.shutdown_sender.take() {
            let _ = sender.send(());
        }
        Ok(())
    }
}

// Modify the start function to accept a shutdown receiver
/// Starts the Tonic gRPC server.
///
/// # Arguments
///
/// * `port` - The port number to bind the gRPC server to.
/// * `service` - The InvocationHandler service.
/// * `shutdown_receiver` - A oneshot receiver to signal server shutdown.
async fn start_tonic<T>(
    port: u16,
    service: T,
    mut shutdown_receiver: oneshot::Receiver<()>,
) -> PyResult<()>
where
    T: OprcFunction,
{
    let socket = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(0, 0, 0, 0)), port);
    let server = OprcFunctionServer::new(service);
    Server::builder()
        .add_service(server.max_decoding_message_size(usize::MAX))
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

/// Listens for shutdown signals (Ctrl+C or terminate on Unix).
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
