import unittest

import grpclib.client
from grpclib.client import Channel

from oaas_sdk2_py import start_grpc_server, ObjectInvocationRequest
from oaas_sdk2_py.pb.oprc import OprcFunctionStub
from .sample_cls import oaas

class TestStuff(unittest.IsolatedAsyncioTestCase):
    async def test_my_func(self):
        port=28080
        grpc_server = await start_grpc_server(oaas, port=port)
        async with Channel('127.0.0.1', port) as channel:
            oprc = OprcFunctionStub(channel)
            try:
                resp = await oprc.invoke_obj(ObjectInvocationRequest(cls_id="default.test", fn_id="fn-1", partition_id=0, payload=b'{"msg": "hello"}'))
                print(resp)
                resp = await oprc.invoke_obj(ObjectInvocationRequest(cls_id="default.test", fn_id="sample_fn2", partition_id=0, object_id=0, payload=b'{"msg": "hello"}'))
                print(resp)
                resp = await oprc.invoke_obj(ObjectInvocationRequest(cls_id="default.test", fn_id="sample_fn3", partition_id=0, object_id=0, payload=b'{"msg": "hello"}'))
                print(resp)
            except grpclib.client.GRPCError as error:
                print(error)
        grpc_server.close()