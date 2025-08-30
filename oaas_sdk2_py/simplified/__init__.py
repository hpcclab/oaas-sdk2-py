"""
Simplified OaaS SDK Interface

This module provides a simplified, opinionated interface for the OaaS SDK
with automatic state management, enhanced decorators, and session handling.

The module is organized into logical components:
- errors: Error handling and debugging infrastructure
- performance: Performance monitoring and metrics
- config: Configuration management with pydantic integration
- session_manager: Automatic session lifecycle management
- state_descriptor: Automatic state serialization for typed fields
- objects: Simplified base class with automatic state management
- decorators: Enhanced decorators for methods, functions, and constructors
- service: Main service registry and decorator system

Usage:
    from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig
    
    @oaas.service("MyService")
    class MyService(OaasObject):
        value: int = 0
        
        @oaas.method
        def increment(self) -> int:
            self.value += 1
            return self.value
    
    # Usage
    obj = MyService.create()
    result = obj.increment()
"""

# Import all components for a unified interface
from .errors import (
    OaasError, SerializationError, ValidationError, SessionError,
    DecoratorError, PerformanceError, ConfigurationError,
    ServerError, AgentError,
    DebugLevel, DebugContext, get_debug_context, set_debug_level, configure_debug
)

from .performance import (
    PerformanceMetrics, debug_wrapper,
    get_performance_metrics, reset_performance_metrics
)

from .config import OaasConfig

from .session_manager import (
    AutoSessionManager, LegacySessionAdapter
)

from .state_descriptor import StateDescriptor

from .objects import OaasObject
from .references import ref, ObjectRef

from .decorators import (
    EnhancedFunctionDecorator, ConstructorDecorator, EnhancedMethodDecorator
)
from .accessors import getter, setter

from .service import (
    OaasService, oaas,
    new_session, get_global_oaas, configure_oaas,
    enable_auto_commit, disable_auto_commit, set_auto_commit_interval,
    create_object, load_object
)

# Backward compatibility exports
__all__ = [
    # Main service interface
    'oaas',
    'OaasService',
    
    # Core classes
    'OaasObject',
    'OaasConfig',
    
    # Error handling
    'OaasError', 'SerializationError', 'ValidationError', 'SessionError',
    'DecoratorError', 'PerformanceError', 'ConfigurationError',
    'ServerError', 'AgentError',
    'DebugLevel', 'DebugContext', 'get_debug_context', 'set_debug_level', 'configure_debug',

    # Performance monitoring
    'PerformanceMetrics', 'debug_wrapper',
    'get_performance_metrics', 'reset_performance_metrics',
    
    # Session management
    'AutoSessionManager', 'LegacySessionAdapter',
    'new_session', 'get_global_oaas', 'configure_oaas',
    'enable_auto_commit', 'disable_auto_commit', 'set_auto_commit_interval',
    
    # State management
    'StateDescriptor',
    
    # Decorators
    'EnhancedFunctionDecorator', 'ConstructorDecorator', 'EnhancedMethodDecorator',
    
    # Convenience functions
    'create_object', 'load_object',
    # References
    'ref', 'ObjectRef'
]
