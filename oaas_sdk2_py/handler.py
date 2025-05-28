import logging
from typing import TYPE_CHECKING

from oprc_py.oprc_py import InvocationRequest, InvocationResponse, InvocationResponseCode, ObjectInvocationRequest

if TYPE_CHECKING:
    from oaas_sdk2_py.engine import Oparaca


class AsyncInvocationHandler:
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
            session = self.oprc.new_session(invocation_request.partition_id)
            resp = await session.invoke_local_async(invocation_request)
            await session.commit_async()
            return resp
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
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
            session = self.oprc.new_session(invocation_request.partition_id)
            resp = await session.invoke_local_async(invocation_request)
            await session.commit_async()
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            return InvocationResponse(
                payload=str(e).encode(),
                status=int(InvocationResponseCode.AppError),
            )
        return resp



class SyncInvocationHandler:
    def __init__(self, oprc: 'Oparaca', **options):
        super().__init__(**options)
        self.oprc = oprc

    def invoke_fn(
        self, invocation_request: InvocationRequest
    ) -> InvocationResponse:
        logging.debug(
            "received ObjectInvocationRequest: cls_id=%s, fn_id=%s, partition_id=%s, object_id=%s",
            invocation_request.cls_id,
            invocation_request.fn_id,
            invocation_request.partition_id,
        )
        try:
            session = self.oprc.new_session(invocation_request.partition_id)
            resp = session.invoke_local_async(invocation_request)
            session.commit()
            return resp
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            return InvocationResponse(
                payload=str(e).encode(),
                status=int(InvocationResponseCode.AppError),
            )

    def invoke_obj(
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
            session = self.oprc.new_session(invocation_request.partition_id)
            resp = session.invoke_local_async(invocation_request)
            session.commit()
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            return InvocationResponse(
                payload=str(e).encode(),
                status=int(InvocationResponseCode.AppError),
            )
        return resp
