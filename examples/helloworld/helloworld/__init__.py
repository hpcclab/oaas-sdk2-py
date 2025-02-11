import asyncio
import json
import logging
import os
import random
import string

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
        payloads = json.loads(req.payload) if len(req.payload) > 0 else {}
        await self.set_intro(payloads.get("intro", "How are you?"))
        tsid = TSID(self.meta.obj_id)
        resp = f'{{"id":{self.meta.obj_id},"tsid":"{tsid.to_string()}"}}'
        return InvocationResponse(
            status=ResponseStatus.OKAY,
            payload=resp.encode()
        )
        
    @greeter.func(stateless=True)
    async def echo(self, req: InvocationRequest):
        return InvocationResponse(
            status=ResponseStatus.OKAY,
            payload=req.payload
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


record = oaas.new_cls(pkg="example", name="record")



def generate_text(num):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(num))

@record
class Record(BaseObject):
    def __init__(self, meta: ObjectMeta = None, ctx: InvocationContext = None):
        super().__init__(meta, ctx)

    @record.data_getter(index=0)
    async def get_record_data(self, raw: bytes=None) -> dict:
        return json.loads(raw.decode("utf-8"))


    @record.data_setter(index=0)
    async def set_record_data(self, data: dict) -> bytes:
        return json.dumps(data).encode("utf-8")


    @record.func()
    async def random(self, req: InvocationRequest):
        payloads = json.loads(req.payload) if len(req.payload) > 0 else {}
        entries = int(payloads.get('ENTRIES', '10'))
        keys = int(payloads.get('KEYS', '10'))
        values = int(payloads.get('VALUES', '10'))
        data = {}
        for _ in range(entries):
            data[generate_text(keys)] = generate_text(values)
        raw = await self.set_record_data(data)
        return InvocationResponse(
            status=ResponseStatus.OKAY,
            payload=raw
        )




# app = FastAPI()
# router = oaas.build_router()
# app.include_router(router)


async def main(port=8080):
    server = await start_grpc_server(oaas, port=port)
    logger.info(f'Serving on {port}')
    await server.wait_closed()

