import logging
from typing import Optional
import oprc_py

from oaas_sdk2_py.mock import LocalDataManager, LocalRpcManager
from .config import OaasConfig
from .handler import AsyncInvocationHandler, SyncInvocationHandler
from .model import ClsMeta
from .repo import MetadataRepo
from .session import Session
from . import telemetry as _telemetry_mod



logger = logging.getLogger(__name__)


class Oparaca:
    data_manager: oprc_py.DataManager
    rpc: oprc_py.RpcManager

    def __init__(
        self,
        default_pkg: str = "default",
        config: OaasConfig = None,
        mock_mode: bool = False,
        meta_repo: MetadataRepo = None,
        engine: oprc_py.OaasEngine = None,
        async_mode: bool = False,
    ):
        if config is None:
            config = OaasConfig()
        self.config = config
        self.default_partition_id = config.oprc_partition_default
        self.meta_repo = meta_repo if meta_repo else MetadataRepo()
        self.default_pkg = default_pkg
        self.mock_mode = mock_mode
        # In mock mode, avoid creating a real engine (which may start Zenoh)
        if mock_mode:
            self.engine = None
        else:
            self.engine = engine if engine else oprc_py.OaasEngine()
        # Managers now lazy; placeholders for mock mode
        self._rpc_manager = None
        self._data_manager = None
        if mock_mode:
            self._rpc_manager = LocalRpcManager()
            self._data_manager = LocalDataManager()
        self.async_mode = async_mode
        # Retry deferred telemetry initialization now that runtime exists
        try:
            _telemetry_mod.retry_if_needed(service_name=self.config.telemetry_service_name, service_version=self.config.telemetry_service_version)
        except Exception:
            pass
        
        # Auto session manager will be set externally by OaasService
        self._auto_session_manager = None
        
        
    def mock(self):
        return Oparaca(
            default_pkg=self.default_pkg,
            config=self.config,
            mock_mode=True,
            meta_repo=self.meta_repo,
            engine=self.engine,
        )

    @property
    def rpc_manager(self):
        if self.mock_mode:
            return self._rpc_manager
        if self._rpc_manager is None:
            # Triggers lazy creation in Rust engine getter
            if self.engine is None:
                raise RuntimeError("Engine is not available in mock mode")
            self._rpc_manager = self.engine.rpc_manager
        return self._rpc_manager

    @property
    def data_manager(self):
        if self.mock_mode:
            return self._data_manager
        if self._data_manager is None:
            if self.engine is None:
                raise RuntimeError("Engine is not available in mock mode")
            self._data_manager = self.engine.data_manager
        return self._data_manager
            
        
    def new_cls(self, name: Optional[str] = None, pkg: Optional[str] = None) -> ClsMeta:
        meta = ClsMeta(
            name,
            pkg if pkg is not None else self.default_pkg,
            lambda m: self.meta_repo.add_cls(meta),
        )
        return meta

    def new_session(self, partition_id: Optional[int] = None) -> Session:
        if self.mock_mode:
            session = Session(
                partition_id if partition_id is not None else self.default_partition_id,
                self.rpc_manager,
                self.data_manager,
                self.meta_repo,
            )
            session.rpc_manager.session = session
            return session
        else:
            return Session(
                partition_id if partition_id is not None else self.default_partition_id,
                self.rpc_manager,
                self.data_manager,
                self.meta_repo,
            )

    def start_grpc_server(self, loop=None, port=8080):
        if self.mock_mode:
            # No-op in mock mode: simulate server started
            return
        if self.async_mode:
            self.engine.serve_grpc_server_async(port, loop, AsyncInvocationHandler(self))
        else:
            self.engine.serve_grpc_server(port, SyncInvocationHandler(self))
            
            
    def stop_server(self):
        if self.engine:
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
        for fn_id, fn_meta in cls_meta.func_dict.items():
            if fn_meta.serve_with_agent:
                if self.mock_mode or self.engine is None:
                    # No-op in mock mode: simulate agent started
                    continue
                if fn_meta.stateless:
                    key = f"oprc/{cls_meta.pkg}.{cls_meta.name}/{parition_id}/invokes/{fn_id}"
                else:
                    key = f"oprc/{cls_meta.pkg}.{cls_meta.name}/{parition_id}/objects/{obj_id}/invokes/{fn_id}"
                await self.engine.serve_function(key, loop, AsyncInvocationHandler(self))

    async def stop_agent(
        self, cls_meta: ClsMeta, obj_id: int, partition_id: Optional[int] = None
    ):
        if partition_id is None:
            partition_id = self.default_partition_id
        for fn_id, fn_meta in cls_meta.func_dict.items():
            if fn_meta.serve_with_agent:
                if self.mock_mode or self.engine is None:
                    # No-op in mock mode: simulate agent stopped
                    continue
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
        return self.default_session.create_object(
            cls_meta=cls_meta, obj_id=obj_id, local=local
        )

    def load_object(self, cls_meta: ClsMeta, obj_id: int):
        return self.default_session.load_object(cls_meta, obj_id)

    def delete_object(self, cls_meta: ClsMeta, obj_id: int, partition_id: Optional[int] = None):
        return self.default_session.delete_object(cls_meta, obj_id, partition_id)
    
    async def commit_async(self):
        return await self.default_session.commit_async()
    
    def commit(self):
        return self.default_session.commit()