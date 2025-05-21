import builtins
import logging
from oprc_py.oprc_py import (
    InvocationRequest,
    InvocationResponse,
    ObjectData,
    ObjectInvocationRequest,
    ObjectMetadata,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaas_sdk2_py.session import Session


class LocalDataManager:
    repo: dict[ObjectMetadata, ObjectData]

    def __init__(self):
        self.repo = {}

    async def get_obj(
        self, cls_id: str, partition_id: builtins.int, obj_id: builtins.int
    ) -> ObjectData:
        metadata = ObjectMetadata(cls_id, partition_id, obj_id)
        if metadata in self.repo:
            return self.repo[metadata].copy()
        raise KeyError(f"Object with metadata {metadata} not found")

    async def set_obj(self, obj: ObjectData) -> None:
        self.repo[obj.meta] = obj.copy()
        logging.info(f"Set object {obj.meta}")

    async def del_obj(
        self, cls_id: str, partition_id: builtins.int, obj_id: builtins.int
    ) -> None:
        metadata = ObjectMetadata(cls_id, partition_id, obj_id)
        if metadata in self.repo:
            self.repo.pop(metadata)
            logging.info(f"Deleted object {metadata}")
        else:
            raise KeyError(f"Object with metadata {metadata} not found")


class MockRpcManager:
    session: "Session"

    async def invoke_fn(self, req: InvocationRequest) -> InvocationResponse:
        return await self.session.invoke_local(req)

    async def invoke_obj(self, req: ObjectInvocationRequest) -> InvocationResponse:
        return await self.session.invoke_local(req)
