import functools
from collections.abc import Callable
import inspect
from typing import Optional, Any

from oprc_py.oprc_py import (
    InvocationRequest,
    InvocationResponse,
    InvocationResponseCode,
    ObjectInvocationRequest,
)
from pydantic import BaseModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaas_sdk2_py.engine import BaseObject


# def create_obj_meta(
#     cls: str,
#     partition_id: int,
#     obj_id: int = None,
# ):
#     oid = obj_id if obj_id is not None else tsidpy.TSID.create().number
#     return ObjectMeta(
#         obj_id=oid,
#         cls=cls,
#         partition_id=partition_id if partition_id is not None else -1,
#     )


# class ObjectMeta:
#     def __init__(
#         self, cls: str, partition_id: int, obj_id: Optional[int] = None, remote=False
#     ):
#         self.cls = cls
#         self.obj_id = obj_id
#         self.partition_id = partition_id
#         self.remote = remote

#     def __hash__(self):
#         return hash((self.cls, self.partition_id, self.obj_id))


class FuncMeta:
    def __init__(
        self,
        func,
        invoke_handler: Callable,
        signature: inspect.Signature,
        name,
        stateless=False,
        serve_with_agent=False,
        is_async=False,
    ):
        self.func = func
        self.invoke_handler = invoke_handler
        self.signature = signature
        self.stateless = stateless
        self.name = name
        self.serve_with_agent = serve_with_agent
        self.is_async = is_async
        self.__name__ = func.__name__
        self.__qualname__ = func.__qualname__
        self.__doc__ = func.__doc__

    def __get__(self, obj, objtype=None):
        """
        Descriptor protocol method that handles method binding when accessed through an instance.

        Args:
            obj: The instance the method is being accessed through (or None if accessed through the class)
            objtype: The class the method is being accessed through

        Returns:
            A bound method if accessed through an instance, or self if accessed through the class
        """
        if obj is None:
            # Class access - return the descriptor itself
            return self

        if inspect.iscoroutinefunction(self.func):
        # Instance access - return a bound method
            async def bound_method(*args, **kwargs):
                return await self.func(obj, *args, **kwargs)
        else:
            def bound_method(*args, **kwargs):
                return self.func(obj, *args, **kwargs)
            
        # Copy over metadata from the original function to make the bound method look authentic
        bound_method.__name__ = self.__name__
        bound_method.__qualname__ = self.__qualname__
        bound_method.__doc__ = self.__doc__

        return bound_method

    def __call__(self, obj_self, *args, **kwargs):
        """
        Make FuncMeta callable, allowing direct invocation when accessed through a class.

        Args:
            obj_self: The object instance (self from the original method)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the function call
        """
        return self.func(obj_self, *args, **kwargs)

    def __str__(self):
        return f"{{name={self.name}, stateless={self.stateless}, serve_with_agent={self.serve_with_agent}}}"

class StateMeta:
    setter: Callable
    getter: Callable

    def __init__(self, index: int, name: Optional[str] = None):
        self.index = index
        self.name = name


def parse_resp(resp) -> InvocationResponse:
    if resp is None:
        return InvocationResponse(status=int(InvocationResponseCode.Okay))
    elif isinstance(resp, InvocationResponse):
        return resp
    elif isinstance(resp, BaseModel):
        b = resp.model_dump_json().encode()
        return InvocationResponse(status=int(InvocationResponseCode.Okay), payload=b)
    elif isinstance(resp, bytes):
        return InvocationResponse(status=int(InvocationResponseCode.Okay), payload=resp)
    elif isinstance(resp, str):
        return InvocationResponse(
            status=int(InvocationResponseCode.Okay), payload=resp.encode()
        )


