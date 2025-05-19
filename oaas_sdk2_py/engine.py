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
        remote_only: bool = False,
    ):
        self.partition_id = partition_id
        self.rpc_manager = rpc_manager
        self.data_manager = data_manager
        self.local_obj_dict = {}
        self.remote_obj_dict = {}
        self.remote_only = remote_only

    async def create_object(
        self,
        cls_meta: ClsMeta,
        obj_id: int = None,
        local: bool = False,
    ):
        if local:
            if obj_id is None:
                obj_id = TSID.create().number
            meta = ObjectMeta(
                cls=cls_meta.cls_id,
                partition_id=self.partition_id,
                obj_id=obj_id,
                remote=False or self.remote_only,
            )
            obj = cls_meta.cls(meta=meta, ctx=self)
            if self.remote_only:
                self.remote_obj_dict[meta] = obj
            else:
                self.local_obj_dict[meta] = obj
            return obj
        else:
            #TODO: create object on remote
            pass

    def load_object(self, cls_meta: ClsMeta, obj_id: int):
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
    # def init(self, enabla_scout: bool = False):
    # zenoh.init_log_from_env_or("error")
    # peers = self.config.get_zenoh_peers()
    # if peers is None:
    #     conf = {}
    # else:
    #     conf = {
    #         "connect": {
    #             "endpoints": peers,
    #         },
    #         "mode": "peer",
    #     }
    # if not enabla_scout:
    #     conf["scouting"] = {
    #         "multicast": {
    #             "enabled": False,
    #         },
    #         "gossip": {
    #             "enabled": False,
    #             "autoconnect": {"router": [], "peer": []},
    #         },
    #     }

    # zenoh_config = zenoh.Config.from_json5(json.dumps(conf))
    # logger.debug("zenoh config: %s", zenoh_config)
    # self.z_session = zenoh.open(zenoh_config)

    # self.rpc = ZenohRpcManager(self.z_session)

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
    
    async def create_object(
        self,
        cls_meta: ClsMeta,
        obj_id: int = None,
        local: bool = False,
    ):
        self.default_session.create_object(cls_meta=cls_meta, obj_id=obj_id, local=local)

    def load_object(self, cls_meta: ClsMeta, obj_id: int):
        self.default_session.load_object(cls_meta, obj_id)

    # async def handle_obj_invoke(
    #     self, req: oprc_py.ObjectInvocationRequest
    # ) -> oprc_py.InvocationResponse:
    #     meta = self.meta_repo.get_cls_meta(req.cls_id)
    #     fn_meta = meta.func_list[req.fn_id]
    #     ctx = self.new_session()
    #     obj = ctx.create_object(meta, req.object_id)
    #     try:
    #         logger.debug("calling %s", fn_meta)
    #         resp = await fn_meta.caller(obj, req)
    #         await ctx.commit()
    #         logger.debug("done commit")
    #         return resp
    #     except Exception as e:
    #         logging.error("Exception occurred", exc_info=True)
    #         return InvocationResponse(
    #             status=ResponseStatus.APP_ERROR, payload=str(e).encode()
    #         )

    # async def serve_local_function(
    #     self, cls_id: str, fn_name: str, obj_id: int, partition_id: int = 0
    # ):
    #     key = f"oprc/{cls_id}/{partition_id}/objects/{obj_id}/invokes/{fn_name}"
    #     logger.info("Serving local function: %s", key)
    #     queryable = self.z_session.declare_queryable(key)

    #     async def query_handler():
    #         while True:
    #             # Run the blocking receive operation in a separate thread using the executor
    #             def receive_query():
    #                 return queryable.recv()

    #             query = await asyncio.get_event_loop().run_in_executor(
    #                 self.executor, receive_query
    #             )

    #             logger.debug("Received query %s", query.key_expr)

    #             # Process the query in the asyncio event loop
    #             payload = query.payload
    #             if payload is not None:
    #                 payload = payload.to_bytes()
    #                 logger.debug("payload %s", payload)
    #                 req = ObjectInvocationRequest().parse(payload)
    #                 logger.debug("Received request %s", req)
    #                 resp = await self.handle_obj_invoke(req)
    #                 resp_bytes = bytes(resp)
    #                 logger.debug("Sending response %s", resp_bytes)
    #                 query.reply(key, resp_bytes)
    #             else:
    #                 logger.error("Received function request without payload")
    #                 query.reply_err(b"Received function request without payload")

    #     # Create and return background task
    #     task = asyncio.create_task(query_handler())
    #     return task
