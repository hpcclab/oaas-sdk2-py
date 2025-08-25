"""
OaaS SDK State Descriptors

This module provides automatic state management and serialization
for the OaaS SDK simplified interface.
"""

import time
from typing import Any, Optional, Type, TYPE_CHECKING

from .errors import SerializationError, ValidationError, get_debug_context, DebugLevel
from .performance import PerformanceMetrics
from .serialization import UnifiedSerializer

if TYPE_CHECKING:
    from .objects import OaasObject


class StateDescriptor:
    """
    Enhanced descriptor that handles automatic serialization/deserialization of typed state fields.
    
    This descriptor provides transparent access to persistent state with automatic
    type conversion, comprehensive error handling, and debugging support.
    """
    
    def __init__(self, name: str, type_hint: Type, default_value: Any, index: int):
        self.name = name
        self.type_hint = type_hint
        self.default_value = default_value
        self.index = index
        self.private_name = f"_state_{name}"
        self.metrics = PerformanceMetrics()
        self.serializer = UnifiedSerializer()
        
    def __get__(self, obj: Optional['OaasObject'], objtype: Optional[Type] = None) -> Any:
        if obj is None:
            return self
            
        debug_ctx = get_debug_context()
        start_time = time.time() if debug_ctx.performance_monitoring else None
        
        try:
            # Check if value is in memory cache
            if hasattr(obj, self.private_name):
                cached_value = getattr(obj, self.private_name)
                debug_ctx.log(DebugLevel.TRACE, f"StateDescriptor cache hit for {self.name}")
                return cached_value
                
            # Load from persistent storage
            raw_data = obj.get_data(self.index)
            if raw_data is None:
                value = self.default_value
                debug_ctx.log(DebugLevel.TRACE, f"StateDescriptor using default value for {self.name}")
            else:
                value = self.serializer.deserialize(raw_data, self.type_hint)
                debug_ctx.log(DebugLevel.TRACE, f"StateDescriptor deserialized {self.name}")
                
            # Cache in memory
            setattr(obj, self.private_name, value)
            
            # Record performance metrics
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                self.metrics.record_call(duration, success=True)
            
            return value
            
        except Exception as e:
            debug_ctx.log(DebugLevel.ERROR, f"StateDescriptor __get__ error for {self.name}: {e}")
            
            # Record performance metrics
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                self.metrics.record_call(duration, success=False)
            
            # Return default value on error
            return self.default_value
        
    def __set__(self, obj: 'OaasObject', value: Any) -> None:
        debug_ctx = get_debug_context()
        start_time = time.time() if debug_ctx.performance_monitoring else None
        
        try:
            # Type validation and conversion using unified serializer
            converted_value = self.serializer.convert_value(value, self.type_hint)
            
            # Update memory cache
            setattr(obj, self.private_name, converted_value)
            
            # Persist to storage with error handling
            serialized_data = self.serializer.serialize(converted_value, self.type_hint)
            obj.set_data(self.index, serialized_data)
            
            debug_ctx.log(DebugLevel.TRACE, f"StateDescriptor set {self.name} = {type(value).__name__}")
            
            # Schedule auto-commit if enabled and available
            if (hasattr(obj, '_auto_commit') and obj._auto_commit and 
                hasattr(obj, '_auto_session_manager') and obj._auto_session_manager is not None):
                try:
                    obj._auto_session_manager.schedule_commit(obj)
                except Exception as e:
                    debug_ctx.log(DebugLevel.WARNING, f"Failed to schedule auto-commit for {self.name}: {e}")
            
            # Record performance metrics
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                self.metrics.record_call(duration, success=True)
                
        except Exception as e:
            debug_ctx.log(DebugLevel.ERROR, f"StateDescriptor __set__ error for {self.name}: {e}")
            
            # Record performance metrics
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                self.metrics.record_call(duration, success=False)
            
            # Re-raise as SerializationError with context
            raise SerializationError(
                f"Failed to set state field '{self.name}' of type {self.type_hint.__name__}",
                error_code="STATE_SET_ERROR",
                details={
                    'field_name': self.name,
                    'field_type': self.type_hint.__name__,
                    'value_type': type(value).__name__,
                    'value': str(value)[:100],  # Truncate for safety
                    'index': self.index
                }
            ) from e
        
    # --- Helper methods for testing and explicit control ---
    def _serialize(self, value: Any) -> bytes:
        """Serialize a value according to this descriptor's type hint."""
        return self.serializer.serialize(value, self.type_hint)

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize bytes into a typed value according to this descriptor's type hint."""
        return self.serializer.deserialize(data, self.type_hint)

    def _convert_value(self, value: Any) -> Any:
        """Convert a value into the descriptor's type with validation."""
        return self.serializer.convert_value(value, self.type_hint)
    
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics for this state descriptor."""
        return self.metrics
    
    def reset_performance_metrics(self):
        """Reset performance metrics for this state descriptor."""
        self.metrics = PerformanceMetrics()
