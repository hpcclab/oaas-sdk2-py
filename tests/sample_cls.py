

from pydantic import BaseModel
from oaas_sdk2_py import Oparaca, BaseObject, ObjectInvocationRequest

oaas = Oparaca()

sample_cls_meta = oaas.new_cls("test")


class Msg(BaseModel):
    msg: str


class Result(BaseModel):
    ok: bool
    msg: str


@sample_cls_meta
class SampleObj(BaseObject):    
    async def get_intro(self) -> str:
        raw = await self.get_data(0)
        return raw.decode("utf-8") if raw is not None else ""

    async def set_intro(self, data: str):
        await self.set_data(0, data.encode("utf-8"))
    
    @sample_cls_meta.func()
    async def greet(self) -> str:
        intro = await self.get_intro()
        return f"Hello, {intro}"

    @sample_cls_meta.func("fn-1")
    async def sample_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg=msg.msg)

    @sample_cls_meta.func()
    async def sample_fn2(self, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")

    @sample_cls_meta.func()
    async def sample_fn3(self, msg: Msg, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")
    
    @sample_cls_meta.func(serve_with_agent=True)
    async def local_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg="local fn")