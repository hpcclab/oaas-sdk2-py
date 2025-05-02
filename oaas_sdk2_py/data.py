import asyncio
import logging
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Optional, Dict

from grpclib.client import Channel
from pydantic.v1 import HttpUrl
import zenoh

from oaas_sdk2_py.pb.oprc import DataServiceStub, SingleKeyRequest, SetObjectRequest, ObjData, ValData, \
    SingleObjectRequest

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, addr: HttpUrl):
        channel = Channel(addr.host, int(addr.port))
        self.client = DataServiceStub(channel)

    async def get(self,
                  cls_id: str,
                  partition_id: int,
                  object_id: int,
                  key: int) -> Optional[bytes]:
        logger.debug("Getting data: cls_id=%s, partition_id=%s, object_id=%s, key=%s",
                    cls_id, partition_id, object_id, key)
        resp = await self.client.get_value(SingleKeyRequest(
            cls_id=cls_id,
            partition_id=partition_id,
            object_id=object_id,
            key=key,
        ))
        match resp.value:
            case ValData(byte=value):
                return value
            case ValData(crdt_map=value):
                return value

    async def get_all(self,
                      cls_id: str,
                      partition_id: int,
                      object_id: int) -> Optional[ObjData]:
        logger.debug("Getting all data: cls_id=%s, partition_id=%s, object_id=%s",
                    cls_id, partition_id, object_id)
        resp = await self.client.get(SingleKeyRequest(
            cls_id=cls_id,
            partition_id=partition_id,
            object_id=object_id,
        ))
        return resp.obj

    async def set_all(self,
                      cls_id: str,
                      partition_id: int,
                      object_id: int,
                      data: Dict[int, bytes]):
        logger.debug("Setting all: cls_id=%s, partition_id=%s, object_id=%s, setting %s keys, example keys=%s",
                     cls_id, partition_id, object_id, len(data), list(data.keys())[:5])
        obj = {k: ValData(byte=v) for k, v in data.items()}
        req = SetObjectRequest(
            cls_id=cls_id,
            partition_id=partition_id,
            object_id=object_id,
            object=ObjData(entries=obj)
        )
        await self.client.set(req)

    async def delete(self,
                     cls_id: str,
                     partition_id: int,
                     object_id: int):
        logger.debug("Deleting object: cls_id=%s, partition_id=%s, object_id=%s",
                     cls_id, partition_id, object_id)
        await self.client.delete(SingleObjectRequest(
            cls_id=cls_id,
            partition_id=partition_id,
            object_id=object_id,
        ))


class ZenohDataManager:
    session: zenoh.Session

    def __init__(self, z_session: zenoh.Session):
        self.session = z_session
        self.executor = ThreadPoolExecutor()

    async def get(self,
                  cls_id: str,
                  partition_id: int,
                  object_id: int,
                  key: int) -> Optional[bytes]:
        loop = asyncio.get_running_loop()
        obj = await loop.run_in_executor(self.executor, self._blocking_get_all, cls_id, partition_id, object_id)
        if obj is None:
            return None
        entries = obj.entries
        if key not in entries:
            logger.warning("Key not found: key=%s", key)
            return None
        match entries[key]:
            case ValData(byte=value):
                return value
            case ValData(crdt_map=value):
                return value

    async def get_all(self,
                      cls_id: str,
                      partition_id: int,
                      object_id: int) -> Optional[bytes]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._blocking_get_all, cls_id, partition_id, object_id)

    def _blocking_get_all(self,
                          cls_id: str,
                          partition_id: int,
                          object_id: int) -> Optional[ObjData]:
        logger.debug("Getting data: cls_id=%s, partition_id=%s, object_id=%s",
                        cls_id, partition_id, object_id)
        resp = self.session.get(f"oprc/{cls_id}/{partition_id}/objects/{object_id}")
        for reply in resp:
            sample = reply.ok
            if sample is not None:
                payload = sample.payload
                if payload is None:
                    logger.warning("No payload found")
                    return None
                b = payload.to_bytes()
                if len(b) == 0:
                    logger.debug("Empty payload")
                    return None
                obj = ObjData().parse(b)
                logger.debug("Received: object_id=%s, entries=%s",
                             obj.metadata.object_id, len(obj.entries))
                return obj
            else:
                logger.error("Error response: %s", reply.err.payload.to_string())
                return None

    async def set_all(self,
                      cls_id: str,
                      partition_id: int,
                      object_id: int,
                      data: Dict[int, bytes]):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self._blocking_set_all, cls_id, partition_id, object_id, data)

    def _blocking_set_all(self,
                          cls_id: str,
                          partition_id: int,
                          object_id: int,
                          data: Dict[int, bytes]):
        logger.debug("Setting all: cls_id=%s, partition_id=%s, object_id=%s, setting %s keys, example keys=%s",
                     cls_id, partition_id, object_id, len(data), list(data.keys())[:5])
        entries = {k: ValData(byte=v) for k, v in data.items()}
        obj = ObjData(entries=entries)
        payload = obj.__bytes__()
        resp = self.session.get(f"oprc/{cls_id}/{partition_id}/objects/{object_id}/set",
                                payload=payload)
        for reply in resp:
            try:
                logger.debug("Received Set response: key_expr=%s", reply.ok.key_expr)
                return
            except Exception:
                logger.error("Error response: %s", reply.err.payload.to_string())
        logger.error("No response received from set operation")
        

    async def delete(self,
                     cls_id: str,
                     partition_id: int,
                     object_id: int):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self._blocking_delete, cls_id, partition_id, object_id)

    def _blocking_delete(self,
                         cls_id: str,
                         partition_id: int,
                         object_id: int):
        resp = self.session.delete(f"oprc/{cls_id}/{partition_id}/objects/{object_id}")
        for reply in resp:
            try:
                logger.debug("Received: key_expr=%s, payload=%s",
                             reply.ok.key_expr, reply.ok.payload.to_string())
            except Exception:
                logger.error("Error response: %s", reply.err.payload.to_string())

class Ref:
    _cache: Optional[bytes] = None
    _dirty: bool = False

    def __init__(self,
                 cls_id: str,
                 partition_id: int,
                 object_id: int,
                 key: int,
                 data_manager: DataManager):
        self.cls_id = cls_id
        self.partition_id = partition_id
        self.object_id = object_id
        self.key = key
        self.data_manager = data_manager

    async def get(self) -> bytes:
        if self._cache is not None:
            return self._cache
        self._cache = await self.data_manager.get(self.cls_id, self.partition_id, self.object_id, self.key)
        return self._cache

    def set(self, data: bytes):
        self._cache = data
        self._dirty = True
