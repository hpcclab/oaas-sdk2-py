from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from typing import Dict, Optional
from tsidpy import TSID
import zenoh
import asyncio

from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.data import DataManager, ZenohDataManager
from oaas_sdk2_py.model import ObjectMeta, ClsMeta
from oaas_sdk2_py.pb.oprc import InvocationRequest, InvocationResponse, ObjectInvocationRequest, ResponseStatus
from oaas_sdk2_py.repo import MetadataRepo
from oaas_sdk2_py.rpc import RpcManager, ZenohRpcManager

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

    async def obj_rpc(
        self,
        req: ObjectInvocationRequest,
    ) -> InvocationResponse:
        return await self.rpc.obj_rpc(req)

    async def fn_rpc(
        self,
        req: InvocationRequest,
    ) -> InvocationResponse:
        return await self.rpc.fn_rpc(req)

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
        o =  InvocationRequest(
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
    ) -> ObjectInvocationRequest:
        o = ObjectInvocationRequest(
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
        
        zenoh.init_log_from_env_or("error")
        peer_url = self.config.oprc_zenoh_peers
        if peer_url is None:
            conf = {}
        else:
            conf = {
                'connect': {
                    'endpoints': [peer_url],
                },
                'mode': 'client',
            }
        zenoh_config = zenoh.Config.from_json5(json.dumps(conf))
        self.z_session = zenoh.open(zenoh_config)    
        self.executor = ThreadPoolExecutor()
        self.data = ZenohDataManager(self.z_session)
        self.rpc = ZenohRpcManager(self.z_session)

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
    
    async def handle_obj_invoke(self, req: ObjectInvocationRequest) -> InvocationResponse:
        meta = self.meta_repo.get_cls_meta(req.cls_id)
        fn_meta = meta.func_list[req.fn_id]
        ctx = self.new_context()
        obj = ctx.create_object(meta, req.object_id)
        try:
            logger.debug("calling %s", fn_meta)
            resp = await fn_meta.caller(obj, req)
            await ctx.commit()
            logger.debug("done commit")
            return resp
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            return InvocationResponse(status=ResponseStatus.APP_ERROR, payload=str(e).encode())
        
    async def serve_local_function(self, cls_id: str, fn_name: str, obj_id: int, partition_id: int = 0):
        key = f"oprc/{cls_id}/{partition_id}/objects/{obj_id}/invokes/{fn_name}"
        logger.info("Serving local function: %s", key)
        queryable = self.z_session.declare_queryable(key)
        
        async def query_handler():
            while True:
                # Run the blocking receive operation in a separate thread using the executor
                def receive_query():
                    return queryable.recv()
                
                query = await asyncio.get_event_loop().run_in_executor(
                    self.executor, receive_query
                )
                
                logger.debug("Received query %s", query.key_expr)
                
                # Process the query in the asyncio event loop
                payload = query.payload
                if payload is not None:
                    payload = payload.to_bytes()
                    logger.debug("payload %s", payload)
                    req = ObjectInvocationRequest().parse(payload)
                    logger.debug("Received request %s", req)
                    resp = await self.handle_obj_invoke(req)
                    resp_bytes = bytes(resp)
                    logger.debug("Sending response %s", resp_bytes)
                    query.reply(key, resp_bytes)
                else:
                    logger.error("Received function request without payload")
                    query.reply_err(b"Received function request without payload")
        
        # Create and return background task
        task = asyncio.create_task(query_handler())
        return task