# Legacy API - maintained for backward compatibility
from .engine import Oparaca  # noqa: F401
from .session import Session # noqa: F401
from .model import ClsMeta, FuncMeta  # noqa: F401
from oprc_py import ObjectInvocationRequest, InvocationRequest, InvocationResponse  # noqa: F401
import os as _os

try:
    from . import telemetry as _telemetry_mod  # noqa: F401
except Exception:  # pragma: no cover
    _telemetry_mod = None

# New Simplified API - Phase 1 Week 1 Foundation
from .simplified import (
    OaasObject,        # Simplified base class with auto-serialization
    OaasService,       # Global registry and decorator system
    OaasConfig,        # Unified configuration object
    StateDescriptor,   # Automatic state management
    AutoSessionManager, # Automatic session lifecycle management
    LegacySessionAdapter, # Backward compatibility for Session API
    getter, setter,    # Accessor decorators
    ref, ObjectRef,    # Identity-based references
    oaas,             # Global service instance
    create_object,     # Convenience function
    load_object,       # Convenience function
    new_session,       # Backward compatible session creation
    get_global_oaas,   # Get global Oparaca instance
    configure_oaas,    # Configure global OaaS
    enable_auto_commit, # Enable auto-commit
    disable_auto_commit, # Disable auto-commit
    set_auto_commit_interval, # Set auto-commit interval
)

# Make the global oaas instance available at package level
# This allows usage like: from oaas_sdk2_py import oaas
# Then: @oaas.service("MyService")
__all__ = [
    # Legacy API
    "Oparaca",
    "Session",
    "ClsMeta",
    "FuncMeta",
    "ObjectInvocationRequest",
    "InvocationRequest",
    "InvocationResponse",
    
    # New Simplified API
    "OaasObject",
    "OaasService",
    "OaasConfig",
    "StateDescriptor",
    "AutoSessionManager",
    "LegacySessionAdapter",
    "getter",
    "setter",
    "ref",
    "ObjectRef",
    "oaas",
    "create_object",
    "load_object",
    "new_session",
    "get_global_oaas",
    "configure_oaas",
    "enable_auto_commit",
    "disable_auto_commit",
    "set_auto_commit_interval"
]

# Auto-enable telemetry if environment hints are present and module available.
if _telemetry_mod is not None:
    if any(k in _os.environ for k in (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_SERVICE_NAME",
        "OTEL_TRACES_SAMPLER"
    )):
        try:
            _telemetry_mod.enable(service_name=_os.environ.get("OTEL_SERVICE_NAME"))
        except Exception:
            pass

# Helpful error for removed legacy symbol
def __getattr__(name: str):  # pragma: no cover - simple runtime guard
    if name == "BaseObject":
        raise AttributeError(
            "BaseObject has been removed from oaas_sdk2_py. "
            "Use OaasObject from oaas_sdk2_py.simplified.objects instead."
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")