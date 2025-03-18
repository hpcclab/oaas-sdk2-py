import logging
import os
from typing import Dict, Optional
from tsidpy import TSID

from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.data import DataManager, Ref, ZenohDataManager
from oaas_sdk2_py.model import ObjectMeta, ClsMeta
from oaas_sdk2_py.pb.oprc import InvocationRequest, ObjectInvocationRequest
from oaas_sdk2_py.repo import MetadataRepo
from oaas_sdk2_py.rpc import RpcManager

logger = logging.getLogger(__name__)


class InvocationContext:
    local_obj_dict: Dict[ObjectMeta, "BaseObject"]
    remote_obj_dict: Dict[ObjectMeta, "BaseObject"]

    def __init__(
        self,
        partition_id: int,
        rpc: RpcManager,
        data: DataManager,
    ):
        self.partition_id = partition_id
        self.rpc = rpc
        self.data_manager = data
        self.local_obj_dict = {}
        self.remote_obj_dict = {}

    def create_empty_object(self, cls_meta: ClsMeta):
        obj_id = TSID.create().number
        meta = ObjectMeta(
            cls=cls_meta.cls_id,
            partition_id=self.partition_id,
            obj_id=obj_id,
            remote=False,
        )
        obj = cls_meta.cls(meta=meta, ctx=self)
        self.local_obj_dict[meta] = obj
        return obj

    def create_object(
        self,
        cls_meta: ClsMeta,
        obj_id: int,
    ):
        meta = ObjectMeta(
            cls=cls_meta.cls_id,
            partition_id=self.partition_id,
            obj_id=obj_id,
            remote=False,
        )
        obj = cls_meta.cls(meta=meta, ctx=self)
        self.local_obj_dict[meta] = obj
        return obj

    def create_object_from_ref(self, cls_meta: ClsMeta, obj_id: int):
        meta = ObjectMeta(
            cls=cls_meta.cls_id,
            partition_id=self.partition_id,
            obj_id=obj_id,
            remote=True,
        )
        obj = cls_meta.cls(meta=meta, ctx=self)
        self.remote_obj_dict[meta] = obj
        return obj

    def obj_rpc(
        self,
        obj,
        fn_name: str,
        req: ObjectInvocationRequest,
    ):
        obj_meta = obj.meta
        req.cls_id = obj_meta.cls
        req.partition_id = obj_meta.partition_id
        req.obj_id = obj_meta.obj_id
        req.fn_id = fn_name
        return self.rpc.obj_rpc(obj.meta, fn_name, req)

    async def commit(self):
        for k, v in self.local_obj_dict.items():
            logger.debug("commit %s %s %s %s", v.meta.cls, v.meta.partition_id, v.meta.obj_id, v.dirty)
            if v.dirty:
                await self.data_manager.set_all(
                    cls_id=v.meta.cls,
                    partition_id=v.meta.partition_id,
                    object_id=v.meta.obj_id,
                    data=v.state,
                )


class BaseObject:
    # _refs: Dict[int, Ref]
    _state: Dict[int, bytes]
    _dirty: bool

    def __init__(self, meta: ObjectMeta = None, ctx: InvocationContext = None):
        self.meta = meta
        self.ctx = ctx
        self._state = {}
        self._dirty = False

    # def create_data_ref(self, index: int) -> Ref:
    #     ref = Ref(
    #         cls_id=self.meta.cls,
    #         object_id=self.meta.obj_id,
    #         partition_id=self.meta.partition_id,
    #         key=index,
    #     )
    #     self._refs[index] = ref
    #     return ref

    def set_data(self, index: int, data: bytes):
        self._state[index] = data
        self._dirty = True

    async def get_data(self, index: int) -> bytes:
        if index in self._state:
            return self._state[index]
        raw = await self.ctx.data_manager.get(
            self.meta.cls, self.meta.partition_id, self.meta.obj_id, index
        )
        self._state[index] = raw
        return raw

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
    ) -> InvocationRequest:
        return InvocationRequest(
            cls_id=self.meta.cls, fn_id=fn_name, payload=payload, options=options
        )

    def create_obj_request(
        self,
        fn_name: str,
        payload: bytes | None = None,
        options: dict[str, str] | None = None,
    ) -> ObjectInvocationRequest:
        return ObjectInvocationRequest(
            cls_id=self.meta.cls,
            partition_id=self.meta.partition_id,
            object_id=self.meta.obj_id,
            fn_id=fn_name,
            payload=payload,
            options=options,
        )


class Oparaca:
    data: DataManager
    rpc: RpcManager

    def __init__(self, default_pkg: str = "default", config: OprcConfig = None):
        if config is None:
            config = OprcConfig()
        self.config = config
        self.odgm_url = config.oprc_odgm_url
        self.meta_repo = MetadataRepo()
        self.default_pkg = default_pkg
        self.default_partition_id = int(os.environ.get("OPRC_PARTITION", "0"))

    def init(self):
        # self.data = DataManager(self.odgm_url)
        self.data = ZenohDataManager(self.config.oprc_zenoh_peers)
        self.rpc = RpcManager(self.odgm_url)

    def new_cls(self, name: Optional[str] = None, pkg: Optional[str] = None) -> ClsMeta:
        meta = ClsMeta(
            name,
            pkg if pkg is not None else self.default_pkg,
            lambda m: self.meta_repo.add_cls(meta),
        )
        return meta

    def new_context(self, partition_id: Optional[int] = None) -> InvocationContext:
        return InvocationContext(
            partition_id if partition_id is not None else self.default_partition_id,
            self.rpc,
            self.data,
        )
