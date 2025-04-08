import json
import logging
import random
import string

from pydantic import BaseModel
from tsidpy import TSID

from oaas_sdk2_py import Oparaca, start_grpc_server, InvocationRequest, InvocationResponse
from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.engine import InvocationContext, BaseObject
from oaas_sdk2_py.model import ObjectMeta
from oaas_sdk2_py.pb.oprc import ResponseStatus

oaas = Oparaca(config=OprcConfig())
greeter = oaas.new_cls(pkg="example", name="hello")


class GreetCreator(BaseModel):
    id: int = 0
    intro: str = "How are you?"

class GreetCreatorResponse(BaseModel):
    id: int
    

class Greet(BaseModel):
    name: str = "world"
    

class GreetResponse(BaseModel):
    message: str
    

class UpdateIntro(BaseModel):
    intro: str = "How are you?"
    
@greeter
class Greeter(BaseObject):
    def __init__(self, meta: ObjectMeta = None, ctx: InvocationContext = None):
        super().__init__(meta, ctx)

    @greeter.data_getter(index=0)
    async def get_intro(self, raw: bytes=None) -> str:
        return raw.decode("utf-8") if raw is not None else ""


    @greeter.data_setter(index=0)
    async def set_intro(self, data: str) -> bytes:
        return data.encode("utf-8")


    @greeter.func(stateless=True)
    async def new(self, req: GreetCreator) -> GreetCreatorResponse:
        if req.id == 0:
            req.id = TSID.create().number
        self.meta.obj_id = req.id
        await self.set_intro(req.intro)
        return GreetCreatorResponse(id=self.meta.obj_id)
        
    @greeter.func(stateless=True)
    async def echo(self, req: InvocationRequest):
        return InvocationResponse(
            status=ResponseStatus.OKAY,
            payload=req.payload
        )

    @greeter.func()
    async def greet(self,  req: Greet) -> GreetResponse:
        intro = await self.get_intro()
        resp = "hello " + req.name + ". " + intro
        return GreetResponse(message=resp)

    # @greeter.func()
    # async def talk(self, friend_id: int):
    #     friend = self.ctx.create_object_from_ref(greeter, friend_id)
    #     # REMOTE RPC
    #     friend.greet()

    @greeter.func()
    async def change_intro(self, req: UpdateIntro):
        await self.set_intro(req.intro)


record = oaas.new_cls(pkg="example", name="record")



def generate_text(num):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(num))

class RandomRequest(BaseModel):
    entries: int = 10
    keys: int = 10
    values: int = 10

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
    async def random(self, req: RandomRequest):
        data = {}
        for _ in range(req.entries):
            data[generate_text(req.keys)] = generate_text(req.values)
        raw = await self.set_record_data(data)
        return InvocationResponse(
            status=ResponseStatus.OKAY,
            payload=raw
        )



async def main(port=8080):
    server = await start_grpc_server(oaas, port=port)
    logging.info(f'Serving on {port}')
    await server.wait_closed()

