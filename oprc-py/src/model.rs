use std::collections::HashMap;

use oprc_pb::{ObjMeta, ValType};

#[derive(Clone)]
#[pyo3::pyclass]
#[pyo3_stub_gen::derive::gen_stub_pyclass]
pub struct InvocationRequest {
    #[pyo3(get, set)]
    partition_id: u32,
    #[pyo3(get, set)]
    cls_id: String,
    #[pyo3(get, set)]
    fn_id: String,
    #[pyo3(get, set)]
    options: HashMap<String, String>,
    #[pyo3(get, set)]
    payload: Vec<u8>,
}

impl From<oprc_pb::InvocationRequest> for InvocationRequest {
    fn from(value: oprc_pb::InvocationRequest) -> Self {
        InvocationRequest {
            partition_id: value.partition_id,
            cls_id: value.cls_id,
            fn_id: value.fn_id,
            options: value.options,
            payload: value.payload,
        }
    }
}

#[derive(Clone)]
#[pyo3::pyclass]
#[pyo3_stub_gen::derive::gen_stub_pyclass]
pub struct InvocationResponse {
    #[pyo3(get, set)]
    payload: Vec<u8>,
    #[pyo3(get, set)]
    status: i32,
    #[pyo3(get, set)]
    header: HashMap<String, String>,
}

impl From<InvocationResponse> for oprc_pb::InvocationResponse {
    fn from(value: InvocationResponse) -> Self {
        oprc_pb::InvocationResponse {
            payload: Some(value.payload),
            status: value.status,
            headers: value.header,
        }
    }
}

impl From<&InvocationResponse> for oprc_pb::InvocationResponse {
    fn from(value: &InvocationResponse) -> Self {
        oprc_pb::InvocationResponse {
            payload: Some(value.payload.to_owned()),
            status: value.status,
            headers: value.header.to_owned(),
        }
    }
}

#[pyo3::pymethods]
#[pyo3_stub_gen::derive::gen_stub_pymethods]
impl InvocationResponse {
    #[new]
    #[pyo3(signature = (payload=vec![], status=0, header=HashMap::new()))]
    fn new(payload: Vec<u8>, status: i32, header: HashMap<String, String>) -> Self {
        InvocationResponse {
            payload,
            status,
            header,
        }
    }
}

#[derive(Clone)]
#[pyo3::pyclass]
#[pyo3_stub_gen::derive::gen_stub_pyclass]
pub struct ObjectInvocationRequest {
    #[pyo3(get, set)]
    partition_id: u32,
    #[pyo3(get, set)]
    cls_id: String,
    #[pyo3(get, set)]
    fn_id: String,
    #[pyo3(get, set)]
    object_id: u64,
    #[pyo3(get, set)]
    options: HashMap<String, String>,
    #[pyo3(get, set)]
    payload: Vec<u8>,
}

impl From<oprc_pb::ObjectInvocationRequest> for ObjectInvocationRequest {
    fn from(value: oprc_pb::ObjectInvocationRequest) -> Self {
        ObjectInvocationRequest {
            partition_id: value.partition_id,
            cls_id: value.cls_id,
            fn_id: value.fn_id,
            object_id: value.object_id,
            options: value.options,
            payload: value.payload,
        }
    }
}

#[pyo3::pyclass]
#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[derive(Clone)]
pub struct ObjectMetadata {
    #[pyo3(get, set)]
    object_id: u64,
    #[pyo3(get, set)]
    cls_id: String,
    #[pyo3(get, set)]
    partition_id: u32,
}

impl Into<oprc_pb::ObjMeta> for &ObjectMetadata {
    fn into(self) -> oprc_pb::ObjMeta {
        ObjMeta {
            object_id: self.object_id,
            cls_id: self.cls_id.clone(),
            partition_id: self.partition_id,
        }
    }
}

impl From<oprc_pb::ObjMeta> for ObjectMetadata {
    fn from(value: oprc_pb::ObjMeta) -> Self {
        ObjectMetadata {
            object_id: value.object_id,
            cls_id: value.cls_id,
            partition_id: value.partition_id,
        }
    }
}

#[pyo3::pyclass]
#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[derive(Clone)]
pub struct ObjectData {
    #[pyo3(get, set)]
    meta: Option<ObjectMetadata>,
    #[pyo3(get, set)]
    entries: HashMap<u32, Vec<u8>>,
}

impl From<oprc_pb::ObjData> for ObjectData {
    fn from(value: oprc_pb::ObjData) -> Self {
        ObjectData {
            meta: value.metadata.map(|m| ObjectMetadata::from(m)),
            entries: value
                .entries
                .into_iter()
                .map(|(k, v)| (k, v.data))
                .collect(),
        }
    }
}

impl ObjectData {
    pub fn to_proto(&self) -> oprc_pb::ObjData {
        oprc_pb::ObjData {
            metadata: self.meta.as_ref().map(|m| m.into()),
            entries: self
                .entries
                .iter()
                .map(|(k, v)| {
                    (
                        *k,
                        oprc_pb::ValData {
                            data: v.to_owned(),
                            r#type: ValType::Byte as i32,
                        },
                    )
                })
                .collect(),
        }
    }
}

impl Into<oprc_pb::ObjData> for &ObjectData {
    fn into(self) -> oprc_pb::ObjData {
        self.to_proto()
    }
}
