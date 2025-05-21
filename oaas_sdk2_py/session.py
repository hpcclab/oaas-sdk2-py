from typing import Dict

import oprc_py

from oprc_py.oprc_py import InvocationResponse, InvocationResponseCode
from tsidpy import TSID
from oprc_py import ObjectMetadata, RpcManager, DataManager
import logging 

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .obj import BaseObject
    from .model import ClsMeta
    from .repo import MetadataRepo


class Session:
    """
    Session manages the lifecycle of objects within the OAAS system.
    
    It handles object creation, loading, and RPC invocations, while keeping track of
    local and remote objects. The session also provides transaction capabilities
    through its commit method.
    
    Attributes:
        local_obj_dict: Dictionary tracking locally created objects
        remote_obj_dict: Dictionary tracking remote objects
        delete_obj_dict: Set tracking objects marked for deletion
        partition_id: ID of the partition this session belongs to
        rpc_manager: Manager for remote procedure calls
        data_manager: Manager for object data persistence
        meta_repo: Repository for class metadata
        local_only: Flag indicating if all objects should be local only
    """
    local_obj_dict: Dict['ObjectMetadata', 'BaseObject']
    remote_obj_dict: Dict['ObjectMetadata', 'BaseObject']
    delete_obj_set: set['ObjectMetadata']

    def __init__(
        self,
        partition_id: int,
        rpc_manager: 'RpcManager',
        data_manager: 'DataManager',
        meta_repo: 'MetadataRepo',
        local_only: bool = False,
    ):
        self.partition_id = partition_id
        self.rpc_manager = rpc_manager
        self.data_manager = data_manager
        self.meta_repo = meta_repo
        self.local_obj_dict = {}
        self.remote_obj_dict = {}
        self.delete_obj_set = set()
        self.local_only = local_only

    def create_object(
        self,
        cls_meta: 'ClsMeta',
        obj_id: int = None,
        local: bool = False,
    ):
        """
        Creates a new object instance of the specified OaaS class.
        
        Args:
            cls_meta: Metadata of the class to instantiate
            obj_id: Optional object ID (generates one if not provided)
            local: Whether the object should be local (not remote)
            
        Returns:
            The newly created object instance
        """
        if obj_id is None:
            obj_id = TSID.create().number
        remote=not (local or self.local_only)
        meta = ObjectMetadata(
            cls_id=cls_meta.cls_id,
            partition_id=self.partition_id,
            object_id=obj_id,
        )
        obj: BaseObject = cls_meta.cls(meta=meta, session=self)
        obj._remote = remote
        if remote:
            self.remote_obj_dict[meta] = obj
        else:
            self.local_obj_dict[meta] = obj
        return obj

    def load_object(self, cls_meta: 'ClsMeta', obj_id: int):
        """
        Loads an existing remote object by its ID.

        Args:
            cls_meta: Metadata of the class to instantiate
            obj_id: ID of the object to load

        Returns:
            The loaded object instance
        """
        meta = ObjectMetadata(
            cls_id=cls_meta.cls_id,
            partition_id=self.partition_id,
            object_id=obj_id,
        )
        obj = cls_meta.cls(meta=meta, session=self)
        obj._remote = True
        self.remote_obj_dict[meta] = obj
        return obj

    def delete_object(self, cls_meta: 'ClsMeta', obj_id: int, partition_id: int = None):
        """
        Marks an object for deletion.

        Args:
            cls_meta: Metadata of the class to instantiate
            obj_id: ID of the object to delete
        """
        partition_id = partition_id if partition_id is not None else self.partition_id
        meta = ObjectMetadata(
            cls_id=cls_meta.cls_id,
            partition_id=self.partition_id,
            object_id=obj_id,
        )
        self.delete_obj_set.add(meta)

    async def obj_rpc(
        self,
        req: oprc_py.ObjectInvocationRequest,
    ) -> oprc_py.InvocationResponse:
        """
        Performs a remote procedure call on an object.

        Args:
            req: The object invocation request

        Returns:
            The invocation response
        """
        return await self.rpc_manager.invoke_obj(req)

    async def fn_rpc(
        self,
        req: oprc_py.InvocationRequest,
    ) -> oprc_py.InvocationResponse:
        """
        Performs a remote procedure call on a function.

        Args:
            req: The function invocation request

        Returns:
            The invocation response
        """
        return await self.rpc_manager.invoke_fn(req)
    
    async def invoke_local(self, req: oprc_py.InvocationRequest | oprc_py.ObjectInvocationRequest) -> oprc_py.InvocationResponse:
        """
        Invokes a function locally without going through RPC.

        Handles both object method invocation and static function invocation
        based on the request type.

        Args:
            req: Either an InvocationRequest (static function) or ObjectInvocationRequest (method)

        Returns:
            The invocation response

        Raises:
            TypeError: If the request type is invalid
        """
        cls_meta = self.meta_repo.get_cls_meta(req.cls_id)
        if cls_meta is None:
            return InvocationResponse(
                payload=f"cls_id '{req.cls_id}' not found".encode(),
                status=int(InvocationResponseCode.InvalidRequest),
            )
        fn_meta = cls_meta.func_dict.get(req.fn_id)
        if fn_meta is None:
            return InvocationResponse(
                payload=f"fn_id '{req.fn_id}' not found".encode(),
                status=int(InvocationResponseCode.InvalidRequest),
            )
        if isinstance(req, oprc_py.InvocationRequest):
            obj = self.create_object(cls_meta, local=True)
            resp = await fn_meta.invoke_handler(obj, req)
            return resp
            
        elif isinstance(req, oprc_py.ObjectInvocationRequest):
            obj = self.load_object(cls_meta, obj_id=req.object_id)
            resp = await fn_meta.invoke_handler(obj, req)
            return resp
        else:
            raise TypeError("Invalid request type")

    async def commit(self):
        """
        Commits all changes in the current session.

        This method persists all dirty objects to storage and deletes
        objects marked for deletion. After a successful commit, the objects'
        dirty flags are cleared and deleted objects are removed from tracking.
        """
        for k, v in self.local_obj_dict.items():
            logging.debug(
                "check of committing [%s, %s, %s, %s]",
                v.meta.cls_id,
                v.meta.partition_id,
                v.meta.object_id,
                v.dirty,
            )
            if v.dirty:
                await self.data_manager.set_obj(
                    cls_id=v.meta.cls_id,
                    partition_id=v.meta.partition_id,
                    object_id=v.meta.object_id,
                    data=v.state,
                )
                v._dirty = False
        while self.delete_obj_set:
            meta = self.delete_obj_set.pop()
            logging.debug(
                "deleting [%s, %s, %s]",
                meta.cls_id,
                meta.partition_id,
                meta.object_id,
            )
            await self.data_manager.del_obj(
                cls_id=meta.cls_id,
                partition_id=meta.partition_id,
                obj_id=meta.object_id,
            )
