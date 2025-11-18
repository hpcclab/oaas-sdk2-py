"""Helpers for working with string-based object identifiers.

This module centralizes all ID generation/normalization logic so the rest of
the SDK can treat object identifiers as canonical strings, while still
supporting the historical numeric flows for backward compatibility.
"""
from __future__ import annotations

from typing import Any, Optional

from tsidpy import TSID  # type: ignore


TSID_FMT = "S"


def _tsid_to_string(tsid_obj: Any) -> str:
    if tsid_obj is None:
        raise ValueError("TSID object is None")
    if hasattr(tsid_obj, "to_string"):
        return tsid_obj.to_string(TSID_FMT)  # type: ignore[no-any-return]
    if hasattr(tsid_obj, "number"):
        return format(getattr(tsid_obj, "number"), "x").upper()
    return str(tsid_obj)


def generate_object_id() -> str:
    """Return a new canonical object identifier string.

    Uses TSID for time-sortable IDs.
    """
    return TSID.create().to_string(TSID_FMT)  # type: ignore[no-any-return]


def normalize_object_id(obj_id: Any) -> str:
    """Normalize user-provided IDs into canonical uppercase strings."""
    if obj_id is None:
        return generate_object_id()
    if isinstance(obj_id, bytes):
        return obj_id.decode("utf-8")
    if isinstance(obj_id, str):
        return obj_id.strip()
    if isinstance(obj_id, TSID):  # type: ignore[arg-type]
        return _tsid_to_string(obj_id)
    return str(obj_id)


def meta_object_id(meta: Any) -> str:
    """Extract the best-effort string identifier from ObjectMetadata-like objects."""
    if meta is None:
        raise ValueError("metadata is required")
    object_id_str = getattr(meta, "object_id_str", None)
    if object_id_str:
        return str(object_id_str)
    object_id = getattr(meta, "object_id", None)
    if object_id is None:
        raise ValueError("metadata missing object_id information")
    return str(object_id)


def request_object_id(req: Any) -> str:
    """Extract the string ID from an ObjectInvocationRequest-like payload."""
    if req is None:
        raise ValueError("request is required")
    object_id_str = getattr(req, "object_id_str", None)
    if object_id_str:
        return str(object_id_str)
    object_id = getattr(req, "object_id", None)
    if object_id is None:
        raise ValueError("request missing object_id")
    return str(object_id)


def identity_key(cls_id: str, partition_id: int, object_id: str) -> str:
    """Build a stable dictionary key for caching objects."""
    return f"{cls_id}:{partition_id}:{object_id}"


def ensure_object_metadata_kwargs(
    cls_id: str,
    partition_id: int,
    object_id: Optional[str] = None,
) -> dict:
    """Prepare kwargs for ObjectMetadata construction with canonical IDs."""
    object_id_str = normalize_object_id(object_id)
    return {
        "cls_id": cls_id,
        "partition_id": partition_id,
        "object_id": None,
        "object_id_str": object_id_str,
    }
