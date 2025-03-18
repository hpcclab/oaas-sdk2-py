import logging

from grpclib import Status, GRPCError
from grpclib.server import Server

from .engine import Oparaca, BaseObject
from .pb.oprc import OprcFunctionBase, InvocationRequest, InvocationResponse, ObjectInvocationRequest


class OprcFunction(OprcFunctionBase):
    def __init__(self, oprc: Oparaca, **options):
        super().__init__(**options)
        self.oprc = oprc

    async def invoke_fn(self, invocation_request: InvocationRequest) -> InvocationResponse:
        logging.debug(f"received {invocation_request}")
        try:
            if invocation_request.cls_id not in self.oprc.meta_repo.cls_dict:
                raise GRPCError(Status.NOT_FOUND, message=f"cls_id '{invocation_request.cls_id}' not found")
            meta = self.oprc.meta_repo.get_cls_meta(invocation_request.cls_id)
            logging.debug("func list %s", meta.func_list)
            if invocation_request.fn_id not in meta.func_list:
                raise GRPCError(Status.NOT_FOUND, message=f"fn_id '{invocation_request.fn_id}' not found")
            fn_meta = meta.func_list[invocation_request.fn_id]
            ctx = self.oprc.new_context()
            obj = ctx.create_empty_object(meta)
            resp = await fn_meta.caller(obj, invocation_request)
            await ctx.commit()
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            raise GRPCError(Status.INTERNAL, str(e))
        return resp

    async def invoke_obj(self, invocation_request: 'ObjectInvocationRequest') -> InvocationResponse:
        logging.debug(f"received {invocation_request}")
        try:
            if invocation_request.cls_id not in self.oprc.meta_repo.cls_dict:
                raise GRPCError(Status.NOT_FOUND, message=f"cls_id {invocation_request.cls_id} not found")
            meta = self.oprc.meta_repo.get_cls_meta(invocation_request.cls_id)
            if invocation_request.fn_id not in meta.func_list:
                raise GRPCError(Status.NOT_FOUND, message=f"fn_id {invocation_request.fn_id} not found")
            fn_meta = meta.func_list[invocation_request.fn_id]
            ctx = self.oprc.new_context(invocation_request.partition_id)
            obj = ctx.create_object(meta, invocation_request.object_id)
            resp = await fn_meta.caller(obj, invocation_request)
            await ctx.commit()
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            raise GRPCError(Status.INTERNAL, str(e))
        return resp

async def start_grpc_server(oprc: Oparaca,
                            port=8080) -> Server:
    oprc.init()
    grpc_server = Server([OprcFunction(oprc)])
    await grpc_server.start("0.0.0.0", port)
    return grpc_server
