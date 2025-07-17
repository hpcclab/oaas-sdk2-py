import logging
from typing import TYPE_CHECKING

from oprc_py.oprc_py import InvocationRequest, InvocationResponse, InvocationResponseCode, ObjectInvocationRequest

if TYPE_CHECKING:
    from oaas_sdk2_py.engine import Oparaca


class AsyncInvocationHandler:
    def __init__(self, oprc: 'Oparaca', **options):
        super().__init__(**options)
        self.oprc = oprc
        # Check if auto session manager is available
        self._use_auto_session_manager = hasattr(oprc, '_auto_session_manager') and oprc._auto_session_manager is not None

    async def invoke_fn(
        self, invocation_request: InvocationRequest
    ) -> InvocationResponse:
        logging.debug(
            "received InvocationRequest: cls_id=%s, fn_id=%s, partition_id=%s",
            invocation_request.cls_id,
            invocation_request.fn_id,
            invocation_request.partition_id,
        )
        try:
            if self._use_auto_session_manager:
                # Use auto session manager for session lifecycle
                session = self.oprc._auto_session_manager.get_session(invocation_request.partition_id)
            else:
                # Fallback to traditional session creation
                session = self.oprc.new_session(invocation_request.partition_id)
                
            resp = await session.invoke_local_async(invocation_request)
            
            # Always commit after function execution to maintain old behavior
            # This ensures state changes are persisted before response is sent
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
            if self._use_auto_session_manager:
                # Use auto session manager for session lifecycle
                session = self.oprc._auto_session_manager.get_session(invocation_request.partition_id)
            else:
                # Fallback to traditional session creation
                session = self.oprc.new_session(invocation_request.partition_id)
                
            resp = await session.invoke_local_async(invocation_request)
            
            # Always commit after function execution to maintain old behavior
            # This ensures state changes are persisted before response is sent
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
        # Check if auto session manager is available
        self._use_auto_session_manager = hasattr(oprc, '_auto_session_manager') and oprc._auto_session_manager is not None

    def invoke_fn(
        self, invocation_request: InvocationRequest
    ) -> InvocationResponse:
        logging.debug(
            "received InvocationRequest: cls_id=%s, fn_id=%s, partition_id=%s",
            invocation_request.cls_id,
            invocation_request.fn_id,
            invocation_request.partition_id,
        )
        try:
            if self._use_auto_session_manager:
                # Use auto session manager for session lifecycle
                session = self.oprc._auto_session_manager.get_session(invocation_request.partition_id)
            else:
                # Fallback to traditional session creation
                session = self.oprc.new_session(invocation_request.partition_id)
                
            resp = session.invoke_local(invocation_request)
            
            # Always commit after function execution to maintain old behavior
            # This ensures state changes are persisted before response is sent
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
            if self._use_auto_session_manager:
                # Use auto session manager for session lifecycle
                session = self.oprc._auto_session_manager.get_session(invocation_request.partition_id)
            else:
                # Fallback to traditional session creation
                session = self.oprc.new_session(invocation_request.partition_id)
                
            resp = session.invoke_local(invocation_request)
            
            # Always commit after function execution to maintain old behavior
            # This ensures state changes are persisted before response is sent
            session.commit()
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            return InvocationResponse(
                payload=str(e).encode(),
                status=int(InvocationResponseCode.AppError),
            )
        return resp
