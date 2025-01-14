from typing import Any

import grpc

from oaas_sdk2_py.model import ObjectMeta
from oaas_sdk2_py.pb.oprc import ObjectInvocationRequest


class ArgWrapper:
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

class RpcManager:
    def __init__(self):
        self.gateway_addr = "http://127.0.0.1:8000"

    def rpc_call(self,
                 obj_meta: ObjectMeta,
                 fn_name: str,
                 req: ObjectInvocationRequest,):
        print("target:", obj_meta)
        print("fn_name:", fn_name)
        print("req:", req)
        return {}

    def resolve_addr(self,
                     obj_meta: ObjectMeta,
                     fn: str) -> str:
        return (f"{self.gateway_addr}/class/{obj_meta.cls}"
                f"/partitions/{obj_meta.partition_id}"
                f"/obj/{obj_meta.obj_id}/func/{fn}")
        
        
        
        # o1 = class1()
        # o1.state = class2()
        # o1.foo = fn {
        #     var o2 = Oparaca.load(o1.state.id);
        #     var out = o2.bar("...")
        #     ....
        #     o1.state = ...
        #} 