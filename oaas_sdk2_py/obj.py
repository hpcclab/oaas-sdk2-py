import oprc_py
import warnings
from typing import Optional, Union

from oprc_py import ObjectData, ObjectMetadata
from oprc_py.oprc_py import FnTriggerType, DataTriggerType
from oaas_sdk2_py.model import ClsMeta
from oaas_sdk2_py.session import Session


class BaseObject:
    meta: ObjectMetadata
    session: Session
    _state: dict[int, bytes]
    _obj: ObjectData
    # TODO implement per entry dirty checking. Now it is all or nothing
    _dirty: bool

    def __init__(self, meta: ObjectMetadata = None, session: Session = None):
        warnings.warn(
            "BaseObject is deprecated. Use OaasObject from oaas_sdk2_py.simplified.objects instead.",
            DeprecationWarning,
            stacklevel=2
        )
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
        return self.meta.object_id

    async def set_data_async(self, index: int, data: bytes):
        self._state[index] = data
        self._dirty = True
        if self._auto_commit:
            await self.commit_async()

    async def get_data_async(self, index: int) -> bytes:
        if index in self._state:
            return self._state[index]
        if self._full_loaded:
            return None
        obj: oprc_py.ObjectData | None = await self.session.data_manager.get_obj_async(
            self.meta.cls_id,
            self.meta.partition_id,
            self.meta.object_id,
        )
        if obj is None:
            return None
        self._obj = obj
        self._state = obj.entries
        self._full_loaded = True
        return self._state.get(index)

    def get_data(self, index: int) -> bytes:
        if index in self._state:
            return self._state[index]
        if self._full_loaded:
            return None
        obj: oprc_py.ObjectData | None = self.session.data_manager.get_obj(
            self.meta.cls_id,
            self.meta.partition_id,
            self.meta.object_id,
        )
        if obj is None:
            return None
        self._obj = obj
        self._state = obj.entries
        self._full_loaded = True
        return self._state.get(index)

    def set_data(self, index: int, data: bytes):
        self._state[index] = data
        self._dirty = True
        if self._auto_commit:
            self.commit()

    def fetch(self, force: bool = False):
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
        return self._dirty

    @property
    def state(self) -> dict[int, bytes]:
        return self._state

    @property
    def remote(self) -> bool:
        return self._remote

    def create_request(
        self,
        fn_name: str,
        payload: bytes | None = None,
        options: dict[str, str] | None = None,
    ) -> oprc_py.InvocationRequest:
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
        self.session.delete_object(
            self.meta.cls_id,
            self.meta.partition_id,
            self.meta.object_id,
        )
        if self._auto_commit:
            self.commit()

    async def commit_async(self):
        if self._dirty:
            obj_data = oprc_py.ObjectData(
                meta=self.meta,
                entries=self._state,
                event=self._obj.event if self._obj else None,  # Ensure event is included
            )
            await self.session.data_manager.set_obj_async(obj_data)
            self._dirty = False

    def commit(self):
        if self._dirty:
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
        return self.session.create_object(
            cls_meta=cls_meta, obj_id=obj_id, local=local
        )

    def load_object(self, cls_meta: ClsMeta, obj_id: int):
        return self.session.load_object(cls_meta, obj_id)

    def delete_object(self, cls_meta: ClsMeta, obj_id: int, partition_id: Optional[int] = None):
        return self.session.delete_object(cls_meta, obj_id, partition_id)


# Import the unified OaasObject to replace BaseObject
# This provides backward compatibility while encouraging migration
try:
    from .simplified.objects import OaasObject
    # Replace BaseObject with OaasObject for new usage
    BaseObject = OaasObject
except ImportError:
    # Fallback if simplified module is not available
    pass