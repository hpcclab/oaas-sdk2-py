import functools
from collections.abc import Callable
from typing import Optional, Any

import tsidpy

from oaas_sdk2_py.pb.oprc import ObjectInvocationRequest


def create_obj_meta(
        cls: str,
        partition_id: int,
        obj_id: int = None, ):
    oid = obj_id if obj_id is not None else tsidpy.TSID.create().number
    return ObjectMeta(
        obj_id=oid,
        cls=cls,
        partition_id=partition_id if partition_id is not None else -1
    )


class ObjectMeta:

    def __init__(self,
                 cls: str,
                 partition_id: int,
                 obj_id: Optional[int] = None,
                 remote = False):
        self.cls = cls
        self.obj_id = obj_id
        self.partition_id = partition_id
        self.remote = remote


class FuncMeta:
    def __init__(self,
                 func,
                 stateless=False):
        self.func = func
        self.stateless = stateless

class StateMeta:
    setter: Callable
    getter: Callable
    def __init__(self,
                 index: int,
                 name: Optional[str] = None):
        self.index = index
        self.name = name

class ClsMeta:
    func_list: dict[str, FuncMeta] = {}
    state_list: dict[int, StateMeta] = {}

    def __init__(self,
                 name: Optional[str],
                 pkg: str = "default",
                 update: Callable = None):
        self.name = name
        self.pkg = pkg
        self.cls_id = f"{pkg}.{name}"
        self.update = update

    def __call__(self, cls):
        if self.name is None or self.name == '':
            self.name = cls.__name__
        self.cls = cls
        if self.update is not None:
            self.update(self)
        return cls

    def func(self, name="", stateless=False):
        def decorator(function):
            fn_name = name if len(name) != 0 else function.__name__

            @functools.wraps(function)
            def wrapper(obj_self, req: 'ObjectInvocationRequest'):
                if obj_self.remote:
                    return obj_self.ctx.rpc_call(obj_self,
                                                 fn_name,
                                                 req)
                else:
                    return function(obj_self, req)

            self.func_list[fn_name] = FuncMeta(wrapper, stateless=stateless)
            return wrapper

        return decorator

    def data_setter(self, index: int, name=None):
        def decorator(function):
            @functools.wraps(function)
            async def wrapper(obj_self, input: Any):
                raw = await function(obj_self, input)
                obj_self.set_data(index, raw)
                return raw
            if index in self.state_list:
                meta = self.state_list[index]
            else:
                meta = StateMeta(index=index, name=name)
                self.state_list[index] = meta
            meta.setter = wrapper
            return wrapper

        return decorator

    def data_getter(self, index: int, name=None):
        def decorator(function):
            @functools.wraps(function)
            async def wrapper(obj_self):
                raw = await obj_self.get_data(index)
                data = await function(obj_self, raw)
                return data
            if index in self.state_list:
                meta = self.state_list[index]
            else:
                meta = StateMeta(index=index, name=name)
                self.state_list[index] = meta
            meta.getter = wrapper
            return wrapper
        return decorator

    def add_data(self, index: int, name=None):
        self.state_list[index] = StateMeta(index=index, name=name)




    def __str__(self):
        return '{' + f"name={self.name}, func_list={self.func_list}" + '}'

    def export_pkg(self, pkg:dict) -> dict[str, Any]:

        fb_list = []
        for k, f in self.func_list.items():
            fb_list.append({
                "name": k,
                "function": "." + k
            })
        cls = {"name": self.name, "functions": fb_list}
        pkg['classes'].append(cls)

        for k, f in self.func_list.items():
            pkg['functions'].append({
                "name": k,
                "provision": {}
            })
        return pkg
