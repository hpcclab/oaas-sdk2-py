
use oprc_pb::ObjMeta;
use pyo3::{
    exceptions::PyRuntimeError, IntoPyObjectExt, Py, PyAny, PyResult, Python,
};
pub(crate) use zenoh::Session;

use crate::model::ObjectData;

#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[pyo3::pyclass]
pub struct DataManager {
    proxy: oprc_offload::proxy::ObjectProxy,
}

impl DataManager {
    pub fn new(session: Session) -> Self {
        let proxy = oprc_offload::proxy::ObjectProxy::new(session);
        DataManager { proxy }
    }
}

#[pyo3_stub_gen::derive::gen_stub_pymethods]
#[pyo3::pymethods]
impl DataManager {
    pub async fn get_obj(
        &self,
        cls_id: String,
        partition_id: u32,
        obj_id: u64,
    ) -> PyResult<Py<PyAny>> {
        let proxy = self.proxy.clone();
        
        let res = proxy
            .get_obj(&ObjMeta {
                cls_id: cls_id.to_string(),
                partition_id,
                object_id: obj_id,
            })
            .await
            .map_err(|e| PyRuntimeError::new_err(e.to_string()));

        Python::with_gil(|py| {
            let obj = res?;
            if let Some(obj) = obj {
                Ok(ObjectData::from(obj).into_py_any(py)?)
            } else {
                Ok(py.None())
            }
        })
    }

    pub async fn set_obj(&self, obj: Py<ObjectData>) -> PyResult<()> {
        let proto = Python::with_gil(|py| {
            let obj = obj.borrow(py);
            obj.to_proto()
        });
        self.proxy
            .set_obj(proto.into())
            .await
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(())
    }
}
