import functools
from collections.abc import Callable
import inspect
from typing import Optional, Any

from pydantic import BaseModel
import tsidpy

from oaas_sdk2_py.pb.oprc import (
    InvocationRequest,
    InvocationResponse,
    ObjectInvocationRequest,
    ResponseStatus,
)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from oaas_sdk2_py.engine import BaseObject


def create_obj_meta(
    cls: str,
    partition_id: int,
    obj_id: int = None,
):
    oid = obj_id if obj_id is not None else tsidpy.TSID.create().number
    return ObjectMeta(
        obj_id=oid,
        cls=cls,
        partition_id=partition_id if partition_id is not None else -1,
    )


class ObjectMeta:
    def __init__(
        self, cls: str, partition_id: int, obj_id: Optional[int] = None, remote=False
    ):
        self.cls = cls
        self.obj_id = obj_id
        self.partition_id = partition_id
        self.remote = remote


class FuncMeta:
    def __init__(
        self,
        func,
        caller: Callable,
        signature: inspect.Signature,
        stateless=False,
    ):
        self.func = func
        self.caller = caller
        self.signature = signature
        self.stateless = stateless


class StateMeta:
    setter: Callable
    getter: Callable

    def __init__(self, index: int, name: Optional[str] = None):
        self.index = index
        self.name = name


def parse_resp(resp) -> InvocationResponse:
    if resp is None:
        return InvocationResponse(status=ResponseStatus.OKAY)
    elif isinstance(resp, InvocationResponse):
        return resp
    elif isinstance(resp, BaseModel):
        b = resp.model_dump_json().encode()
        return InvocationResponse(status=ResponseStatus.OKAY, payload=b)
    elif isinstance(resp, bytes):
        return InvocationResponse(status=ResponseStatus.OKAY, payload=resp)
    elif isinstance(resp, str):
        return InvocationResponse(status=ResponseStatus.OKAY, payload=resp.encode())


