use std::collections::HashMap;

// Protocol crate renamed: oprc_pb -> oprc_grpc
use oprc_grpc::{ObjMeta, ValType};
use pyo3::{Bound, PyResult};
use pyo3::exceptions::PyRuntimeError;


#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyo3::pyclass(hash, eq, frozen, get_all)]
#[derive(Clone, PartialEq, Eq, Hash, Default)]
/// Represents the metadata of an object.
pub struct ObjectMetadata {
    object_id: Option<String>,
    cls_id: String,
    partition_id: u32,
}

impl Into<oprc_grpc::ObjMeta> for &ObjectMetadata {
    /// Converts a reference to `ObjectMetadata` into its protobuf representation.
    fn into(self) -> oprc_grpc::ObjMeta {
        ObjMeta {
            object_id: self.object_id.clone(),
            cls_id: self.cls_id.clone(),
            partition_id: self.partition_id,
        }
    }
}

impl From<oprc_grpc::ObjMeta> for ObjectMetadata {
    /// Creates an `ObjectMetadata` from its protobuf representation.
    fn from(value: oprc_grpc::ObjMeta) -> Self {
        ObjectMetadata {
            object_id: value.object_id,
            cls_id: value.cls_id,
            partition_id: value.partition_id,
        }
    }
}

impl ObjectMetadata {
    /// Converts this `ObjectMetadata` into its protobuf representation.
    pub fn into_proto(&self) -> oprc_grpc::ObjMeta {
    oprc_grpc::ObjMeta {
            object_id: self.object_id.clone(),
            cls_id: self.cls_id.clone(),
            partition_id: self.partition_id,
        }
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl ObjectMetadata {
    #[new]
    /// Creates a new `ObjectMetadata`.
    #[pyo3(signature = (cls_id, partition_id, object_id=None))]
    pub fn new(
        cls_id: String,
        partition_id: u32,
        object_id: Option<String>,
    ) -> Self {
        ObjectMetadata {
            object_id,
            cls_id,
            partition_id,
        }
    }

    pub fn __str__(&self) -> String {
        format!(
            "ObjectMetadata {{ object_id: {:?}, cls_id: {}, partition_id: {} }}",
            self.object_id,
            self.cls_id,
            self.partition_id
        )
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyo3::pyclass]
/// Represents the data of an object, including its metadata, entries, and event.
pub struct ObjectData {
    pub(crate) meta: ObjectMetadata,
    pub(crate) entries: HashMap<String, Vec<u8>>,
    pub(crate) event: Option<PyObjectEvent>,
    pub(crate) legacy_entries: bool,
    pub(crate) moved: bool,
}

impl From<oprc_grpc::ObjData> for ObjectData {
    /// Creates an `ObjectData` from its protobuf representation.
    fn from(value: oprc_grpc::ObjData) -> Self {
        if !value.entries.is_empty() {
            ObjectData {
                meta: value
                    .metadata
                    .map(|m| ObjectMetadata::from(m))
                    .unwrap_or_default(),
                entries: value
                    .entries
                    .into_iter()
                    .map(|(k, v)| (k, v.data))
                    .collect(),
                event: value.event.map(PyObjectEvent::from),
                legacy_entries: false,
                moved: false,
            }
        } else {
            // Optimization: Do not convert legacy entries if they are going to be rejected.
            // We just mark it as legacy.
            ObjectData {
                meta: value
                    .metadata
                    .map(|m| ObjectMetadata::from(m))
                    .unwrap_or_default(),
                entries: HashMap::new(),
                event: value.event.map(PyObjectEvent::from),
                legacy_entries: false,
                moved: false,
            }
        }
    }
}

impl ObjectData {
    /// Converts this `ObjectData` into its protobuf representation.
    pub fn into_proto(&self) -> oprc_grpc::ObjData {
    oprc_grpc::ObjData {
            metadata: Some((&self.meta).into()),
            entries: self
                .entries
                .iter()
                .map(|(k, v)| {
                    (
                        k.to_owned(),
                        oprc_grpc::ValData {
                            data: v.to_owned(),
                            r#type: ValType::Byte as i32,
                        },
                    )
                })
                .collect(),
            event: self.event.as_ref().map(|e| e.into_proto()),
        }
    }

    /// Drains the data from this object and converts it into a protobuf object.
    /// This avoids cloning the data.
    pub fn drain_to_proto(&mut self) -> oprc_grpc::ObjData {
        self.moved = true;
        oprc_grpc::ObjData {
            metadata: Some((&self.meta).into()),
            entries: self
                .entries
                .drain()
                .map(|(k, v)| {
                    (
                        k,
                        oprc_grpc::ValData {
                            data: v,
                            r#type: ValType::Byte as i32,
                        },
                    )
                })
                .collect(),
            event: self.event.as_ref().map(|e| e.into_proto()),
        }
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl ObjectData {
    #[new]
    #[pyo3(signature = (meta, entries=HashMap::new(), event=None, legacy_entries=false))]
    /// Creates a new `ObjectData`.
    pub fn new(
        meta: ObjectMetadata,
        entries: HashMap<String, Vec<u8>>,
        event: Option<PyObjectEvent>,
        legacy_entries: bool,
    ) -> Self {
        Self {
            meta,
            entries,
            event,
            legacy_entries,
            moved: false,
        }
    }

    /// Creates a clone of this `ObjectData`.
    pub fn copy(&self) -> Self {
        Self {
            meta: self.meta.clone(),
            entries: self.entries.clone(),
            event: self.event.clone(),
            legacy_entries: self.legacy_entries,
            moved: self.moved,
        }
    }

    #[getter]
    pub fn get_meta(&self) -> ObjectMetadata {
        self.meta.clone()
    }

    #[setter]
    pub fn set_meta(&mut self, value: ObjectMetadata) {
        self.meta = value;
    }

    #[getter]
    pub fn get_entries(&self) -> PyResult<HashMap<String, Vec<u8>>> {
        if self.moved {
            return Err(PyRuntimeError::new_err("ObjectData has been moved"));
        }
        Ok(self.entries.clone())
    }

    #[setter]
    pub fn set_entries(&mut self, value: HashMap<String, Vec<u8>>) {
        self.entries = value;
        self.moved = false;
    }

    #[getter]
    pub fn get_event(&self) -> Option<PyObjectEvent> {
        self.event.clone()
    }

    #[setter]
    pub fn set_event(&mut self, value: Option<PyObjectEvent>) {
        self.event = value;
    }

    #[getter]
    pub fn get_legacy_entries(&self) -> bool {
        self.legacy_entries
    }

    #[setter]
    pub fn set_legacy_entries(&mut self, value: bool) {
        self.legacy_entries = value;
    }
}

impl Into<oprc_grpc::ObjData> for &ObjectData {
    /// Converts a reference to `ObjectData` into its protobuf representation.
    fn into(self) -> oprc_grpc::ObjData {
        self.into_proto()
    }
}


#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass_enum)]
#[pyo3::pyclass(eq, eq_int)]
#[derive(PartialEq, Clone, Copy, Debug)]
pub enum FnTriggerType {
    OnComplete,
    OnError,
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass_enum)]
#[pyo3::pyclass(eq, eq_int)]
#[derive(PartialEq, Clone, Copy, Debug)]
pub enum DataTriggerType {
    OnCreate,
    OnUpdate,
    OnDelete,
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyo3::pyclass]
#[derive(Clone)]
/// Represents an event associated with an object, wrapping the protobuf `ObjectEvent`.
pub struct PyObjectEvent {
    inner: oprc_grpc::ObjectEvent,
}


#[pyo3::pymethods]
impl DataTriggerType {
    fn __str__(&self) -> &'static str {
        match self {
            DataTriggerType::OnCreate => "OnCreate",
            DataTriggerType::OnUpdate => "OnUpdate",
            DataTriggerType::OnDelete => "OnDelete",
        }
    }
}


impl From<oprc_grpc::ObjectEvent> for PyObjectEvent {
    /// Creates a `PyObjectEvent` from its protobuf representation.
    fn from(value: oprc_grpc::ObjectEvent) -> Self {
        Self { inner: value }
    }
}

impl PyObjectEvent {
    /// Converts this `PyObjectEvent` into its protobuf representation.
    pub fn into_proto(&self) -> oprc_grpc::ObjectEvent {
        self.inner.clone()
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl PyObjectEvent {
    #[new]
    /// Creates a new, empty `PyObjectEvent`.
    pub fn new() -> Self {
        Self {
            inner: Default::default(),
        }
    }

    /// Returns a string representation of the `PyObjectEvent`.
    pub fn __str__(&self) -> String {
        format!("{:?}", self.inner)
    }
    /// Manages function triggers by adding or removing a trigger target for a specific function and event type.
    /// 
    /// # Arguments
    /// * `source_fn_id` - The function ID that will trigger the event
    /// * `trigger` - The target to be triggered
    /// * `event_type` - When to trigger (on completion or on error)
    /// * `add_action` - Whether to add (true) or remove (false) the trigger
    /// 
    /// # Returns
    /// * `true` if the operation was successful (trigger added or removed)
    /// * `false` if the operation failed (trigger already exists or not found)
    fn manage_fn_trigger(
        &mut self,
        source_fn_id: String,
        trigger: PyTriggerTarget,
        event_type: Bound<'_, FnTriggerType>,
        add_action: bool, // true for add, false for delete
    ) -> bool {
        let func_trigger_map = &mut self.inner.func_trigger;
        let event_type = *event_type.borrow();
        let trigger = trigger.inner;

        if add_action {
            // Get or create the function trigger entry
            let f_trigger_entry = func_trigger_map
                .entry(source_fn_id.clone())
                .or_insert_with(Default::default);
            // Get the appropriate vector based on event type
            let target_vec = match event_type {
                FnTriggerType::OnComplete => &mut f_trigger_entry.on_complete,
                FnTriggerType::OnError => &mut f_trigger_entry.on_error,
            };

            if target_vec.contains(&trigger) {
                return false; // Already exists
            } else {
                target_vec.push(trigger);
                return true; // Added
            }
        } else {
            // Delete action
            if let Some(f_trigger_entry) = func_trigger_map.get_mut(&source_fn_id) {
                let target_vec = match event_type {
                    FnTriggerType::OnComplete => &mut f_trigger_entry.on_complete,
                    FnTriggerType::OnError => &mut f_trigger_entry.on_error,
                };

                if let Some(index) = target_vec.iter().position(|t| t == &trigger) {
                    target_vec.remove(index);
                    // If the entry becomes empty, we could remove it from the map,
                    // but we'll keep original behavior unless specified.
                    // if f_trigger_entry.on_complete.is_empty() && f_trigger_entry.on_error.is_empty() {
                    //     func_trigger_map.remove(&source_fn_id);
                    // }
                    return true; // Deleted
                }
            }
            return false; // Not found for deletion
        }
        
    }

    /// Manages data triggers by adding or removing a trigger target for a specific data key and event type.
    /// 
    /// # Arguments
    /// * `source_key` - The data key ID that will trigger the event
    /// * `trigger` - The target to be triggered
    /// * `event_type` - When to trigger (on create, update, or delete)
    /// * `add_action` - Whether to add (true) or remove (false) the trigger
    /// 
    /// # Returns
    /// * `true` if the operation was successful (trigger added or removed)
    /// * `false` if the operation failed (trigger already exists or not found)
    fn manage_data_trigger(
        &mut self,
        source_key: String,
        trigger: PyTriggerTarget,
        event_type:  Bound<'_, DataTriggerType>,
        add_action: bool, // true for add, false for delete
    ) -> bool {
        let data_trigger_map = &mut self.inner.data_trigger;
        let event_type = *event_type.borrow();
        let trigger = trigger.inner;

        if add_action {
            // Get or create the data trigger entry
            let d_trigger_entry = data_trigger_map
                .entry(source_key.clone())
                .or_insert_with(Default::default);

            // Get the appropriate vector based on event type
            let target_vec = match event_type {
                DataTriggerType::OnCreate => &mut d_trigger_entry.on_create,
                DataTriggerType::OnUpdate => &mut d_trigger_entry.on_update,
                DataTriggerType::OnDelete => &mut d_trigger_entry.on_delete,
            };

            if target_vec.contains(&trigger) {
                return false; // Already exists
            } else {
                target_vec.push(trigger);
                return true; // Added
            }
        } else {
            // Delete action
            if let Some(d_trigger_entry) = data_trigger_map.get_mut(&source_key) {
                let target_vec = match event_type {
                    DataTriggerType::OnCreate => &mut d_trigger_entry.on_create,
                    DataTriggerType::OnUpdate => &mut d_trigger_entry.on_update,
                    DataTriggerType::OnDelete => &mut d_trigger_entry.on_delete,
                };

                if let Some(index) = target_vec.iter().position(|t| t == &trigger) {
                    target_vec.remove(index);
                    // Optional: clean up entry if all vectors are empty
                    // if d_trigger_entry.on_create.is_empty() && d_trigger_entry.on_update.is_empty() && d_trigger_entry.on_delete.is_empty() {
                    //     data_trigger_map.remove(&source_key);
                    // }
                    return true; // Deleted
                }
            }
            return false; // Not found for deletion
        }
    }

    /// Gets the function triggers associated with this event.
    ///
    /// Returns a map where keys are source function IDs and values are `PyFuncTriggerEntry` objects.
    pub fn get_func_triggers(&self) -> HashMap<String, PyFuncTriggerEntry> {
        self.inner
            .func_trigger
            .iter()
            .map(|(k, v)| (k.clone(), PyFuncTriggerEntry::from(v.clone())))
            .collect()
    }

    /// Gets the data triggers associated with this event.
    ///
    /// Returns a map where keys are source data key IDs and values are `PyDataTriggerEntry` objects.
    pub fn get_data_triggers(&self) -> HashMap<String, PyDataTriggerEntry> {
        self.inner
            .data_trigger
            .iter()
            .map(|(k, v)| (k.clone(), PyDataTriggerEntry::from(v.clone())))
            .collect()
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyo3::pyclass(get_all)]
#[derive(Clone)]
/// Represents the trigger entries for a specific function event, wrapping `oprc_pb::FuncTriggerEntry`.
pub struct PyFuncTriggerEntry {
    /// List of targets to trigger on function completion.
    pub on_complete: Vec<PyTriggerTarget>,
    /// List of targets to trigger on function error.
    pub on_error: Vec<PyTriggerTarget>,
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl PyFuncTriggerEntry {
    /// Returns a string representation of the `PyFuncTriggerEntry`.
    fn __str__(&self) -> String {
        format!(
            "PyFuncTriggerEntry {{ on_complete: {:?}, on_error: {:?} }}",
            self.on_complete
                .iter()
                .map(|t| t.__str__())
                .collect::<Vec<String>>(),
            self.on_error
                .iter()
                .map(|t| t.__str__())
                .collect::<Vec<String>>()
        )
    }
}

impl From<oprc_grpc::FuncTrigger> for PyFuncTriggerEntry {
    fn from(value: oprc_grpc::FuncTrigger) -> Self {
        Self {
            on_complete: value
                .on_complete
                .into_iter()
                .map(PyTriggerTarget::from)
                .collect(),
            on_error: value
                .on_error
                .into_iter()
                .map(PyTriggerTarget::from)
                .collect(),
        }
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyo3::pyclass(get_all)]
#[derive(Clone)]
/// Represents the trigger entries for a specific data event, wrapping `oprc_pb::DataTriggerEntry`.
pub struct PyDataTriggerEntry {
    /// List of targets to trigger on data creation.
    pub on_create: Vec<PyTriggerTarget>,
    /// List of targets to trigger on data update.
    pub on_update: Vec<PyTriggerTarget>,
    /// List of targets to trigger on data deletion.
    pub on_delete: Vec<PyTriggerTarget>,
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl PyDataTriggerEntry {
    /// Returns a string representation of the `PyDataTriggerEntry`.
    fn __str__(&self) -> String {
        format!(
            "PyDataTriggerEntry {{ on_create: {:?}, on_update: {:?}, on_delete: {:?} }}",
            self.on_create
                .iter()
                .map(|t| t.__str__())
                .collect::<Vec<String>>(),
            self.on_update
                .iter()
                .map(|t| t.__str__())
                .collect::<Vec<String>>(),
            self.on_delete
                .iter()
                .map(|t| t.__str__())
                .collect::<Vec<String>>()
        )
    }
}

impl From<oprc_grpc::DataTrigger> for PyDataTriggerEntry {
    fn from(value: oprc_grpc::DataTrigger) -> Self {
        Self {
            on_create: value
                .on_create
                .into_iter()
                .map(PyTriggerTarget::from)
                .collect(),
            on_update: value
                .on_update
                .into_iter()
                .map(PyTriggerTarget::from)
                .collect(),
            on_delete: value
                .on_delete
                .into_iter()
                .map(PyTriggerTarget::from)
                .collect(),
        }
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pyclass)]
#[pyo3::pyclass]
#[derive(Clone)]
/// Represents a target for a trigger, wrapping the protobuf `TriggerTarget`.
pub struct PyTriggerTarget {
    inner: oprc_grpc::TriggerTarget,
}

impl From<oprc_grpc::TriggerTarget> for PyTriggerTarget {
    /// Creates a `PyTriggerTarget` from its protobuf representation.
    fn from(value: oprc_grpc::TriggerTarget) -> Self {
        Self { inner: value }
    }
}

impl PyTriggerTarget {
    /// Converts this `PyTriggerTarget` into its protobuf representation.
    pub fn into_proto(&self) -> oprc_grpc::TriggerTarget {
        self.inner.clone()
    }
}

#[cfg_attr(feature = "stub-gen", pyo3_stub_gen::derive::gen_stub_pymethods)]
#[pyo3::pymethods]
impl PyTriggerTarget {
    #[new]
    #[pyo3(signature = (cls_id, partition_id,  fn_id, object_id=None, req_options=HashMap::new()))]
    /// Creates a new `PyTriggerTarget`.
    #[allow(deprecated)]
    pub fn new(
        cls_id: String,
        partition_id: u32,
        fn_id: String,
        object_id: Option<String>,
        req_options: HashMap<String, String>,
    ) -> Self {
        Self {
            inner: oprc_grpc::TriggerTarget {
                cls_id,
                partition_id,
                fn_id,
                object_id,
                req_options,
            },
        }
    }

    /// Returns a string representation of the `PyTriggerTarget`.
    pub fn __str__(&self) -> String {
        format!("TriggerTarget {:?}", self.inner)
    }

    #[getter]
    /// Gets the class ID of the trigger target.
    pub fn get_cls_id(&self) -> String {
        self.inner.cls_id.clone()
    }

    #[setter]
    /// Sets the class ID of the trigger target.
    pub fn set_cls_id(&mut self, cls_id: String) {
        self.inner.cls_id = cls_id;
    }

    #[getter]
    /// Gets the partition ID of the trigger target.
    pub fn get_partition_id(&self) -> u32 {
        self.inner.partition_id
    }

    #[setter]
    /// Sets the partition ID of the trigger target.
    pub fn set_partition_id(&mut self, partition_id: u32) {
        self.inner.partition_id = partition_id;
    }

    #[getter]
    /// Gets the function ID of the trigger target.
    pub fn get_fn_id(&self) -> String {
        self.inner.fn_id.clone()
    }

    #[setter]
    /// Sets the function ID of the trigger target.
    pub fn set_fn_id(&mut self, fn_id: String) {
        self.inner.fn_id = fn_id;
    }

    #[getter]
    /// Gets the object ID of the trigger target, if any.
    #[allow(deprecated)]
    pub fn get_object_id(&self) -> Option<String> {
        self.inner.object_id.clone()
    }

    #[setter]
    /// Sets the object ID of the trigger target.
    #[allow(deprecated)]
    pub fn set_object_id(&mut self, object_id: Option<String>) {
        self.inner.object_id = object_id;
    }

    #[getter]
    /// Gets the request options for the trigger target.
    pub fn get_req_options(&self) -> HashMap<String, String> {
        self.inner.req_options.clone()
    }

    #[setter]
    /// Sets the request options for the trigger target.
    pub fn set_req_options(&mut self, req_options: HashMap<String, String>) {
        self.inner.req_options = req_options;
    }
}
