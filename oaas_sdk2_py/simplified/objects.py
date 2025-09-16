"""
OaaS SDK Objects

This module provides simplified base class with automatic state management
for the OaaS SDK simplified interface.
"""

import oprc_py
from typing import Any, Dict, Optional, get_type_hints, TYPE_CHECKING, Union

from oprc_py import ObjectData, ObjectMetadata
from oprc_py.oprc_py import FnTriggerType, DataTriggerType
from ..model import ClsMeta
from ..session import Session
from .state_descriptor import StateDescriptor

if TYPE_CHECKING:
    pass


class OaasObject:
    """
    Unified base class with automatic state management and serialization.
    
    This class provides:
    - Manual state management (BaseObject style)
    - Automatic state detection from type hints
    - Transparent serialization/deserialization
    - Simplified object lifecycle management
    - Backward compatibility with existing BaseObject API
    """
    
    # BaseObject attributes
    meta: ObjectMetadata
    session: Session
    _state: dict[int, bytes]
    _obj: ObjectData
    # TODO implement per entry dirty checking. Now it is all or nothing
    _dirty: bool
    
    # OaasObject attributes
    _state_fields: Dict[str, StateDescriptor] = {}
    _state_index_counter: int = 0
    
    def __init__(self, meta: ObjectMetadata = None, session: Session = None):
        """
        Initialize the unified object with BaseObject functionality.
        
        Args:
            meta: Object metadata
            session: Session instance
        """
        # BaseObject initialization
        self.meta = meta
        self.session = session
        self._state = {}
        self._obj = None
        self._dirty = False
        self._full_loaded = False
        self._remote = True
        self._auto_commit = False
    
    @property
    def object_id(self) -> int:
        """Get the object ID from metadata."""
        return self.meta.object_id

    # --- Reference helpers -------------------------------------------------
    def as_ref(self) -> 'OaasObject':
        """Return an identity-based proxy to this object."""
        from .references import ObjectRef
        return ObjectRef(self.meta)

    async def set_data_async(self, index: int, data: bytes):
        """
        Set data at the specified index asynchronously.
        
        Args:
            index: Data entry index
            data: Data bytes to store
        """
        self._state[index] = data
        self._dirty = True
        if self._auto_commit:
            await self.commit_async()

    async def get_data_async(self, index: int) -> bytes:
        """
        Get data at the specified index asynchronously.
        
        Args:
            index: Data entry index
            
        Returns:
            Data bytes or None if not found
        """
        if index in self._state:
            return self._state[index]
        if self._full_loaded:
            return None
        obj: oprc_py.ObjectData | None
        try:
            obj = await self.session.data_manager.get_obj_async(
                self.meta.cls_id,
                self.meta.partition_id,
                self.meta.object_id,
            )
        except KeyError:
            obj = None
        if obj is None:
            return None
        self._obj = obj
        self._state = obj.entries
        self._full_loaded = True
        return self._state.get(index)

    def get_data(self, index: int) -> bytes:
        """
        Get data at the specified index synchronously.
        
        Args:
            index: Data entry index
            
        Returns:
            Data bytes or None if not found
        """
        if index in self._state:
            return self._state[index]
        if self._full_loaded:
            return None
        obj: oprc_py.ObjectData | None
        try:
            obj = self.session.data_manager.get_obj(
                self.meta.cls_id,
                self.meta.partition_id,
                self.meta.object_id,
            )
        except KeyError:
            obj = None
        if obj is None:
            return None
        self._obj = obj
        self._state = obj.entries
        self._full_loaded = True
        return self._state.get(index)

    def set_data(self, index: int, data: bytes):
        """
        Set data at the specified index synchronously.
        
        Args:
            index: Data entry index
            data: Data bytes to store
        """
        self._state[index] = data
        self._dirty = True
        if self._auto_commit:
            self.commit()

    def fetch(self, force: bool = False):
        """
        Fetch object data from the server.
        
        Args:
            force: Whether to force fetch even if already loaded
        """
        if not force and self._full_loaded:
            return
        obj: oprc_py.ObjectData | None = self.session.data_manager.get_obj(
            self.meta.cls_id,
            self.meta.partition_id,
            self.meta.object_id,
        )
        if obj is None:
            raise ValueError("Object not found")
        self._obj = obj
        self._state = obj.entries
        self._dirty = False
        self._full_loaded = True

    def trigger(
        self, source, target_fn, event_type: Union[FnTriggerType, DataTriggerType]
    ):
        """
        Adds a trigger to this object.

        Args:
            source: The source of the event, either an integer (data entry index) or function.
            target_fn: The target function to be triggered.
            event_type: The type of event (FnTriggerType or DataTriggerType).
        """
        return self.manage_trigger(source, target_fn, event_type, add=True)

    def suppress(
        self, source, target_fn, event_type: Union[FnTriggerType, DataTriggerType]
    ):
        """
        Removes a trigger from this object.

        Args:
            source: The source of the event, either an integer (data entry index) or function.
            target_fn: The target function whose trigger is to be removed.
            event_type: The type of event (FnTriggerType or DataTriggerType).
        """
        return self.manage_trigger(source, target_fn, event_type, add=False)

    def manage_trigger(
        self,
        source,
        target_fn,
        event_type: Union[FnTriggerType, DataTriggerType],
        add=True,
        req_options=None,
    ):
        """
        Manages (adds or removes) a trigger for this object.

        This method configures a trigger that will invoke a target function
        when a specific event occurs on a source (either a data entry or another function).

        Args:
            source: The source of the event. Can be an integer representing a data entry index
                    or a function object.
            target_fn: The function to be triggered. It must have an _owner attribute
                       which in turn has a meta attribute (ObjectMetadata), and a _meta attribute (FuncMeta).
            event_type: The type of event that will cause the trigger.
                        Must be DataTriggerType if source is an int (data entry).
                        Must be FnTriggerType if source is a function.
            add: A boolean indicating whether to add (True) or remove (False) the trigger.
            req_options: Optional dictionary for request options for the trigger.

        Raises:
            ValueError: If the target function is invalid, if the event_type is mismatched
                        with the source type, or if the source type is unrecognized.
        """
        if not self._obj:
            self.fetch()
        event =  self._obj.event if self._obj.event else oprc_py.PyObjectEvent()

        if not hasattr(target_fn, "_owner") or not target_fn._owner:
            raise ValueError("Invalid target function: missing _owner.")
        if not hasattr(target_fn._owner, "meta") or not target_fn._owner.meta:
            raise ValueError("Invalid target function: _owner missing meta.")
        if not hasattr(target_fn, "_meta") or not target_fn._meta:
            raise ValueError("Invalid target function: missing _meta.")

        meta = target_fn._owner.meta
        fn_meta = target_fn._meta

        trigger_target = oprc_py.PyTriggerTarget(
            cls_id=meta.cls_id,
            partition_id=meta.partition_id,
            object_id=meta.object_id,
            fn_id=fn_meta.name,
            req_options={} if req_options is None else req_options,
        )

        if isinstance(source, int):  # Data trigger
            if not isinstance(event_type, DataTriggerType):
                raise ValueError(
                    "event_type must be an instance of DataTriggerType for data source"
                )

            out = event.manage_data_trigger(
                source_key=source,
                trigger=trigger_target,
                event_type=event_type,
                add_action=add,
            )
            self._obj.event = event
        elif hasattr(source, "_meta") and source._meta:  # Function trigger
            if not isinstance(event_type, FnTriggerType):
                raise ValueError(
                    "event_type must be an instance of FnTriggerType for function source"
                )

            out = event.manage_fn_trigger(
                source_fn_id=source._meta.name,
                trigger=trigger_target,
                event_type=event_type,
                add_action=add,
            )
            self._obj.event = event
        else:
            raise ValueError(
                "Invalid source type. Must be an integer (data key) or a function with _meta attribute."
            )
        self._dirty = True  # Mark object as dirty as event is part of ObjectData
        return out

    @property
    def dirty(self):
        """Check if the object has uncommitted changes."""
        return self._dirty

    @property
    def state(self) -> dict[int, bytes]:
        """Get the current state dictionary."""
        return self._state

    @property
    def remote(self) -> bool:
        """Check if this is a remote object."""
        return self._remote

    def create_request(
        self,
        fn_name: str,
        payload: bytes | None = None,
        options: dict[str, str] | None = None,
    ) -> oprc_py.InvocationRequest:
        """
        Create an invocation request for a function.
        
        Args:
            fn_name: Function name
            payload: Optional payload bytes
            options: Optional request options
            
        Returns:
            InvocationRequest object
        """
        o = oprc_py.InvocationRequest(
            cls_id=self.meta.cls_id, fn_id=fn_name, payload=payload
        )
        if options is not None:
            o.options = options
        return o

    def create_obj_request(
        self,
        fn_name: str,
        payload: bytes | None = None,
        options: dict[str, str] | None = None,
    ) -> oprc_py.ObjectInvocationRequest:
        """
        Create an object invocation request for a function.
        
        Args:
            fn_name: Function name
            payload: Optional payload bytes
            options: Optional request options
            
        Returns:
            ObjectInvocationRequest object
        """
        payload = payload if payload is not None else b""
        o = oprc_py.ObjectInvocationRequest(
            cls_id=self.meta.cls_id,
            partition_id=self.meta.partition_id,
            object_id=self.meta.object_id,
            fn_id=fn_name,
            payload=payload,
        )
        if options is not None:
            o.options = options
        return o

    def delete(self):
        """Delete this object from the session."""
        # Prefer the class metadata captured at registration/creation
        cls_meta = getattr(self.__class__, '_oaas_cls_meta', None)
        if cls_meta is None:
            # Fallback: construct a lightweight object with cls_id attribute
            class _ClsMetaShim:
                def __init__(self, cls_id: str):
                    self.cls_id = cls_id
            cls_meta = _ClsMetaShim(self.meta.cls_id)

        self.session.delete_object(
            cls_meta,
            self.meta.object_id,
            self.meta.partition_id,
        )
        if self._auto_commit:
            self.commit()

    async def commit_async(self, force: bool = False):
        """Commit changes to the server asynchronously."""
        if self._dirty or force:
            obj_data = oprc_py.ObjectData(
                meta=self.meta,
                entries=self._state,
                event=self._obj.event if self._obj else None,  # Ensure event is included
            )
            await self.session.data_manager.set_obj_async(obj_data)
            self._dirty = False

    def commit(self, force: bool = False):
        """Commit changes to the server synchronously."""
        if self._dirty or force:
            obj_data = oprc_py.ObjectData(
                meta=self.meta,
                entries=self._state,
                event=self._obj.event if self._obj else None,  # Ensure event is included
            )
            self.session.data_manager.set_obj(obj_data)
            self._dirty = False

    def create_object(
        self,
        cls_meta: ClsMeta,
        obj_id: int = None,
        local: bool = False,
    ):
        """
        Create a new object instance.
        
        Args:
            cls_meta: Class metadata
            obj_id: Optional object ID
            local: Whether to create locally
            
        Returns:
            New object instance
        """
        return self.session.create_object(
            cls_meta=cls_meta, obj_id=obj_id, local=local
        )

    def load_object(self, cls_meta: ClsMeta, obj_id: int):
        """
        Load an existing object instance.
        
        Args:
            cls_meta: Class metadata
            obj_id: Object ID to load
            
        Returns:
            Loaded object instance
        """
        return self.session.load_object(cls_meta, obj_id)

    def delete_object(self, cls_meta: ClsMeta, obj_id: int, partition_id: Optional[int] = None):
        """
        Delete an object instance.
        
        Args:
            cls_meta: Class metadata
            obj_id: Object ID to delete
            partition_id: Optional partition ID
        """
        return self.session.delete_object(cls_meta, obj_id, partition_id)
    
    def __init_subclass__(cls, **kwargs):
        """
        Automatically set up state management for subclasses.
        
        This method analyzes class annotations and creates StateDescriptor
        instances for each typed attribute, providing automatic serialization.
        """
        super().__init_subclass__(**kwargs)
        
        # Initialize state management
        cls._state_fields = {}
        cls._state_index_counter = 0
        
        # Get type hints for this class (not inherited ones)
        try:
            type_hints = get_type_hints(cls)
        except Exception:
            # If type hints fail, skip state management
            type_hints = {}
        
        # Process each annotated attribute
        for name, type_hint in type_hints.items():
            if not name.startswith('_') and name not in ('meta', 'session'):  # Skip private attributes and BaseObject internals
                # Get default value if it exists
                default_value = getattr(cls, name, None)
                
                # Create descriptor for this field
                descriptor = StateDescriptor(
                    name=name,
                    type_hint=type_hint,
                    default_value=default_value,
                    index=cls._state_index_counter
                )
                
                # Replace class attribute with descriptor
                setattr(cls, name, descriptor)
                cls._state_fields[name] = descriptor
                cls._state_index_counter += 1
    
    @classmethod
    def create(cls, obj_id: Optional[int] = None, local: bool = None) -> 'OaasObject':
        """
        Create a new instance of this service with automatic session management.
        
        Args:
            obj_id: Optional object ID (auto-generated if not provided)
            local: Whether to create a local object (defaults to True in mock mode)
            
        Returns:
            New instance of the service
        """
        # Import here to avoid circular imports
        from .service import OaasService
        
        # Use the global service registry to get the class metadata
        service_name = getattr(cls, '_oaas_service_name', cls.__name__)
        package = getattr(cls, '_oaas_package', 'default')
        
        # Get or create the global oaas instance
        global_oaas = OaasService._get_global_oaas()
        
        # Default to local in mock mode, remote otherwise, unless explicitly overridden
        if local is None:
            try:
                local = bool(global_oaas.mock_mode)
            except Exception:
                local = False
        
        # Get class metadata
        cls_meta = getattr(cls, '_oaas_cls_meta', None)
        
        if cls_meta is None:
            # Create metadata if not already created
            cls_meta = global_oaas.new_cls(service_name, package)
            cls._oaas_cls_meta = cls_meta
        
        # Try to use AutoSessionManager for automatic session management
        try:
            auto_session_manager = OaasService._get_auto_session_manager()
            obj = auto_session_manager.create_object(cls_meta, obj_id=obj_id, local=local)
        except Exception:
            # Fallback to traditional session creation if auto session manager fails
            session = global_oaas.new_session()
            obj = session.create_object(cls_meta, obj_id=obj_id, local=local)
            # Manually set auto-commit if possible
            if hasattr(obj, '_auto_commit'):
                obj._auto_commit = False  # Disable since no auto session manager
        
        return obj
    
    @classmethod
    def load(cls, obj_id: int, partition_id: Optional[int] = None) -> 'OaasObject':
        """
        Load an existing instance of this service.
        
        Args:
            obj_id: ID of the object to load
            
        Returns:
            Loaded instance of the service
        """
        # Import here to avoid circular imports
        from .service import OaasService
        
        service_name = getattr(cls, '_oaas_service_name', cls.__name__)
        package = getattr(cls, '_oaas_package', 'default')
        
        # Get or create the global oaas instance
        global_oaas = OaasService._get_global_oaas()
        
        # Get class metadata
        cls_meta = getattr(cls, '_oaas_cls_meta', None)
        
        if cls_meta is None:
            # Create metadata if not already created
            cls_meta = global_oaas.new_cls(service_name, package)
            cls._oaas_cls_meta = cls_meta
        
        # Try to use AutoSessionManager for automatic session management
        auto_session_manager = OaasService._get_auto_session_manager()
        obj = auto_session_manager.load_object(cls_meta, obj_id, partition_id=partition_id)
    
        return obj

    # =============================================================================
    # AGENT MANAGEMENT METHODS
    # =============================================================================

    @classmethod
    async def start_agent(cls, obj_id: int = None, partition_id: int = None, 
                         loop: Any = None) -> str:
        """
        Start agent for this service class.
        
        Convenience method that delegates to OaasService.start_agent.
        """
        from .service import OaasService
        return await OaasService.start_agent(cls, obj_id, partition_id, loop)

    @classmethod
    async def stop_agent(cls, obj_id: int = None) -> None:
        """
        Stop agent for this service class.
        
        Convenience method that delegates to OaasService.stop_agent.
        """
        from .service import OaasService
        await OaasService.stop_agent(service_class=cls, obj_id=obj_id)

    async def start_instance_agent(self, loop: Any = None) -> str:
        """Start agent for this specific object instance."""
        from .service import OaasService
        return await OaasService.start_agent(
            service_class=self.__class__,
            obj_id=self.object_id,
            loop=loop
        )

    async def stop_instance_agent(self) -> None:
        """Stop agent for this specific object instance."""
        from .service import OaasService
        await OaasService.stop_agent(
            service_class=self.__class__,
            obj_id=self.object_id
        )


# Backward compatibility alias
BaseObject = OaasObject
