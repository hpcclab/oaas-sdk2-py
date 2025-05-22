
import oprc_py

from oaas_sdk2_py.session import Session

from .model import FuncMeta

class BaseObject:
    _state: dict[int, bytes]
    _obj: oprc_py.ObjectData
    # TODO implement per entry dirty checking. Now it is all or nothing
    _dirty: bool

    def __init__(self, meta: oprc_py.ObjectMetadata = None, session: 'Session' = None):
        self.meta = meta
        self.session = session
        self._state = {}
        self._dirty = False
        self._full_loaded = False
        self._remote = True
        self._auto_commit = False

    async def set_data(self, index: int, data: bytes):
        self._state[index] = data
        self._dirty = True
        if self._auto_commit:
            await self.commit()
            

    async def get_data(self, index: int) -> bytes:
        if index in self._state:
            return self._state[index]
        if self._full_loaded:
            return None
        obj: oprc_py.ObjectData | None = await self.session.data_manager.get_obj(
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
    
    def add_on_complete_trigger(self, source_fn: 'FuncMeta', target: 'BaseObject', fn: 'FuncMeta'):
        self._obj
        pass
    
    async def commit(self):
        if self._dirty:
            obj_data = oprc_py.ObjectData(
                meta=self.meta,
                entries=self._state,
            )
            await self.session.data_manager.set_obj(obj_data)
            self._dirty = False