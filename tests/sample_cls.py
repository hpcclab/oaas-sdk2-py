from pydantic import BaseModel
from oaas_sdk2_py import Oparaca, BaseObject, ObjectInvocationRequest
from oaas_sdk2_py.engine import Session
from oaas_sdk2_py.model import ObjectMeta

oaas = Oparaca()

test = oaas.new_cls("test")


class Msg(BaseModel):
    msg: str


class Result(BaseModel):
    ok: bool
    msg: str


@test
class SampleObj(BaseObject):
    def __init__(self, meta: ObjectMeta = None, ctx: Session = None):
        super().__init__(meta, ctx)

    @test.data_getter(index=0)
    async def get_intro(self, raw: bytes = None) -> str:
        return raw.decode("utf-8")

    @test.data_setter(index=0)
    async def set_intro(self, data: str) -> bytes:
        return data.encode("utf-8")

    @test.func("fn-1")
    async def sample_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg=msg.msg)

    @test.func()
    async def sample_fn2(self, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")

    @test.func()
    async def sample_fn3(self, msg: Msg, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")
