"""
Object reference proxies for OaaS services.

Implements identity-based references that forward method calls over RPC.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Optional

import oprc_py
from oprc_py import ObjectMetadata
from .accessors import AccessorKind, _apply_projection


class ObjectRef:
    """
    Lightweight proxy to an OaaS object identified by ObjectMetadata.

    - Holds metadata and forwards method calls over RPC using AutoSessionManager.
    - Methods surfaced are awaitable; payloads are serialized based on the
      target function signature when available.
    """

    def __init__(self, metadata: ObjectMetadata):
        self._metadata = metadata

    # Public surface ---------------------------------------------------------
    @property
    def metadata(self) -> ObjectMetadata:
        return self._metadata

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ObjectRef):
            return False
        a, b = self._metadata, other._metadata
        return a.cls_id == b.cls_id and a.partition_id == b.partition_id and a.object_id == b.object_id

    def __hash__(self) -> int:
        m = self._metadata
        return hash((m.cls_id, m.partition_id, m.object_id))

    def __str__(self) -> str:
        m = self._metadata
        return f"ObjectRef({m.cls_id}#{m.object_id}@{m.partition_id})"

    def __repr__(self) -> str:
        return str(self)

    def __getattr__(self, name: str) -> Callable[..., Any]:
        """
        Return an async function that performs RPC to the target method.

        Supports 0 or 1 user parameter methods. Parameter serialization and
        return parsing use the same UnifiedSerializer/type hints used elsewhere.
        """
        # Late imports to avoid cycles
        from .service import OaasService
        from ..model import ClsMeta
        from .serialization import UnifiedSerializer

        meta_repo = OaasService._get_global_oaas().meta_repo
        cls_meta: Optional[ClsMeta] = meta_repo.get_cls_meta(self._metadata.cls_id)
        if cls_meta is None:
            # Fallback: allow method name but raise on call
            async def _missing(*args, **kwargs):  # pragma: no cover - defensive
                raise AttributeError(f"Class id '{self._metadata.cls_id}' not registered; cannot call '{name}'")
            return _missing

        fn_meta = cls_meta.func_dict.get(name)
        if fn_meta is None:
            # Try accessor wrappers (not exported as functions)
            accessor_spec = getattr(cls_meta, 'accessor_dict', {}).get(name)
            if accessor_spec is not None and accessor_spec.kind == AccessorKind.GETTER:
                async def _accessor_getter():
                    from .service import OaasService
                    from .serialization import UnifiedSerializer
                    auto = OaasService._get_auto_session_manager()
                    session = auto.get_session(self._metadata.partition_id)
                    obj: oprc_py.ObjectData | None = await session.data_manager.get_obj_async(
                        self._metadata.cls_id, self._metadata.partition_id, self._metadata.object_id
                    )
                    if obj is None:
                        return None
                    idx = accessor_spec.storage_index
                    if idx is None:
                        return None
                    raw = obj.entries.get(idx)
                    if raw is None:
                        return None
                    payload = bytes(raw) if not isinstance(raw, (bytes, bytearray, memoryview)) else bytes(raw)
                    serializer = UnifiedSerializer()
                    value = serializer.deserialize(payload, accessor_spec.return_type)
                    return _apply_projection(value, accessor_spec.projection)

                return _accessor_getter

            if accessor_spec is not None and accessor_spec.kind == AccessorKind.SETTER:
                async def _accessor_setter(value):
                    from .service import OaasService
                    from .serialization import UnifiedSerializer
                    auto = OaasService._get_auto_session_manager()
                    session = auto.get_session(self._metadata.partition_id)
                    idx = accessor_spec.storage_index
                    if idx is None:
                        raise AttributeError(f"Setter '{name}' missing storage index on service '{self._metadata.cls_id}'")
                    # Fetch existing entries, update idx
                    existing: oprc_py.ObjectData | None = await session.data_manager.get_obj_async(
                        self._metadata.cls_id, self._metadata.partition_id, self._metadata.object_id
                    )
                    entries = dict(existing.entries) if existing is not None else {}
                    serializer = UnifiedSerializer()
                    # Use param type when available, else fallback to return_type or leave as-is
                    param_type = getattr(accessor_spec, 'param_type', None)
                    converted = serializer.convert_value(value, param_type) if param_type is not None else value
                    raw = serializer.serialize(converted, param_type)
                    entries[idx] = raw
                    obj_data = oprc_py.ObjectData(meta=self._metadata, entries=entries, event=None)
                    await session.data_manager.set_obj_async(obj_data)
                    # If accessor returns a value, honor it; otherwise None
                    return converted if accessor_spec.returns_value else None

                return _accessor_setter

            async def _missing(*args, **kwargs):  # pragma: no cover - defensive
                raise AttributeError(f"Method '{name}' not found on service '{self._metadata.cls_id}'")
            return _missing

        sig = fn_meta.signature
        is_stateless = getattr(fn_meta, "stateless", False)
        serializer = UnifiedSerializer()

        async def _caller(*args, **kwargs):
            from .service import OaasService

            # Acquire session for the target partition
            auto = OaasService._get_auto_session_manager()
            session = auto.get_session(self._metadata.partition_id)

            # Build request payload from args
            param_count = len(sig.parameters)
            payload: bytes | None = None

            if param_count == 1:
                # only self on server side => no payload
                payload = b""
            elif param_count >= 2:
                # Take the first user argument positionally
                if args:
                    arg_val = args[0]
                else:
                    # If only kwargs provided, pick the first parameter after self
                    second = list(sig.parameters.values())[1]
                    if second.name in kwargs:
                        arg_val = kwargs[second.name]
                    else:
                        raise TypeError(f"Missing argument '{second.name}' for '{name}'")

                second = list(sig.parameters.values())[1]
                param_type = second.annotation if second.annotation is not inspect._empty else None

                if param_type is not None:
                    payload = serializer.serialize(arg_val, param_type)
                else:
                    # Best-effort generic serialization
                    payload = serializer.serialize(arg_val, None)
            else:
                # Shouldn't happen; default to empty
                payload = b""

            # Invoke RPC (stateless uses function RPC; otherwise object RPC)
            if is_stateless:
                req = oprc_py.InvocationRequest(
                    cls_id=self._metadata.cls_id,
                    fn_id=name,
                    payload=payload,
                )
                resp = await session.fn_rpc_async(req)
            else:
                req = oprc_py.ObjectInvocationRequest(
                    cls_id=self._metadata.cls_id,
                    partition_id=self._metadata.partition_id,
                    object_id=self._metadata.object_id,
                    fn_id=name,
                    payload=payload or b"",
                )
                resp = await session.obj_rpc_async(req)

            # Map response to annotated return type if available
            return_type = sig.return_annotation
            if return_type is inspect._empty or return_type is None:
                # Return raw response for unknown type
                return resp

            # Pydantic model
            try:
                from pydantic import BaseModel  # type: ignore
                if inspect.isclass(return_type) and issubclass(return_type, BaseModel):
                    return return_type.model_validate_json(resp.payload)
            except Exception:
                pass

            if return_type is bytes:
                return resp.payload
            if return_type is str:
                return resp.payload.decode()

            # Default unified deserialization path
            return serializer.deserialize(resp.payload, return_type)

        return _caller


def ref(cls_id: str, object_id: int, partition_id: int = 0) -> ObjectRef:
    """Create an ObjectRef from identity components."""
    meta = ObjectMetadata(cls_id=cls_id, partition_id=partition_id, object_id=object_id)
    return ObjectRef(meta)
