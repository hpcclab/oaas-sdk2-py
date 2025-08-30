"""
Accessor decorators and metadata for OaaS SDK simplified interface.

This module defines @oaas.getter and @oaas.setter, along with metadata
and utilities to finalize them against a service class. At runtime,
accessors perform persisted reads/writes via the object's storage APIs
and/or StateDescriptor, and are registered as standard OaaS methods.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, get_type_hints


class AccessorKind(str, Enum):
    GETTER = "getter"
    SETTER = "setter"


@dataclass
class AccessorSpec:
    name: str
    kind: AccessorKind
    field_name: str
    projection: Optional[List[str]]
    returns_value: bool
    param_type: Any | None
    return_type: Any | None
    defined_in: Type
    uses_descriptor: bool
    storage_index: Optional[int]


def getter(field: str | None = None, *, projection: List[str] | None = None):
    """Decorator to mark a method (sync or async) as a read-only accessor for a field."""

    def decorator(fn):
        setattr(fn, "_oaas_accessor", True)
        setattr(
            fn,
            "_oaas_accessor_config",
            {
                "kind": AccessorKind.GETTER,
                "field": field,
                "projection": projection,
            },
        )
        return fn

    return decorator


def setter(field: str | None = None):
    """Decorator to mark a method (sync or async) as a write accessor for a field."""

    def decorator(fn):
        setattr(fn, "_oaas_accessor", True)
        setattr(
            fn,
            "_oaas_accessor_config",
            {
                "kind": AccessorKind.SETTER,
                "field": field,
                "projection": None,
            },
        )
        return fn

    return decorator


def _infer_field_name(
    cls: Type, method_name: str, kind: AccessorKind, explicit_field: Optional[str]
) -> str:
    if explicit_field:
        return explicit_field

    # Pull annotations including bases
    annotations: Dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        annotations.update(getattr(base, "__annotations__", {}) or {})

    # Inference by name
    if kind is AccessorKind.GETTER:
        if method_name.startswith("get_"):
            candidate = method_name[4:]
            if candidate in annotations:
                return candidate
        if method_name in annotations:
            return method_name
    else:  # SETTER
        if method_name.startswith("set_"):
            candidate = method_name[4:]
            if candidate in annotations:
                return candidate
        if method_name in annotations:
            return method_name

    raise TypeError(
        f"Cannot infer field for accessor method '{method_name}' on {cls.__name__}"
    )


def _resolve_field_type(cls: Type, field_name: str) -> Any:
    # Prefer get_type_hints for forward refs
    try:
        type_hints = get_type_hints(cls)
    except Exception:
        # Fallback to raw annotations if hints fail
        type_hints = {}
        for base in reversed(cls.__mro__):
            type_hints.update(getattr(base, "__annotations__", {}) or {})
    if field_name not in type_hints:
        raise AttributeError(
            f"Field '{field_name}' not found in annotations of {cls.__name__}"
        )
    return type_hints[field_name]


def _validate_projection(projection: Optional[List[str]]):
    if projection is None:
        return
    if not isinstance(projection, list) or any(
        not isinstance(seg, str) or not seg for seg in projection
    ):
        raise ValueError("projection must be a list[str] with non-empty segments")


def _resolve_storage(cls: Type, field_name: str) -> Tuple[bool, Optional[int]]:
    """Return (uses_descriptor, storage_index)."""
    state_fields = getattr(cls, "_state_fields", None)
    if isinstance(state_fields, dict) and field_name in state_fields:
        descriptor = state_fields[field_name]
        index = getattr(descriptor, "index", None)
        return True, index
    # No descriptor mapping available for legacy classes
    return False, None


def _ensure_async_signature(kind: AccessorKind, fn):
    if not inspect.iscoroutinefunction(fn):
        raise TypeError(f"@oaas.{kind.value} must decorate an async method: {fn.__name__}")


def _validate_getter_signature(fn, return_type):
    sig = inspect.signature(fn)
    # Expect only self
    if len(sig.parameters) != 1:
        raise TypeError("getter must not take parameters other than self")
    if sig.return_annotation in (inspect._empty, None):
        raise TypeError("getter must declare a return annotation")
    # Best-effort: allow any, but could add stricter checks later
    return sig


def _validate_setter_signature(fn, field_type):
    sig = inspect.signature(fn)
    if len(sig.parameters) != 2:
        raise TypeError("setter must take exactly one parameter besides self")
    # Second param type should be annotated
    second = list(sig.parameters.values())[1]
    if second.annotation in (inspect._empty, None):
        raise TypeError("setter value parameter must be annotated")
    # Return can be None or field type (best-effort)
    return sig


def _apply_projection(value: Any, projection: Optional[List[str]]):
    if projection is None:
        return value
    current = value
    for seg in projection:
        if current is None:
            return None
        if hasattr(current, seg):
            current = getattr(current, seg)
        elif isinstance(current, dict) and seg in current:
            current = current[seg]
        else:
            raise ValueError(f"Invalid projection segment '{seg}'")
    return current


def build_accessor_wrapper(
    cls: Type, method_name: str, fn, config: Dict[str, Any]
) -> Tuple[Callable, AccessorSpec]:
    """
    Build an async wrapper that performs persisted read/write for the accessor
    and produce an AccessorSpec. The wrapper ignores the original body.
    """
    kind: AccessorKind = config["kind"]
    projection: Optional[List[str]] = config.get("projection")

    _validate_projection(projection)

    field_name = _infer_field_name(cls, method_name, kind, config.get("field"))
    field_type = _resolve_field_type(cls, field_name)
    uses_descriptor, storage_index = _resolve_storage(cls, field_name)

    is_async = inspect.iscoroutinefunction(fn)

    if kind is AccessorKind.GETTER:
        sig = _validate_getter_signature(fn, field_type)
        return_type = sig.return_annotation
        param_type = None
        returns_value = True

        if is_async:
            async def wrapper(obj_self):
                if uses_descriptor:
                    value = getattr(obj_self, field_name)
                else:
                    if storage_index is None:
                        raise TypeError(
                            f"No storage mapping for field '{field_name}' on {cls.__name__}"
                        )
                    if hasattr(obj_self, "get_data_async") and inspect.iscoroutinefunction(
                        getattr(obj_self, "get_data_async")
                    ):
                        raw = await obj_self.get_data_async(storage_index)
                    else:
                        raw = obj_self.get_data(storage_index)
                    if raw is None:
                        value = None
                    else:
                        from .serialization import UnifiedSerializer
                        serializer = UnifiedSerializer()
                        value = serializer.deserialize(raw, field_type)
                return _apply_projection(value, projection)
        else:
            def wrapper(obj_self):
                if uses_descriptor:
                    value = getattr(obj_self, field_name)
                else:
                    if storage_index is None:
                        raise TypeError(
                            f"No storage mapping for field '{field_name}' on {cls.__name__}"
                        )
                    raw = obj_self.get_data(storage_index)
                    if raw is None:
                        value = None
                    else:
                        from .serialization import UnifiedSerializer
                        serializer = UnifiedSerializer()
                        value = serializer.deserialize(raw, field_type)
                return _apply_projection(value, projection)

        # Set up wrapper metadata for potential future RPC use
        wrapper.__name__ = method_name
        wrapper._owner = None  # Will be set when bound to instance
        wrapper._meta = None   # Not registered as function
        spec = AccessorSpec(
            name=method_name,
            kind=kind,
            field_name=field_name,
            projection=projection,
            returns_value=returns_value,
            param_type=param_type,
            return_type=return_type,
            defined_in=cls,
            uses_descriptor=uses_descriptor,
            storage_index=storage_index,
        )
        return wrapper, spec

    else:  # SETTER
        sig = _validate_setter_signature(fn, field_type)
        second = list(sig.parameters.values())[1]
        param_type = second.annotation
        return_type = sig.return_annotation if sig.return_annotation is not inspect._empty else None
        returns_value = return_type is not None and return_type is not type(None)  # noqa: E721

        if is_async:
            async def wrapper(obj_self, value):
                if uses_descriptor:
                    setattr(obj_self, field_name, value)
                    if returns_value:
                        return getattr(obj_self, field_name)
                    return None
                else:
                    if storage_index is None:
                        raise TypeError(
                            f"No storage mapping for field '{field_name}' on {cls.__name__}"
                        )
                    from .serialization import UnifiedSerializer
                    serializer = UnifiedSerializer()
                    converted = serializer.convert_value(value, field_type)
                    raw = serializer.serialize(converted, field_type)
                    if hasattr(obj_self, "set_data_async") and inspect.iscoroutinefunction(
                        getattr(obj_self, "set_data_async")
                    ):
                        await obj_self.set_data_async(storage_index, raw)
                    else:
                        obj_self.set_data(storage_index, raw)
                    return converted if returns_value else None
        else:
            def wrapper(obj_self, value):
                if uses_descriptor:
                    setattr(obj_self, field_name, value)
                    if returns_value:
                        return getattr(obj_self, field_name)
                    return None
                else:
                    if storage_index is None:
                        raise TypeError(
                            f"No storage mapping for field '{field_name}' on {cls.__name__}"
                        )
                    from .serialization import UnifiedSerializer
                    serializer = UnifiedSerializer()
                    converted = serializer.convert_value(value, field_type)
                    raw = serializer.serialize(converted, field_type)
                    obj_self.set_data(storage_index, raw)
                    return converted if returns_value else None

        # Set up wrapper metadata for potential future RPC use
        wrapper.__name__ = method_name
        wrapper._owner = None  # Will be set when bound to instance
        wrapper._meta = None   # Not registered as function
        spec = AccessorSpec(
            name=method_name,
            kind=kind,
            field_name=field_name,
            projection=None,
            returns_value=returns_value,
            param_type=param_type,
            return_type=return_type,
            defined_in=cls,
            uses_descriptor=uses_descriptor,
            storage_index=storage_index,
        )
        return wrapper, spec


def collect_accessor_members(cls: Type) -> Dict[str, Dict[str, Any]]:
    """Collect methods on class that were marked as accessors: name -> config dict."""
    out: Dict[str, Dict[str, Any]] = {}
    for attr_name in dir(cls):
        if attr_name.startswith("_"):
            continue
        attr = getattr(cls, attr_name)
        if callable(attr) and hasattr(attr, "_oaas_accessor"):
            cfg = getattr(attr, "_oaas_accessor_config", None)
            if not cfg:
                continue
            out[attr_name] = cfg
    return out
