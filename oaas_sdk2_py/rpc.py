import asyncio
from asyncio.log import logger
from concurrent.futures import ThreadPoolExecutor
from pydantic.v1 import HttpUrl
import zenoh
from oaas_sdk2_py.pb.oprc import (
    InvocationRequest,
    InvocationResponse,
    ObjectInvocationRequest,
    OprcFunctionStub,
)
from grpclib.client import Channel


class RpcManager:
    def __init__(self, addr: HttpUrl):
        channel = Channel(addr.host, int(addr.port))
        self.client = OprcFunctionStub(channel)

    async def obj_rpc(
        self,
        req: ObjectInvocationRequest,
    ) -> InvocationResponse:
        print("req:", req)
        return await self.client.invoke_obj(req)

    async def fn_rpc(self, req: InvocationRequest) -> InvocationResponse:
        print("req:", req)
        return await self.client.invoke_fn(req)


class ZenohRpcManager:
    session: zenoh.Session

    def __init__(self, z_session: zenoh.Session):
        self.session = z_session
        self.executor = ThreadPoolExecutor()

    async def obj_rpc(
        self,
        req: ObjectInvocationRequest,
    ) -> InvocationResponse:
        print("req:", req)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._blocking_obj_rpc, req)

    def _blocking_obj_rpc(
        self,
        req: ObjectInvocationRequest,
    ) -> InvocationResponse:
        key = f"oprc/{req.cls_id}/{req.partition_id}/objects/{req.object_id}/invokes/{req.fn_id}"
        logger.debug("call rpc to '%s'", key)
        resp = self.session.get(
            key,
            payload=req.__bytes__(),
            congestion_control=zenoh.CongestionControl.BLOCK,
        )
        for reply in resp:
            sample = reply.ok
            if sample is not None:
                payload = sample.payload
                return InvocationResponse.parse(payload)
            else:
                logger.error(f"Received (ERROR: '{reply.err.payload.to_string()}')")
                return None

    async def fn_rpc(self, req: InvocationRequest) -> InvocationResponse:
        print("req:", req)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._blocking_fn_rpc, req)

    def _blocking_fn_rpc(
        self,
        req: InvocationRequest,
    ) -> InvocationResponse:
        resp = self.session.get(
            f"oprc/{req.cls_id}/{req.partition_id}/invokes/{req.fn_id}",
            payload=req.__bytes__(),
            congestion_control=zenoh.CongestionControl.BLOCKING,
        )
        for reply in resp:
            sample = reply.ok
            if sample is not None:
                payload = sample.payload
                return InvocationResponse.parse(payload)
            else:
                logger.error(f"Received (ERROR: '{reply.err.payload.to_string()}')")
                return None
