use flume::Receiver;
use oprc_invoke::handler::InvocationZenohHandler;
use std::{
    collections::HashMap,
    net::{IpAddr, Ipv4Addr, SocketAddr},
    sync::Arc,
};
use tokio::sync::{Mutex, oneshot};
use zenoh::query::{Query, Queryable};
use std::sync::OnceLock;

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
use pyo3_async_runtimes::{TaskLocals, tokio::get_runtime};
use tokio::runtime::Builder;
use tonic::transport::Server;

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyclass]
/// Represents the OaasEngine, which manages data, RPC, and Zenoh sessions.
pub struct OaasEngine {
    // Lazily created components
    data_manager: Option<Py<DataManager>>,
    rpc_manager: Option<Py<RpcManager>>,
    session: OnceLock<zenoh::Session>,
    shutdown_sender: Option<oneshot::Sender<()>>, // shutdown sender for gRPC server
    queryable_table: Arc<Mutex<HashMap<String, Queryable<Receiver<Query>>>>>,
}

// Internal (non-Python exposed) helper methods
impl OaasEngine {
    fn ensure_session(&self) -> PyResult<&zenoh::Session> {
        if let Some(s) = self.session.get() { return Ok(s); }
        let conf = oprc_zenoh::OprcZenohConfig::init_from_env()
            .map_err(|e| PyErr::new::<PyTypeError, _>(e.to_string()))?;
        let runtime = get_runtime();
        let new_session = runtime.block_on(async move {
            zenoh::open(conf.create_zenoh()).await.map_err(|e| {
                PyErr::new::<PyRuntimeError, _>(format!("Failed to open zenoh session: {}", e))
            })
        })?;
        let _ = self.session.set(new_session);
        Ok(self.session.get().expect("session just initialized"))
    }

    fn ensure_data_manager(&mut self) -> PyResult<()> {
        if self.data_manager.is_none() {
            let session = self.ensure_session()?.clone();
            let dm = Python::attach(|py| Py::new(py, DataManager::new(session)))?;
            self.data_manager = Some(dm);
        }
        Ok(())
    }

    fn ensure_rpc_manager(&mut self) -> PyResult<()> {
        if self.rpc_manager.is_none() {
            let session = self.ensure_session()?.clone();
            let rm = Python::attach(|py| Py::new(py, RpcManager::new(session)))?;
            self.rpc_manager = Some(rm);
        }
        Ok(())
    }
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
        // If telemetry was initialized early without a runtime, upgrade to batch now.
        crate::telemetry::upgrade_batch_if_runtime();
        Ok(OaasEngine {
            data_manager: None,
            rpc_manager: None,
            session: OnceLock::new(),
            shutdown_sender: None,
            queryable_table: Arc::new(Mutex::new(HashMap::new())),
        })
    }
    
    // Exposed getters lazily initialize underlying components.
    #[getter]
    fn data_manager<'py>(&'py mut self, py: Python<'py>) -> PyResult<Py<DataManager>> {
        self.ensure_data_manager()?;
        Ok(self.data_manager.as_ref().unwrap().clone_ref(py))
    }

    #[getter]
    fn rpc_manager<'py>(&'py mut self, py: Python<'py>) -> PyResult<Py<RpcManager>> {
        self.ensure_rpc_manager()?;
        Ok(self.rpc_manager.as_ref().unwrap().clone_ref(py))
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

        Python::attach(|py| {
            let l = event_loop.into_bound(py);
            let task_locals = TaskLocals::new(l);
            py.detach(|| {
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

        Python::attach(|py| {
            py.detach(|| {
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
        let handler = Python::attach(|py| {
            let l = event_loop.into_bound(py);
            let task_locals = TaskLocals::new(l);
            let service = AsyncInvocationHandler::new(callback, task_locals);
            service
        });

    let z_session = self.ensure_session()?.clone();
        let ke = key_expr.clone();
        let z_handler = InvocationZenohHandler::new("".to_string(), Arc::new(handler));
        let runtime = get_runtime();
        let conf = oprc_zenoh::util::ManagedConfig::new(ke, 1, 65536);
        let q = runtime
            .spawn(async move {
                oprc_zenoh::util::declare_managed_queryable(&z_session, conf, z_handler).await
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
