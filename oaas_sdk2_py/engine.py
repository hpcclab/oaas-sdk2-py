import logging
import os
from typing import Dict, Optional

from fastapi import APIRouter
from tsidpy import TSID

from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.data import DataManager, Ref, ZenohDataManager
from oaas_sdk2_py.model import ObjectMeta, ClsMeta
from oaas_sdk2_py.pb.oprc import ObjectInvocationRequest, InvocationResponse
from oaas_sdk2_py.repo import MetadataRepo
from oaas_sdk2_py.rpc import RpcManager

logger = logging.getLogger(__name__)


class InvocationContext:
    local_obj_dict: Dict[ObjectMeta, 'BaseObject'] = {}
    remote_obj_dict: Dict[ObjectMeta, 'BaseObject'] = {}

    def __init__(self,
                 partition_id: int,
                 rpc: RpcManager,
                 data: DataManager, ):
        self.partition_id = partition_id
        self.rpc = rpc
        self.data = data

    def create_empty_object(self, cls_meta: ClsMeta):
        obj_id = TSID.create().number
        meta = ObjectMeta(cls=cls_meta.cls_id, partition_id=self.partition_id, obj_id=obj_id, remote=False)
        obj = cls_meta.cls(meta=meta, ctx=self)
        self.local_obj_dict[meta] = obj
        return obj

    def create_object(self,
                      cls_meta: ClsMeta,
                      obj_id: int, ):
        meta = ObjectMeta(cls=cls_meta.cls_id, partition_id=self.partition_id, obj_id=obj_id, remote=False)
        obj = cls_meta.cls(meta=meta, ctx=self)
        self.local_obj_dict[meta] = obj
        return obj

    def create_object_from_ref(self,
                               cls_meta: ClsMeta,
                               obj_id: int):
        meta = ObjectMeta(cls=cls_meta.cls_id, partition_id=self.partition_id, obj_id=obj_id, remote=True)
        obj = cls_meta.cls(meta=meta, ctx=self)
        self.remote_obj_dict[meta] = obj
        return obj

    def rpc_call(self,
                 obj,
                 fn_name: str,
                 req: ObjectInvocationRequest, ):
        return self.rpc.rpc_call(obj.meta, fn_name, req)

    async def commit(self):
        for (k, v) in self.local_obj_dict.items():
            await self.data.set_all(cls_id=v.meta.cls,
                                    partition_id=v.meta.partition_id,
                                    object_id=v.meta.obj_id,
                                    data=v.state)


class BaseObject:
    _refs: Dict[int, Ref] = {}
    _state: Dict[int, bytes] = {}
    _dirty = False
    remote: bool = False

    def __init__(self,
                 meta: ObjectMeta = None,
                 ctx: InvocationContext = None):
        self.meta = meta
        self.ctx = ctx

    def create_data_ref(self, index: int) -> Ref:
        ref = Ref(
            cls_id=self.meta.cls,
            object_id=self.meta.obj_id,
            partition_id=self.meta.partition_id,
            key=index,
        )
        self._refs[index] = ref
        return ref

    def set_data(self, index: int, data: bytes):
        self._state[index] = data
        self._dirty = True

    async def get_data(self, index: int) -> bytes:
        if index in self._state:
            return self._state[index]
        raw = await self.ctx.data.get(self.meta.cls, self.meta.partition_id, self.meta.obj_id, index)
        self._state[index] = raw
        return raw

    @property
    def dirty(self):
        return self._dirty

    @property
    def state(self) -> Dict[int, bytes]:
        return self._state


class Oparaca:
    data: DataManager
    rpc: RpcManager

    def __init__(self, default_pkg: str = "default",
                 config:OprcConfig=None):
        if config is None:
            config = OprcConfig()
        self.config = config
        self.odgm_url = config.oprc_odgm_url
        self.meta_repo = MetadataRepo()
        self.default_pkg = default_pkg
        self.default_partition_id = int(os.environ.get("OPRC_PARTITION", '0'))

    def init(self):
        logger.debug(f"connect odgm: {self.odgm_url}")
        # self.data = DataManager(self.odgm_url)
        self.data = ZenohDataManager()
        self.rpc = RpcManager()

    def new_cls(self,
                name: Optional[str] = None,
                pkg: Optional[str] = None) -> ClsMeta:
        meta = ClsMeta(name,
                       pkg if pkg is not None else self.default_pkg,
                       lambda m: self.meta_repo.add_cls(meta))
        return meta

    def new_context(self,
                    partition_id: Optional[int] = None) -> InvocationContext:
        return InvocationContext(
            partition_id if partition_id is not None else self.default_partition_id,
            self.rpc, self.data)

    def _rest_invoke_object(self,
                            cls: str,
                            fn: str,
                            obj_id: Optional[str],
                            partition_id: int,
                            payload: bytes) -> Optional[InvocationResponse]:
        meta = self.meta_repo.cls_dict[cls]
        if meta is None:
            return None
        fn_meta = meta.func_list[fn]
        if fn_meta is None:
            return None
        ctx = self.new_context(partition_id)
        obj_id = TSID.from_string(obj_id).number
        obj = ctx.create_object(meta, obj_id)
        request = ObjectInvocationRequest(
            cls_id=cls,
            fn_id=fn,
            object_id=obj_id,
            partition_id=partition_id,
            payload=payload,
        )
        payload = fn_meta.func(obj, request)
        return InvocationResponse(payload=payload)

    def _rest_invoke_function(self,
                              cls: str,
                              fn: str,
                              partition_id: int,
                              payload: bytes):
        return self._rest_invoke_object(cls, fn, None, partition_id, payload)

    def build_router(self) -> APIRouter:
        router = APIRouter()
        router.post("/class/{cls}/partitions/{partition_key}/obj/{obj_id}/func/{fn}")(self._rest_invoke_object)
        router.post("/class/{cls}/partitions/{partition_key}/func/{fn}")(self._rest_invoke_function)
        return router
