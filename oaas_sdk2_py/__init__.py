import logging
import sys
import traceback

from grpclib import Status, GRPCError
from grpclib.server import Server

from .engine import Oparaca
from .pb.oprc import OprcFunctionBase, InvocationRequest, InvocationResponse, ObjectInvocationRequest


class OprcFunction(OprcFunctionBase):
    def __init__(self, oprc: Oparaca, **options):
        super().__init__(**options)
        self.oprc = oprc

    async def invoke_fn(self, invocation_request: InvocationRequest) -> InvocationResponse:
        print(f"received {invocation_request}")
        try:
            meta = self.oprc.meta_repo.get_cls_meta(invocation_request.cls_id)
            fn_meta = meta.func_list[invocation_request.fn_id]
            if fn_meta is None:
                raise GRPCError(Status.NOT_FOUND)
            ctx = self.oprc.new_context()
            obj = ctx.create_empty_object(meta)
            resp = await fn_meta.func(obj, invocation_request)
            await ctx.commit()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            raise GRPCError(Status.INTERNAL, str(e))
        return resp

    async def invoke_obj(self, invocation_request: 'ObjectInvocationRequest') -> InvocationResponse:
        print(f"received {invocation_request}")
        try:
            meta = self.oprc.meta_repo.get_cls_meta(invocation_request.cls_id)
            fn_meta = meta.func_list[invocation_request.fn_id]
            if fn_meta is None:
                raise GRPCError(Status.NOT_FOUND)
            ctx = self.oprc.new_context(invocation_request.partition_id)
            obj = ctx.create_object(meta, invocation_request.object_id)
            resp = await fn_meta.func(obj, invocation_request)
            await ctx.commit()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            raise GRPCError(Status.INTERNAL, str(e))
        return resp

async def start_grpc_server(oprc: Oparaca,
                            port=8080) -> Server:
    oprc.init()
    grpc_server = Server([OprcFunction(oprc)])
    await grpc_server.start("0.0.0.0", port)
    return grpc_server
