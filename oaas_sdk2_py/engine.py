import logging
from typing import Dict, Optional
from tsidpy import TSID
import oprc_py
from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.handler import GrpcHandler
from oaas_sdk2_py.model import ObjectMeta, ClsMeta
from oaas_sdk2_py.repo import MetadataRepo

logger = logging.getLogger(__name__)


class Session:
    local_obj_dict: Dict[oprc_py.ObjectMetadata, "BaseObject"]
    remote_obj_dict: Dict[oprc_py.ObjectMetadata, "BaseObject"]

    def __init__(
        self,
        partition_id: int,
        rpc_manager: oprc_py.RpcManager,
        data_manager: oprc_py.DataManager,
        local_only: bool = False,
    ):
        self.partition_id = partition_id
        self.rpc_manager = rpc_manager
        self.data_manager = data_manager
        self.local_obj_dict = {}
        self.remote_obj_dict = {}
        self.local_only = local_only

    def create_object(
        self,
        cls_meta: ClsMeta,
        obj_id: int = None,
        local: bool = False,
    ):
        if obj_id is None:
            obj_id = TSID.create().number
        meta = ObjectMeta(
            cls=cls_meta.cls_id,
            partition_id=self.partition_id,
            obj_id=obj_id,
            remote=not (local or self.local_only),
        )
        obj = cls_meta.cls(meta=meta, session=self)
        if meta.remote:
            self.remote_obj_dict[meta] = obj
        else:
            self.local_obj_dict[meta] = obj
        return obj

    def load_object(self, cls_meta: ClsMeta, obj_id: int):
        meta = ObjectMeta(
            cls=cls_meta.cls_id,
            partition_id=self.partition_id,
            obj_id=obj_id,
            remote=True,
        )
        obj = cls_meta.cls(meta=meta, session=self)
        self.remote_obj_dict[meta] = obj
        return obj

    async def obj_rpc(
        self,
        req: oprc_py.ObjectInvocationRequest,
    ) -> oprc_py.InvocationResponse:
        return await self.rpc_manager.invoke_obj(req)

    async def fn_rpc(
        self,
        req: oprc_py.InvocationRequest,
    ) -> oprc_py.InvocationResponse:
        return await self.rpc_manager.invoke_fn(req)

    async def commit(self):
        for k, v in self.local_obj_dict.items():
            logger.debug(
                "check of committing [%s, %s, %s, %s]",
                v.meta.cls,
                v.meta.partition_id,
                v.meta.obj_id,
                v.dirty,
            )
            if v.dirty:
                await self.data_manager.set_all(
                    cls_id=v.meta.cls,
                    partition_id=v.meta.partition_id,
                    object_id=v.meta.obj_id,
                    data=v.state,
                )
                v._dirty = False


class BaseObject:
    # _refs: Dict[int, Ref]
    _state: Dict[int, bytes]
    _dirty: bool

    def __init__(self, meta: oprc_py.ObjectMetadata = None, session: Session = None):
        self.meta = meta
        self.ctx = session
        self.session = session
        self._state = {}
        self._dirty = False
        self._full_loaded = False

    def set_data(self, index: int, data: bytes):
        self._state[index] = data
        self._dirty = True

    async def get_data(self, index: int) -> bytes:
        if index in self._state:
            return self._state[index]
        if self._full_loaded:
            return None
        obj: oprc_py.ObjectData | None = await self.ctx.data_manager.get_obj(
            self.meta.cls_id,
            self.meta.partition_id,
            self.meta.object_id,
        )
        if obj is None:
            return None
        self._state = obj.entries
        self._full_loaded = True
        return self._state.get(index)

    @property
    def dirty(self):
        return self._dirty

    @property
    def state(self) -> Dict[int, bytes]:
        return self._state

    @property
    def remote(self) -> bool:
        return self.meta.remote

    def create_request(
        self,
        fn_name: str,
        payload: bytes | None = None,
        options: dict[str, str] | None = None,
    ) -> oprc_py.InvocationRequest:
        o = oprc_py.InvocationRequest(
            cls_id=self.meta.cls, fn_id=fn_name, payload=payload
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
        o = oprc_py.ObjectInvocationRequest(
            cls_id=self.meta.cls,
            partition_id=self.meta.partition_id,
            object_id=self.meta.obj_id,
            fn_id=fn_name,
            payload=payload,
        )
        if options is not None:
            o.options = options
        return o


class Oparaca:
    data_manager: oprc_py.DataManager
    rpc: oprc_py.RpcManager

    def __init__(self, default_pkg: str = "default", config: OprcConfig = None):
        if config is None:
            config = OprcConfig()
        self.config = config
        # self.odgm_url = config.oprc_odgm_url
        self.meta_repo = MetadataRepo()
        self.default_pkg = default_pkg
        self.engine = oprc_py.OaasEngine()
        self.default_partition_id = config.oprc_partition_default
        self.default_session = self.new_session()
    

    def new_cls(self, name: Optional[str] = None, pkg: Optional[str] = None) -> ClsMeta:
        meta = ClsMeta(
            name,
            pkg if pkg is not None else self.default_pkg,
            lambda m: self.meta_repo.add_cls(meta),
        )
        return meta

    def new_session(self, partition_id: Optional[int] = None) -> Session:
        return Session(
            partition_id if partition_id is not None else self.default_partition_id,
            self.engine.rpc_manager,
            self.engine.data_manager,
        )

    def start_grpc_server(self, loop, port=8080):
        self.engine.serve_grpc_server(port, loop, GrpcHandler(self))

    def stop_server(self):
        self.engine.stop_server()

    async def run_agent(
        self,
        loop,
        cls_meta: ClsMeta,
        obj_id: int,
        parition_id: Optional[int] = None,
    ):
        if parition_id is None:
            parition_id = self.default_partition_id
        for fn_id, fn_meta in cls_meta.func_list.items():
            if fn_meta.serve_with_agent:
                if fn_meta.stateless:
                    key = f"oprc/{cls_meta.pkg}.{cls_meta.name}/{parition_id}/invokes/{fn_id}"
                else: 
                    key = f"oprc/{cls_meta.pkg}.{cls_meta.name}/{parition_id}/objects/{obj_id}/invokes/{fn_id}"
                await self.engine.serve_function(key, loop, GrpcHandler(self))
    
    async def stop_agent(self, cls_meta: ClsMeta, obj_id: int, partition_id: Optional[int] = None):
        if partition_id is None:
            partition_id = self.default_partition_id
        for fn_id, fn_meta in cls_meta.func_list.items():
            if fn_meta.serve_with_agent:
                if fn_meta.stateless:
                    key = f"oprc/{cls_meta.pkg}.{cls_meta.name}/{partition_id}/invokes/{fn_id}"
                else: 
                    key = f"oprc/{cls_meta.pkg}.{cls_meta.name}/{partition_id}/objects/{obj_id}/invokes/{fn_id}"
                await self.engine.stop_function(key)
        
    
    def create_object(
        self,
        cls_meta: ClsMeta,
        obj_id: int = None,
        local: bool = False,
    ):
        return self.default_session.create_object(cls_meta=cls_meta, obj_id=obj_id, local=local)

    def load_object(self, cls_meta: ClsMeta, obj_id: int):
        return self.default_session.load_object(cls_meta, obj_id)

    
