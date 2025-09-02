from pydantic import BaseModel
from oaas_sdk2_py import oaas, OaasObject, ObjectInvocationRequest


class Msg(BaseModel):
    msg: str


class Result(BaseModel):
    ok: bool
    msg: str


@oaas.service("TestAsync", package="test")
class AsyncSampleObj(OaasObject):
    intro: str = ""
    
    @oaas.getter("intro")
    async def get_intro(self) -> str:
        return self.intro

    @oaas.setter("intro")
    async def set_intro(self, value: str) -> str:
        self.intro = value
        return self.intro
    
    @oaas.method()
    async def greet(self) -> str:
        intro = await self.get_intro()
        return f"Hello, {intro}"

    @oaas.method(name="fn-1")
    async def sample_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg=msg.msg)

    @oaas.method()
    async def sample_fn2(self, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")

    @oaas.method()
    async def sample_fn3(self, msg: Msg, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")
    
    @oaas.method()
    async def dict_fn(self, data: dict) -> Result:
        """Test function that explicitly expects a dictionary input"""
        print(f"Received dict: {data}")
        message = data.get("message", "No message provided")
        return Result(ok=True, msg=f"Processed dict: {message}")

    @oaas.method()
    async def untyped_fn(self, data) -> Result:
        """Test function without type annotation (should be treated as dict)"""
        print(f"Received untyped data: {data}")
        if isinstance(data, dict):
            message = data.get("message", "No message in dict")
        else:
            message = str(data)
        return Result(ok=True, msg=f"Processed untyped: {message}")
    
    @oaas.method(serve_with_agent=True)
    async def local_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg="local fn")
    

@oaas.service("Test", package="test")
class SampleObj(OaasObject):
    intro: str = ""
    
    @oaas.getter("intro")
    async def get_intro(self) -> str:
        return self.intro

    @oaas.setter("intro")
    async def set_intro(self, value: str) -> str:
        self.intro = value
        return self.intro
    
    @oaas.method()
    async def greet(self) -> str:
        intro = await self.get_intro()
        return f"Hello, {intro}"

    @oaas.method(name="fn-1")
    async def sample_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg=msg.msg)

    @oaas.method()
    async def sample_fn2(self, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")

    @oaas.method()
    async def sample_fn3(self, msg: Msg, req: ObjectInvocationRequest) -> Result:
        print(req.payload)
        return Result(ok=True, msg="ok")
    
    @oaas.method()
    async def dict_fn(self, data: dict) -> Result:
        """Test function that explicitly expects a dictionary input"""
        print(f"Received dict: {data}")
        message = data.get("message", "No message provided")
        return Result(ok=True, msg=f"Processed dict: {message}")

    @oaas.method()
    async def untyped_fn(self, data) -> Result:
        """Test function without type annotation (should be treated as dict)"""
        print(f"Received untyped data: {data}")
        if isinstance(data, dict):
            message = data.get("message", "No message in dict")
        else:
            message = str(data)
        return Result(ok=True, msg=f"Processed untyped: {message}")
    
    @oaas.method(serve_with_agent=True)
    async def local_fn(self, msg: Msg) -> Result:
        print(msg)
        return Result(ok=True, msg="local fn")