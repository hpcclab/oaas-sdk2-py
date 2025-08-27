# Legacy API - maintained for backward compatibility
from .engine import Oparaca  # noqa: F401
from .session import Session # noqa: F401
from .obj import BaseObject # noqa: F401
from .model import ClsMeta, FuncMeta  # noqa: F401
from oprc_py import ObjectInvocationRequest, InvocationRequest, InvocationResponse  # noqa: F401

# New Simplified API - Phase 1 Week 1 Foundation
from .simplified import (
    OaasObject,        # Simplified base class with auto-serialization
    OaasService,       # Global registry and decorator system
    OaasConfig,        # Unified configuration object
    StateDescriptor,   # Automatic state management
    AutoSessionManager, # Automatic session lifecycle management
    LegacySessionAdapter, # Backward compatibility for Session API
    getter, setter,    # Accessor decorators
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
    "BaseObject",
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