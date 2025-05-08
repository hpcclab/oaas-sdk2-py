import logging
from typing import TYPE_CHECKING

from oprc_py.oprc_py import InvocationRequest, InvocationResponse, InvocationResponseCode, ObjectInvocationRequest

if TYPE_CHECKING:
    from oaas_sdk2_py.engine import Oparaca


class OprcFunction:
    def __init__(self, oprc: 'Oparaca', **options):
        super().__init__(**options)
        self.oprc = oprc

    async def invoke_fn(
        self, invocation_request: InvocationRequest
    ) -> InvocationResponse:
        logging.debug(
            "received ObjectInvocationRequest: cls_id=%s, fn_id=%s, partition_id=%s, object_id=%s",
            invocation_request.cls_id,
            invocation_request.fn_id,
            invocation_request.partition_id,
        )
        try:
            if invocation_request.cls_id not in self.oprc.meta_repo.cls_dict:
                return InvocationResponse(
                    payload=f"cls_id '{invocation_request.cls_id}' not found".encode(),
                    status=int(InvocationResponseCode.InvalidRequest),
                )

            meta = self.oprc.meta_repo.get_cls_meta(invocation_request.cls_id)
            if invocation_request.fn_id not in meta.func_list:
                return InvocationResponse(
                    payload=f"fn_id '{invocation_request.fn_id}' not found".encode(),
                    status=int(InvocationResponseCode.InvalidRequest),
                )
            fn_meta = meta.func_list[invocation_request.fn_id]
            ctx = self.oprc.new_session()
            obj = ctx.create_object(meta)
            resp = await fn_meta.caller(obj, invocation_request)
            await ctx.commit()
            return resp
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            # raise GRPCError(Status.INTERNAL, str(e))
            return InvocationResponse(
                payload=str(e).encode(),
                status=int(InvocationResponseCode.AppError),
            )

    async def invoke_obj(
        self, invocation_request: "ObjectInvocationRequest"
    ) -> InvocationResponse:
        logging.debug(
            "received ObjectInvocationRequest: cls_id=%s, fn_id=%s, partition_id=%s, object_id=%s",
            invocation_request.cls_id,
            invocation_request.fn_id,
            invocation_request.partition_id,
            invocation_request.object_id,
        )
        try:
            if invocation_request.cls_id not in self.oprc.meta_repo.cls_dict:
                return InvocationResponse(
                    payload=f"cls_id '{invocation_request.cls_id}' not found".encode(),
                    status=int(InvocationResponseCode.InvalidRequest),
                )

            meta = self.oprc.meta_repo.get_cls_meta(invocation_request.cls_id)
            if invocation_request.fn_id not in meta.func_list:
                return InvocationResponse(
                    payload=f"fn_id '{invocation_request.fn_id}' not found".encode(),
                    status=int(InvocationResponseCode.InvalidRequest),
                )
            fn_meta = meta.func_list[invocation_request.fn_id]
            ctx = self.oprc.new_session(invocation_request.partition_id)
            obj = ctx.create_object(meta, invocation_request.object_id)
            resp = await fn_meta.caller(obj, invocation_request)
            await ctx.commit()
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            return InvocationResponse(
                payload=str(e).encode(),
                status=int(InvocationResponseCode.AppError),
            )
        return resp
