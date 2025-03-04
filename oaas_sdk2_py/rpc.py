from pydantic.v1 import HttpUrl
from oaas_sdk2_py.pb.oprc import (
    InvocationRequest,
    InvocationResponse,
    ObjectInvocationRequest,
    OprcFunctionStub,
)
from grpclib.client import Channel


class ArgWrapper:
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs


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

        # o1 = class1()
        # o1.state = class2()
        # o1.foo = fn {
        #     var o2 = Oparaca.load(o1.state.id);
        #     var out = o2.bar("...")
        #     ....
        #     o1.state = ...
        # }