class ClsMeta:
    func_dict: dict[str, FuncMeta]
    state_dict: dict[int, StateMeta]

    def __init__(
        self, name: Optional[str], pkg: str = "default", update: Callable = None
    ):
        self.name = name
        self.pkg = pkg
        self.cls_id = f"{pkg}.{name}"
        self.update = update
        self.func_dict = {}
        self.state_dict = {}

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
        # Inject the ClsMeta instance into the decorated class
        setattr(cls, "__cls_meta__", self)
        if self.update is not None:
            self.update(self)
        return cls

    def func(self, name="", stateless=False, strict=False, serve_with_agent=False):
        """
        Decorator for registering class methods as invokable functions in OaaS platform.

        Args:
            name: Optional function name override. Defaults to the method's original name.
            stateless: Whether the function doesn't modify object state.
            strict: Whether to use strict validation when deserializing models.

        Returns:
            A FuncMeta instance that wraps the original method and is callable
        """

        def decorator(function):
            """
            Inner decorator that wraps the class method.

            Args:
                function: The method to wrap

            Returns:
                FuncMeta instance that wraps the original method
            """
            fn_name = name if len(name) != 0 else function.__name__
            sig = inspect.signature(function)
            
            if inspect.iscoroutinefunction(function):
                
                @functools.wraps(function)
                async def async_wrapper(obj_self: "BaseObject", *args, **kwargs):
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
                            req = self._extract_request(
                                obj_self, fn_name, args, kwargs, stateless
                            )
                            resp = await obj_self.session.fn_rpc_async(req)
                        else:
                            req = self._extract_request(
                                obj_self, fn_name, args, kwargs, stateless
                            )
                            resp = await obj_self.session.obj_rpc_async(req)
                        if issubclass(sig.return_annotation, BaseModel):
                            return sig.return_annotation.model_validate_json(
                                resp.payload, strict=strict
                            )
                        elif sig.return_annotation is bytes:
                            return resp.payload
                        elif sig.return_annotation is str:
                            return resp.payload.decode()
                        else:
                            return resp
                    else:
                        return await function(obj_self, *args, **kwargs)

                caller = self._create_caller(function, sig, strict)
                fn_meta = FuncMeta(
                    async_wrapper,
                    invoke_handler=caller,
                    signature=sig,
                    stateless=stateless,
                    name=fn_name,
                    serve_with_agent=serve_with_agent,
                    is_async=True,
                )
                self.func_dict[fn_name] = fn_meta
                return fn_meta  # Return FuncMeta instance instead of wrapper

            else:
                @functools.wraps(function)
                def sync_wrapper(obj_self: "BaseObject", *args, **kwargs):
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
                            req = self._extract_request(
                                obj_self, fn_name, args, kwargs, stateless
                            )
                            resp = obj_self.session.fn_rpc(req)
                        else:
                            req = self._extract_request(
                                obj_self, fn_name, args, kwargs, stateless
                            )
                            resp = obj_self.session.obj_rpc(req)
                        if issubclass(sig.return_annotation, BaseModel):
                            return sig.return_annotation.model_validate_json(
                                resp.payload, strict=strict
                            )
                        elif sig.return_annotation is bytes:
                            return resp.payload
                        elif sig.return_annotation is str:
                            return resp.payload.decode()
                        else:
                            return resp
                    else:
                        return function(obj_self, *args, **kwargs)

                caller = self._create_caller(function, sig, strict)
                fn_meta = FuncMeta(
                    sync_wrapper,
                    invoke_handler=caller,
                    signature=sig,
                    stateless=stateless,
                    name=fn_name,
                    serve_with_agent=serve_with_agent,
                )
                self.func_dict[fn_name] = fn_meta
                return fn_meta  # Return FuncMeta instance instead of wrapper
                
        return decorator

    def _extract_request(
        self, obj_self, fn_name, args, kwargs, stateless
    ) -> InvocationRequest | ObjectInvocationRequest | None:
        """Extract or create a request object from function arguments."""
        # Try to find an existing request object
        req = self._find_request_object(args, kwargs)
        if req is not None:
            return req

        # Try to find a BaseModel to create a request
        model = self._find_base_model(args, kwargs)
        return self._create_request_from_model(obj_self, fn_name, model, stateless)

    def _find_request_object(
        self, args, kwargs
    ) -> InvocationRequest | ObjectInvocationRequest | None:
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

    def _create_request_from_model(
        self, obj_self: "BaseObject", fn_name: str, model: BaseModel, stateless: bool
    ):
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
        if inspect.iscoroutinefunction(function):
            @functools.wraps(function)
            async def caller(obj_self, req):
                result = await function(obj_self)
                return parse_resp(result)
            return caller
        else:
            @functools.wraps(function)
            def caller(obj_self, req):
                result = function(obj_self)
                return parse_resp(result)
            return caller

    def _create_single_param_caller(self, function, sig, strict):
        """Create caller for functions with a single parameter."""
        second_param = list(sig.parameters.values())[1]

        if issubclass(second_param.annotation, BaseModel):
            model_cls = second_param.annotation
            if inspect.iscoroutinefunction(function):
                @functools.wraps(function)
                async def caller(obj_self, req):
                    model = model_cls.model_validate_json(req.payload, strict=strict)
                    result = await function(obj_self, model)
                    return parse_resp(result)
                return caller
            else:
                @functools.wraps(function)
                def caller(obj_self, req):
                    model = model_cls.model_validate_json(req.payload, strict=strict)
                    result = function(obj_self, model)
                    return parse_resp(result)

                return caller
        elif (
            second_param.annotation == InvocationRequest
            or second_param.annotation == ObjectInvocationRequest
        ):
            
            if inspect.iscoroutinefunction(function):
                @functools.wraps(function)
                async def caller(obj_self, req):
                    resp = await function(obj_self, req)
                    return parse_resp(resp)

                return caller
            else:
                @functools.wraps(function)
                async def caller(obj_self, req):
                    resp = await function(obj_self, req)
                    return parse_resp(resp)

                return caller
        elif issubclass(second_param.annotation, bytes):
            if inspect.iscoroutinefunction(function):
                @functools.wraps(function)
                async def caller(obj_self, req):
                    resp = await function(obj_self, req.payload)
                    return parse_resp(resp)
            else:
                @functools.wraps(function)
                def caller(obj_self, req):
                    resp = function(obj_self, req.payload)
                    return parse_resp(resp)
            return caller
        elif issubclass(second_param.annotation, str):
            if inspect.iscoroutinefunction(function):
                @functools.wraps(function)
                async def caller(obj_self, req):
                    resp = await function(obj_self, req.payload.decode())
                    return parse_resp(resp)
            else:
                @functools.wraps(function)
                def caller(obj_self, req):
                    resp = function(obj_self, req.payload.decode())
                    return parse_resp(resp)
            return caller
        else:
            raise ValueError(f"Unsupported parameter type: {second_param.annotation}")

    def _create_dual_param_caller(self, function, sig, strict):
        """Create caller for functions with model and request parameters."""
        second_param = list(sig.parameters.values())[1]
        model_cls = second_param.annotation

        if inspect.iscoroutinefunction(function):
            @functools.wraps(function)
            async def caller(obj_self, req):
                model = model_cls.model_validate_json(req.payload, strict=strict)
                result = await function(obj_self, model, req)
                return parse_resp(result)
        else:
            @functools.wraps(function)
            def caller(obj_self, req):
                model = model_cls.model_validate_json(req.payload, strict=strict)
                result = function(obj_self, model, req)
                return parse_resp(result)
        return caller


    def __str__(self):
        return "{" + f"name={self.name}, func_list={self.func_dict}" + "}"

    def export_pkg(self, pkg: dict) -> dict[str, Any]:
        fb_list = []
        for k, f in self.func_dict.items():
            fb_list.append({"name": k, "function": "." + k})
        cls = {"name": self.name, "functions": fb_list}
        pkg["classes"].append(cls)

        for k, f in self.func_dict.items():
            pkg["functions"].append({"name": k, "provision": {}})
        return pkg
