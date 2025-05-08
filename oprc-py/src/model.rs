use std::collections::HashMap;

use oprc_pb::{ObjMeta, ValType};

#[derive(Clone)]
#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[pyo3::pyclass]
pub struct InvocationRequest {
    #[pyo3(get, set)]
    pub partition_id: u32,
    #[pyo3(get, set)]
    pub cls_id: String,
    #[pyo3(get, set)]
    pub fn_id: String,
    #[pyo3(get, set)]
    pub options: HashMap<String, String>,
    #[pyo3(get, set)]
    pub payload: Vec<u8>,
}

impl InvocationRequest {
    pub fn into_proto(&self) -> oprc_pb::InvocationRequest {
        oprc_pb::InvocationRequest {
            partition_id: self.partition_id,
            cls_id: self.cls_id.clone(),
            fn_id: self.fn_id.clone(),
            options: self.options.clone(),
            payload: self.payload.clone(),
        }
    }
}

impl Into<oprc_pb::InvocationRequest> for InvocationRequest {
    fn into(self) -> oprc_pb::InvocationRequest {
        oprc_pb::InvocationRequest {
            partition_id: self.partition_id,
            cls_id: self.cls_id,
            fn_id: self.fn_id,
            options: self.options,
            payload: self.payload,
        }
    }
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

#[pyo3_stub_gen::derive::gen_stub_pyclass_enum]
#[pyo3::pyclass(eq, eq_int)]
#[derive(PartialEq)]
pub enum InvocationResponseCode {
    Okay = 0,
    InvalidRequest = 1,
    AppError = 2,
    SystemError = 3,
}

#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[derive(Clone)]
#[pyo3::pyclass]
pub struct InvocationResponse {
    #[pyo3(get, set)]
    payload: Vec<u8>,
    #[pyo3(get, set)]
    status: i32,
    #[pyo3(get, set)]
    header: HashMap<String, String>,
}

impl From<oprc_pb::InvocationResponse> for InvocationResponse {
    fn from(value: oprc_pb::InvocationResponse) -> Self {
        Self {
            payload: value.payload.unwrap_or_default(),
            status: value.status,
            header: value.headers,
        }
    }
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

#[pyo3_stub_gen::derive::gen_stub_pymethods]
#[pyo3::pymethods]
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

#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[derive(Clone)]
#[pyo3::pyclass()]
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


impl ObjectInvocationRequest {
    pub fn into_proto(&self) -> oprc_pb::ObjectInvocationRequest {
        oprc_pb::ObjectInvocationRequest {
            partition_id: self.partition_id,
            cls_id: self.cls_id.clone(),
            fn_id: self.fn_id.clone(),
            object_id: self.object_id,
            options: self.options.clone(),
            payload: self.payload.clone(),
        }
    }
}


#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[pyo3::pyclass(hash, eq, frozen)]
#[derive(Clone, PartialEq, Eq, Hash, Default)]
pub struct ObjectMetadata {
    #[pyo3(get)]
    object_id: u64,
    #[pyo3(get)]
    cls_id: String,
    #[pyo3(get)]
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

impl ObjectMetadata {
    pub fn into_proto(&self) -> oprc_pb::ObjMeta {
        oprc_pb::ObjMeta {
            object_id: self.object_id,
            cls_id: self.cls_id.clone(),
            partition_id: self.partition_id,
        }
    }
    
}

#[pyo3_stub_gen::derive::gen_stub_pymethods]
#[pyo3::pymethods]
impl ObjectMetadata {
    #[new]
    pub fn new(cls_id: String, partition_id: u32, object_id: u64) -> Self {
        ObjectMetadata {
            object_id,
            cls_id,
            partition_id,
        }
    }
}

#[pyo3_stub_gen::derive::gen_stub_pyclass]
#[pyo3::pyclass]
#[derive(Clone)]
pub struct ObjectData {
    #[pyo3(get, set)]
    pub(crate) meta: ObjectMetadata,
    #[pyo3(get, set)]
    pub(crate) entries: HashMap<u32, Vec<u8>>,
    #[pyo3(get, set)]
    pub(crate) dirty: bool,
    #[pyo3(get, set)]
    pub(crate) remote: bool,
}

impl From<oprc_pb::ObjData> for ObjectData {
    fn from(value: oprc_pb::ObjData) -> Self {
        ObjectData {
            meta: value.metadata.map(|m| ObjectMetadata::from(m)).unwrap_or_default(),
            entries: value
                .entries
                .into_iter()
                .map(|(k, v)| (k, v.data))
                .collect(),
            dirty: false,
            remote: false,
        }
    }
}

impl ObjectData {
    pub fn into_proto(&self) -> oprc_pb::ObjData {
        oprc_pb::ObjData {
            metadata: Some((&self.meta).into()),
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
        self.into_proto()
    }
}