class ClsMeta:
    func_list: dict[str, FuncMeta]
    state_list: dict[int, StateMeta]

    def __init__(
        self, name: Optional[str], pkg: str = "default", update: Callable = None
    ):
        self.name = name
        self.pkg = pkg
        self.cls_id = f"{pkg}.{name}"
        self.update = update
        self.func_list = {}
        self.state_list = {}

    def __call__(self, cls):
        """
        Make the ClsMeta instance callable to work as a class decorator.
        
        Args:
            cls: The class being decorated
            
        Returns:
            The decorated class
        """
        if self.name is None or self.name == "":
            self.name = cls.__name__
        self.cls = cls
        if self.update is not None:
            self.update(self)
        return cls

    def func(self, name="", stateless=False, strict=False):
        """
        Decorator for registering class methods as invokable functions in OaaS platform.
        
        Args:
            name: Optional function name override. Defaults to the method's original name.
            stateless: Whether the function doesn't modify object state.
            strict: Whether to use strict validation when deserializing models.
            
        Returns:
            A decorator function that wraps the original method
        """
        
        def decorator(function):
            """
            Inner decorator that wraps the class method.
            
            Args:
                function: The method to wrap
                
            Returns:
                The wrapped method
            """
            fn_name = name if len(name) != 0 else function.__name__
            sig = inspect.signature(function)

            @functools.wraps(function)
            async def wrapper(obj_self, *args, **kwargs):
                """
                Wrapper function that handles remote/local method invocation.
                
                Args:
                    obj_self: The object instance
                    *args: Positional arguments
                    **kwargs: Keyword arguments
                    
                Returns:
                    The result of the function call or a response object
                """
                if obj_self.remote:
                    if stateless:
                        req = self._extract_request(obj_self, fn_name, args, kwargs, stateless)
                        resp = await obj_self.ctx.fn_rpc(req)              
                    else:
                        req = self._extract_request(obj_self, fn_name, args, kwargs, stateless)
                        resp =  await obj_self.ctx.obj_rpc(req)
                    if issubclass(sig.return_annotation, BaseModel):
                        return sig.return_annotation.model_validate_json(resp.payload, strict=strict)
                    else:
                        return resp
                else:
                    return await function(obj_self, *args, **kwargs)

            caller = self._create_caller(function, sig, strict)
            self.func_list[fn_name] = FuncMeta(
                wrapper, caller=caller, signature=sig, stateless=stateless
            )
            return wrapper

        return decorator
    
    def _extract_request(self, obj_self, fn_name, args, kwargs, stateless) -> (InvocationRequest| ObjectInvocationRequest| None):
        """Extract or create a request object from function arguments."""
        # Try to find an existing request object
        req = self._find_request_object(args, kwargs)
        if req is not None:
            return req
        
        # Try to find a BaseModel to create a request
        model = self._find_base_model(args, kwargs)
        return self._create_request_from_model(obj_self, fn_name, model, stateless)
    
    
    def _find_request_object(self, args, kwargs) -> (InvocationRequest| ObjectInvocationRequest| None):
        """Find InvocationRequest or ObjectInvocationRequest in args or kwargs."""
        # Check in args first
        for arg in args:
            if isinstance(arg, (InvocationRequest, ObjectInvocationRequest)):
                return arg
        
        # Then check in kwargs
        for _, val in kwargs.items():
            if isinstance(val, (InvocationRequest, ObjectInvocationRequest)):
                return val
        
        return None
    
    def _find_base_model(self, args, kwargs):
        """Find BaseModel instance in args or kwargs."""
        # Check in args first
        for arg in args:
            if isinstance(arg, BaseModel):
                return arg
        
        # Then check in kwargs
        for _, val in kwargs.items():
            if isinstance(val, BaseModel):
                return val
        
        return None
    
    def _create_request_from_model(self, obj_self: "BaseObject", fn_name: str, model: BaseModel, stateless: bool):
        """Create appropriate request object from a BaseModel."""
        if model is None:
            if stateless:
                return obj_self.create_request(fn_name)
            else:
                return obj_self.create_obj_request(fn_name)
        payload = model.model_dump_json().encode()
        if stateless:
            return obj_self.create_request(fn_name, payload=payload)
        else:
            return obj_self.create_obj_request(fn_name, payload=payload)
    
    def _create_caller(self, function, sig, strict):
        """Create the appropriate caller function based on the signature."""
        param_count = len(sig.parameters)
        
        if param_count == 1:  # Just self
            return self._create_no_param_caller(function)
        elif param_count == 2:
            return self._create_single_param_caller(function, sig, strict)
        elif param_count == 3:
            return self._create_dual_param_caller(function, sig, strict)
        else:
            raise ValueError(f"Unsupported parameter count: {param_count}")
    
    def _create_no_param_caller(self, function):
        """Create caller for functions with no parameters."""
        @functools.wraps(function)
        async def caller(obj_self, req):
            result = await function(obj_self)
            return parse_resp(result)
        return caller
    
    def _create_single_param_caller(self, function, sig, strict):
        """Create caller for functions with a single parameter."""
        second_param = list(sig.parameters.values())[1]
        
        if issubclass(second_param.annotation, BaseModel):
            model_cls = second_param.annotation
            @functools.wraps(function)
            async def caller(obj_self, req):
                model = model_cls.model_validate_json(req.payload, strict=strict)
                result = await function(obj_self, model)
                return parse_resp(result)
            return caller
        elif (second_param.annotation == InvocationRequest or 
                second_param.annotation == ObjectInvocationRequest):
            @functools.wraps(function)
            async def caller(obj_self, req):
                resp = await function(obj_self, req)
                return parse_resp(resp)
            return caller
        elif issubclass(second_param.annotation, bytes):
            @functools.wraps(function)
            async def caller(obj_self, req):
                resp = await function(obj_self, req.payload)
                return parse_resp(resp)
            return caller
        elif issubclass(second_param.annotation, str):
            @functools.wraps(function)
            async def caller(obj_self, req):
                resp = await function(obj_self, req.payload.decode())
                return parse_resp(resp)
            return caller
        else:
            raise ValueError(f"Unsupported parameter type: {second_param.annotation}")
    
    def _create_dual_param_caller(self, function, sig, strict):
        """Create caller for functions with model and request parameters."""
        second_param = list(sig.parameters.values())[1]
        model_cls = second_param.annotation
        
        @functools.wraps(function)
        async def caller(obj_self, req):
            model = model_cls.model_validate_json(req.payload, strict=strict)
            result = await function(obj_self, model, req)
            return parse_resp(result)
        return caller

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
        return "{" + f"name={self.name}, func_list={self.func_list}" + "}"

    def export_pkg(self, pkg: dict) -> dict[str, Any]:
        fb_list = []
        for k, f in self.func_list.items():
            fb_list.append({"name": k, "function": "." + k})
        cls = {"name": self.name, "functions": fb_list}
        pkg["classes"].append(cls)

        for k, f in self.func_list.items():
            pkg["functions"].append({"name": k, "provision": {}})
        return pkg
