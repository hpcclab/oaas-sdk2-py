import logging
from typing import Optional, Dict
from urllib.parse import urlparse

from grpclib.client import Channel
from pydantic.v1 import HttpUrl
import zenoh

from oaas_sdk2_py.pb.oprc import DataServiceStub, SingleKeyRequest, SetObjectRequest, ObjData, ValData, \
    SingleObjectRequest

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, addr: HttpUrl ):
        channel = Channel(addr.host, int(addr.port))
        self.client = DataServiceStub(channel)

    async def get(self,
                  cls_id: str,
                  partition_id: int,
                  object_id: int,
                  key: int, ) -> Optional[bytes]:
        logger.info("get data %s %s %s %s", cls_id, partition_id, object_id, key)
        resp = await self.client.get_value(SingleKeyRequest(
            cls_id=cls_id,
            partition_id=partition_id,
            object_id=object_id,
            key=key,
        ))
        logger.info("resp %s", resp)
        match resp.value:
            case ValData(byte=value):
                return value
            case ValData(crdt_map=value):
                return value


    async def set_all(self,
                      cls_id: str,
                      partition_id: int,
                      object_id: int,
                      data: Dict[int, bytes], ):
        logger.info("data %s", data)
        obj = dict((k, ValData(byte=v)) for (k,v) in data.items())
        req = SetObjectRequest(
            cls_id=cls_id,
            partition_id=partition_id,
            object_id=object_id,
            object= ObjData(
                entries=obj
            )
        )
        await self.client.set(req)


    async def delete(self,
                     cls_id: str,
                     partition_id: int,
                     object_id: int):
        await self.client.delete(SingleObjectRequest(
            cls_id=cls_id,
            partition_id=partition_id,
            object_id=object_id,)
        )
        
        

class ZenohDataManager:
    session: zenoh.Session
    
    def __init__(self):
        self.session = zenoh.open(config=zenoh.Config()) 

    async def get(self,
                  cls_id: str,
                  partition_id: int,
                  object_id: int,
                  key: int, ) -> Optional[bytes]:
        logger.info("get data %s %s %s %s", cls_id, partition_id, object_id, key)
        resp = self.session.get(f"oprc/{cls_id}/{partition_id}/objects/{object_id}").recv
        
        logger.info("resp %s", resp)
        resp = resp.ok
        payload = resp.payload
        obj = ObjData.parse(payload)
        val = obj.entries[key]
        match val:
            case ValData(byte=value):
                return value
            case ValData(crdt_map=value):
                return value


    async def set_all(self,
                      cls_id: str,
                      partition_id: int,
                      object_id: int,
                      data: Dict[int, bytes], ):
        logger.info("data %s", data)
        entries = dict((k, ValData(byte=v)) for (k,v) in data.items())
        obj = ObjData(
                entries=entries
            )
        payload = obj.__bytes__();
        resp = self.session.get(f"oprc/{cls_id}/{partition_id}/objects/{object_id}/set",
                                payload=payload).recv
        logger.info("resp %s", resp)
        


    async def delete(self,
                     cls_id: str,
                     partition_id: int,
                     object_id: int):
        self.session.delete(f"oprc/{cls_id}/{partition_id}/objects/{object_id}")
        
        





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
