

from pydantic import BaseModel
from oaas_sdk2_py import Oparaca, BaseObject, ObjectInvocationRequest

oaas = Oparaca()

async_sample_cls_meta = oaas.new_cls("TestAsync")


class Msg(BaseModel):
    msg: str


class Result(BaseModel):
    ok: bool
    msg: str


@async_sample_cls_meta
class AsyncSampleObj(BaseObject):    
    async def get_intro(self) -> str:
        raw = await self.get_data_async(0)
        return raw.decode("utf-8") if raw is not None else ""

    async def set_intro(self, data: str):
        await self.set_data_async(0, data.encode("utf-8"))
    
    @async_sample_cls_meta.func()
    async def greet(self) -> str:
        intro = await self.get_intro()
        return f"Hello, {intro}"

    @async_sample_cls_meta.func("fn-1")
    async def sample_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg=msg.msg)

    @async_sample_cls_meta.func()
    async def sample_fn2(self, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")

    @async_sample_cls_meta.func()
    async def sample_fn3(self, msg: Msg, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")
    
    @async_sample_cls_meta.func(serve_with_agent=True)
    async def local_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg="local fn")
    
    

sample_cls_meta = oaas.new_cls("Test")

@sample_cls_meta
class SampleObj(BaseObject):    
    def get_intro(self) -> str:
        raw = self.get_data(0)
        return raw.decode("utf-8") if raw is not None else ""

    def set_intro(self, data: str):
        self.set_data(0, data.encode("utf-8"))
    
    @sample_cls_meta.func()
    def greet(self) -> str:
        intro = self.get_intro()
        return f"Hello, {intro}"

    @sample_cls_meta.func("fn-1")
    def sample_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg=msg.msg)

    @sample_cls_meta.func()
    def sample_fn2(self, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")

    @sample_cls_meta.func()
    def sample_fn3(self, msg: Msg, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")
    
    @sample_cls_meta.func(serve_with_agent=True)
    def local_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg="local fn")