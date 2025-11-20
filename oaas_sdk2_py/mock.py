import builtins
import logging
from oprc_py.oprc_py import (
    InvocationRequest,
    InvocationResponse,
    ObjectData,
    ObjectInvocationRequest,
    ObjectMetadata,
)

from .object_ids import ensure_object_metadata_kwargs

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaas_sdk2_py.session import Session


class LocalDataManager:
    repo: dict[ObjectMetadata, ObjectData]

    def __init__(self):
        self.repo = {}

    async def get_obj_async(
        self, cls_id: str, partition_id: builtins.int, obj_id
    ) -> ObjectData:
        metadata = ObjectMetadata(
            **ensure_object_metadata_kwargs(
                cls_id=cls_id,
                partition_id=partition_id,
                object_id=obj_id,
            )
        )
        if metadata in self.repo:
            return self.repo[metadata].copy()
        raise KeyError(f"Object with metadata {metadata} not found")


    def get_obj(
        self, cls_id: str, partition_id: builtins.int, obj_id
    ) -> ObjectData:
        metadata = ObjectMetadata(
            **ensure_object_metadata_kwargs(
                cls_id=cls_id,
                partition_id=partition_id,
                object_id=obj_id,
            )
        )
        if metadata in self.repo:
            return self.repo[metadata].copy()
        raise KeyError(f"Object with metadata {metadata} not found")


    async def set_obj_move_async(self, obj: ObjectData) -> None:
        self.repo[obj.meta] = obj.copy()
        logging.info(f"Set object {obj.meta}")
        
    
    def set_obj_move(self, obj: ObjectData) -> None:
        self.repo[obj.meta] = obj.copy()
        logging.info(f"Set object {obj.meta}")
        
        
    def del_obj(
        self, cls_id: str, partition_id: builtins.int, obj_id
    ) -> None:
        metadata = ObjectMetadata(
            **ensure_object_metadata_kwargs(
                cls_id=cls_id,
                partition_id=partition_id,
                object_id=obj_id,
            )
        )
        if metadata in self.repo:
            self.repo.pop(metadata)
            logging.info(f"Deleted object {metadata}")
        else:
            raise KeyError(f"Object with metadata {metadata} not found")

    async def del_obj_async(
        self, cls_id: str, partition_id: builtins.int, obj_id
    ) -> None:
        metadata = ObjectMetadata(
            **ensure_object_metadata_kwargs(
                cls_id=cls_id,
                partition_id=partition_id,
                object_id=obj_id,
            )
        )
        if metadata in self.repo:
            self.repo.pop(metadata)
            logging.info(f"Deleted object {metadata}")
        else:
            raise KeyError(f"Object with metadata {metadata} not found")


class LocalRpcManager:
    session: "Session"

    async def invoke_fn_async(self, req: InvocationRequest) -> InvocationResponse:
        resp = await self.session.invoke_local_async(req)
        try:
            await self.session.commit_async()
        except Exception:
            pass
        return resp
    
    
    def invoke_fn(self, req: InvocationRequest) -> InvocationResponse:
        resp = self.session.invoke_local(req)
        try:
            self.session.commit()
        except Exception:
            pass
        return resp

    async def invoke_obj_async(self, req: ObjectInvocationRequest) -> InvocationResponse:
        resp = await self.session.invoke_local_async(req)
        try:
            await self.session.commit_async()
        except Exception:
            pass
        return resp
    
    
    def invoke_obj(self, req: ObjectInvocationRequest) -> InvocationResponse:
        resp = self.session.invoke_local(req)
        try:
            self.session.commit()
        except Exception:
            pass
        return resp
