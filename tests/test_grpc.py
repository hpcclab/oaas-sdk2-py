import unittest

import grpclib.client
from grpclib.client import Channel

from oaas_sdk2_py import start_grpc_server, ObjectInvocationRequest
from oaas_sdk2_py.pb.oprc import OprcFunctionStub
from .sample_cls import oaas

class TestStuff(unittest.IsolatedAsyncioTestCase):
    async def test_my_func(self):
        grpc_server = await start_grpc_server(oaas)
        async with Channel('127.0.0.1', 8080) as channel:
            oprc = OprcFunctionStub(channel)
            try:
                resp = await oprc.invoke_obj(ObjectInvocationRequest(cls_id="default.test", fn_id="fn-1", partition_id=0))
                print(resp)
            except grpclib.client.GRPCError as error:
                print(error)
        grpc_server.close()