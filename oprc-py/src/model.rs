use std::collections::HashMap;


#[derive(Clone)]
#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyo3::pyclass(get_all, set_all)]
/// Represents a request to invoke a function.
pub struct InvocationRequest {
    pub partition_id: u32,
    pub cls_id: String,
    pub fn_id: String,
    pub options: HashMap<String, String>,
    pub payload: Vec<u8>,
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl InvocationRequest {
    #[new]
    #[pyo3(signature = (cls_id, fn_id, partition_id=0, options=HashMap::new(), payload=vec![]))]
    /// Creates a new `InvocationRequest`.
    pub fn new(
        cls_id: String,
        fn_id: String,
        partition_id: u32,
        options: HashMap<String, String>,
        payload: Vec<u8>,
    ) -> Self {
        InvocationRequest {
            partition_id,
            cls_id,
            fn_id,
            options,
            payload,
        }
    }
}

impl InvocationRequest {
    /// Converts this `InvocationRequest` into its protobuf representation.
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
    /// Converts this `InvocationRequest` into its protobuf representation.
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
    /// Creates an `InvocationRequest` from its protobuf representation.
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

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass_enum)]
#[pyo3::pyclass(eq, eq_int)]
#[derive(PartialEq)]
/// Represents the status code of an invocation response.
pub enum InvocationResponseCode {
    Okay = 0,
    InvalidRequest = 1,
    AppError = 2,
    SystemError = 3,
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[derive(Clone)]
#[pyo3::pyclass(get_all, set_all)]
/// Represents the response of an invocation.
pub struct InvocationResponse {
    payload: Vec<u8>,
    status: i32,
    header: HashMap<String, String>,
}

impl From<oprc_pb::InvocationResponse> for InvocationResponse {
    /// Creates an `InvocationResponse` from its protobuf representation.
    fn from(value: oprc_pb::InvocationResponse) -> Self {
        Self {
            payload: value.payload.unwrap_or_default(),
            status: value.status,
            header: value.headers,
        }
    }
}

impl From<InvocationResponse> for oprc_pb::InvocationResponse {
    /// Converts this `InvocationResponse` into its protobuf representation.
    fn from(value: InvocationResponse) -> Self {
        oprc_pb::InvocationResponse {
            payload: Some(value.payload),
            status: value.status,
            headers: value.header,
        }
    }
}

impl From<&InvocationResponse> for oprc_pb::InvocationResponse {
    /// Converts a reference to `InvocationResponse` into its protobuf representation.
    fn from(value: &InvocationResponse) -> Self {
        oprc_pb::InvocationResponse {
            payload: Some(value.payload.to_owned()),
            status: value.status,
            headers: value.header.to_owned(),
        }
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl InvocationResponse {
    #[new]
    #[pyo3(signature = (payload=vec![], status=0, header=HashMap::new()))]
    /// Creates a new `InvocationResponse`.
    fn new(payload: Vec<u8>, status: i32, header: HashMap<String, String>) -> Self {
        InvocationResponse {
            payload,
            status,
            header,
        }
    }

    /// Returns a string representation of the `InvocationResponse`.
    fn __str__(&self) -> String {
        format!(
            "InvocationResponse {{ payload: {:?}, status: {}, header: {:?} }}",
            self.payload, self.status, self.header
        )
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[derive(Clone)]
#[pyo3::pyclass(get_all, set_all)]
/// Represents a request to invoke a function on an object.
pub struct ObjectInvocationRequest {
    partition_id: u32,
    cls_id: String,
    fn_id: String,
    object_id: u64,
    options: HashMap<String, String>,
    payload: Vec<u8>,
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl ObjectInvocationRequest {
    #[new]
    #[pyo3(signature = (cls_id, fn_id, object_id, partition_id=0,  options=HashMap::new(), payload=vec![]))]
    /// Creates a new `ObjectInvocationRequest`.
    pub fn new(
        cls_id: String,
        fn_id: String,
        object_id: u64,
        partition_id: u32,
        options: HashMap<String, String>,
        payload: Vec<u8>,
    ) -> Self {
        ObjectInvocationRequest {
            partition_id,
            cls_id,
            fn_id,
            object_id,
            options,
            payload,
        }
    }
}

impl From<oprc_pb::ObjectInvocationRequest> for ObjectInvocationRequest {
    /// Creates an `ObjectInvocationRequest` from its protobuf representation.
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
    /// Converts this `ObjectInvocationRequest` into its protobuf representation.
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
