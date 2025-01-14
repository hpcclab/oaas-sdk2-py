import asyncio
import json
import logging
import os
import sys
from importlib.metadata import metadata

from fastapi import FastAPI
from tsidpy import TSID

from oaas_sdk2_py import Oparaca, start_grpc_server, InvocationRequest, InvocationResponse
from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.engine import InvocationContext, logger, BaseObject
from oaas_sdk2_py.model import ObjectMeta
from oaas_sdk2_py.pb.oprc import ObjectInvocationRequest, ResponseStatus

oaas = Oparaca(config=OprcConfig())
greeter = oaas.new_cls(pkg="example", name="hello")


@greeter
class Greeter(BaseObject):
    def __init__(self, meta: ObjectMeta = None, ctx: InvocationContext = None):
        super().__init__(meta, ctx)

    @greeter.data_getter(index=0)
    async def get_intro(self, raw: bytes=None) -> str:
        return raw.decode("utf-8")


    @greeter.data_setter(index=0)
    async def set_intro(self, data: str) -> bytes:
        return data.encode("utf-8")


    @greeter.func(stateless=True)
    async def new(self, req: InvocationRequest):
        if len(req.payload) == 0:
            await self.set_intro("How are you?")
        else:
            payloads = json.loads(req.payload)
            await self.set_intro(payloads.get("intro", "How are you?"))
        tsid = TSID(self.meta.obj_id)
        resp = f'{{"id":{self.meta.obj_id},"tsid":"{tsid.to_string()}"}}'
        return InvocationResponse(
            status=ResponseStatus.OKAY,
            payload=resp.encode()
        )

    @greeter.func()
    async def greet(self,  req: ObjectInvocationRequest):
        if len(req.payload) == 0:
            name = "world"
        else:
            payloads = json.loads(req.payload)
            name = payloads.get("name", "world")
        intro = await self.get_intro()
        resp = "hello " + name + ". " + intro
        return InvocationResponse(
            status=ResponseStatus.OKAY,
            payload=resp.encode()
        )

    # @greeter.func()
    # async def talk(self, friend_id: int):
    #     friend = self.ctx.create_object_from_ref(greeter, friend_id)
    #     # REMOTE RPC
    #     friend.greet()

    @greeter.func()
    async def change_intro(self, req: ObjectInvocationRequest):
        if len(req.payload) > 0:
            payloads = json.loads(req.payload)
            await self.set_intro(payloads.get("intro", "How are you?"))
        return InvocationResponse(
            status=ResponseStatus.OKAY
        )


app = FastAPI()
router = oaas.build_router()
app.include_router(router)


async def main(port=8080):
    level = logging.getLevelName(os.getenv("LOG_LEVEL", "INFO"))
    logging.basicConfig(level=level)
    server = await start_grpc_server(oaas, port=port)
    logger.info(f'Serving on {port}')
    await server.wait_closed()

