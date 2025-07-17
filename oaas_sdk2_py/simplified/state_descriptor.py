"""
OaaS SDK State Descriptors

This module provides automatic state management and serialization
for the OaaS SDK simplified interface.
"""

import json
import pickle
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, get_origin, get_args, Union, TYPE_CHECKING
from uuid import UUID

from .errors import SerializationError, ValidationError, get_debug_context, DebugLevel
from .performance import PerformanceMetrics

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
                value = self._deserialize(raw_data)
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
            # Type validation and conversion with comprehensive error handling
            converted_value = self._convert_value(value)
            
            # Update memory cache
            setattr(obj, self.private_name, converted_value)
            
            # Persist to storage with error handling
            serialized_data = self._serialize(converted_value)
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
        
    def _convert_value(self, value: Any) -> Any:
        """Convert value to the expected type with comprehensive error handling."""
        debug_ctx = get_debug_context()
        
        try:
            # Handle None values first
            if value is None:
                if self.default_value is not None:
                    return self.default_value
                return None
            
            # Handle basic type conversions
            if self.type_hint in (int, float, str, bool):
                try:
                    # Check if it's already the right type
                    if isinstance(value, self.type_hint):
                        return value
                    return self.type_hint(value)
                except (ValueError, TypeError) as e:
                    debug_ctx.log(DebugLevel.WARNING, f"Basic type conversion failed for {self.name}: {e}")
                    raise ValidationError(
                        f"Cannot convert {type(value).__name__} to {self.type_hint.__name__}",
                        error_code="TYPE_CONVERSION_ERROR",
                        details={'field_name': self.name, 'value': str(value), 'target_type': self.type_hint.__name__}
                    ) from e
            
            # Handle generic types (List, Dict, Union, etc.)
            origin = get_origin(self.type_hint)
            if origin is not None:
                # Handle list types
                if origin is list:
                    if isinstance(value, list):
                        return self._convert_list_elements(value)
                    elif isinstance(value, (tuple, set)):
                        return self._convert_list_elements(list(value))
                    else:
                        return [value]
                
                # Handle dict types
                elif origin is dict:
                    if isinstance(value, dict):
                        return self._convert_dict_elements(value)
                    else:
                        debug_ctx.log(DebugLevel.WARNING, f"Cannot convert {type(value).__name__} to dict for {self.name}")
                        return {}
                
                # Handle Union types (including Optional)
                elif origin is Union:
                    return self._convert_union_value(value)
                
                # Handle other generic types
                else:
                    # For other generic types, try to check the origin type
                    try:
                        if isinstance(value, origin):
                            return value
                        return origin(value)
                    except Exception:
                        return value
            
            # Handle non-generic types safely
            try:
                # Check if it's already the right type
                if isinstance(value, self.type_hint):
                    return value
            except TypeError:
                # isinstance failed, skip this check
                pass
            
            # Handle Pydantic models
            if hasattr(self.type_hint, 'model_validate'):
                try:
                    if isinstance(value, dict):
                        return self.type_hint.model_validate(value)
                    elif hasattr(value, 'model_dump'):  # Already a Pydantic model
                        return value
                    else:
                        return self.type_hint(value)
                except Exception as e:
                    debug_ctx.log(DebugLevel.WARNING, f"Pydantic model validation failed for {self.name}: {e}")
                    raise ValidationError(
                        f"Invalid data for Pydantic model {self.type_hint.__name__}",
                        error_code="PYDANTIC_VALIDATION_ERROR",
                        details={'field_name': self.name, 'model_type': self.type_hint.__name__}
                    ) from e
            
            # Handle datetime
            if self.type_hint == datetime:
                if isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value)
                    except ValueError as e:
                        raise ValidationError(
                            f"Invalid datetime format for field '{self.name}'",
                            error_code="DATETIME_FORMAT_ERROR",
                            details={'field_name': self.name, 'value': value}
                        ) from e
                elif isinstance(value, datetime):
                    return value
            
            # Handle UUID
            if self.type_hint == UUID:
                if isinstance(value, str):
                    try:
                        return UUID(value)
                    except ValueError as e:
                        raise ValidationError(
                            f"Invalid UUID format for field '{self.name}'",
                            error_code="UUID_FORMAT_ERROR",
                            details={'field_name': self.name, 'value': value}
                        ) from e
                elif isinstance(value, UUID):
                    return value
            
            # For other types, try direct conversion or return as-is
            try:
                return self.type_hint(value)
            except Exception as e:
                debug_ctx.log(DebugLevel.WARNING, f"Direct type conversion failed for {self.name}: {e}")
                # Return the value as-is if conversion fails
                return value
                
        except Exception as e:
            if isinstance(e, (ValidationError, SerializationError)):
                raise
            
            debug_ctx.log(DebugLevel.ERROR, f"Unexpected error in _convert_value for {self.name}: {e}")
            raise ValidationError(
                f"Unexpected error converting value for field '{self.name}'",
                error_code="CONVERSION_ERROR",
                details={'field_name': self.name, 'error': str(e)}
            ) from e
    
    def _convert_list_elements(self, value_list: List[Any]) -> List[Any]:
        """Convert list elements to the correct type if type arguments are available."""
        type_args = get_args(self.type_hint)
        if not type_args:
            return value_list
            
        element_type = type_args[0]
        converted_list = []
        
        for i, item in enumerate(value_list):
            try:
                if element_type == Any:
                    converted_list.append(item)
                elif isinstance(item, element_type):
                    converted_list.append(item)
                else:
                    # Try to convert the item
                    converted_list.append(element_type(item))
            except Exception as e:
                debug_ctx = get_debug_context()
                debug_ctx.log(DebugLevel.WARNING, f"List element conversion failed at index {i}: {e}")
                # Keep original item if conversion fails
                converted_list.append(item)
        
        return converted_list
    
    def _convert_dict_elements(self, value_dict: Dict[Any, Any]) -> Dict[Any, Any]:
        """Convert dict elements to the correct type if type arguments are available."""
        type_args = get_args(self.type_hint)
        if not type_args or len(type_args) < 2:
            return value_dict
            
        key_type, value_type = type_args[0], type_args[1]
        converted_dict = {}
        
        for k, v in value_dict.items():
            try:
                # Convert key
                if key_type == Any:
                    converted_key = k
                elif isinstance(k, key_type):
                    converted_key = k
                else:
                    converted_key = key_type(k)
                
                # Convert value
                if value_type == Any:
                    converted_value = v
                elif isinstance(v, value_type):
                    converted_value = v
                else:
                    converted_value = value_type(v)
                
                converted_dict[converted_key] = converted_value
                
            except Exception as e:
                debug_ctx = get_debug_context()
                debug_ctx.log(DebugLevel.WARNING, f"Dict element conversion failed for key {k}: {e}")
                # Keep original key-value pair if conversion fails
                converted_dict[k] = v
        
        return converted_dict
    
    def _convert_union_value(self, value: Any) -> Any:
        """Convert value for Union types (including Optional)."""
        type_args = get_args(self.type_hint)
        if not type_args:
            return value
        
        # Handle Optional (Union[T, None])
        if len(type_args) == 2 and type(None) in type_args:
            if value is None:
                return None
            non_none_type = next(t for t in type_args if t is not type(None))
            try:
                return non_none_type(value)
            except Exception:
                return value
        
        # Try each type in the union
        for union_type in type_args:
            try:
                if isinstance(value, union_type):
                    return value
                return union_type(value)
            except Exception:
                continue
        
        # If no conversion worked, return as-is
        return value
        
    def _serialize(self, value: Any) -> bytes:
        """Serialize value based on type hint with comprehensive error handling."""
        debug_ctx = get_debug_context()
        
        try:
            if value is None:
                debug_ctx.log_serialization("serialize", "None", 0)
                return b""
            
            # Handle basic types
            if self.type_hint in (int, float, str, bool):
                data = json.dumps(value).encode()
                debug_ctx.log_serialization("serialize", self.type_hint.__name__, len(data))
                return data
            
            # Handle generic types like List[T], Dict[K, V]
            elif get_origin(self.type_hint) in (list, dict, tuple, set):
                data = json.dumps(value, default=self._json_serializer).encode()
                debug_ctx.log_serialization("serialize", str(self.type_hint), len(data))
                return data
            
            # Handle Pydantic models
            elif hasattr(self.type_hint, 'model_dump_json'):
                data = value.model_dump_json().encode()
                debug_ctx.log_serialization("serialize", "Pydantic", len(data))
                return data
            
            # Handle datetime
            elif self.type_hint == datetime:
                data = value.isoformat().encode()
                debug_ctx.log_serialization("serialize", "datetime", len(data))
                return data
            
            # Handle UUID
            elif self.type_hint == UUID:
                data = str(value).encode()
                debug_ctx.log_serialization("serialize", "UUID", len(data))
                return data
            
            else:
                # Try JSON first, fallback to pickle
                try:
                    data = json.dumps(value, default=self._json_serializer).encode()
                    debug_ctx.log_serialization("serialize", "JSON", len(data))
                    return data
                except (TypeError, ValueError):
                    data = pickle.dumps(value)
                    debug_ctx.log_serialization("serialize", "pickle", len(data))
                    return data
                    
        except Exception as e:
            debug_ctx.log_serialization("serialize", str(self.type_hint), error=e, success=False)
            raise SerializationError(
                f"Failed to serialize field '{self.name}' of type {self.type_hint.__name__}",
                error_code="SERIALIZATION_ERROR",
                details={
                    'field_name': self.name,
                    'field_type': self.type_hint.__name__,
                    'value_type': type(value).__name__,
                    'index': self.index
                }
            ) from e
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for complex types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
            
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value based on type hint with comprehensive error handling."""
        debug_ctx = get_debug_context()
        
        try:
            if not data:
                debug_ctx.log_serialization("deserialize", "empty", 0)
                return self.default_value
            
            # Handle basic types
            if self.type_hint in (int, float, str, bool):
                value = json.loads(data.decode())
                debug_ctx.log_serialization("deserialize", self.type_hint.__name__, len(data))
                return value
            
            # Handle generic types like List[T], Dict[K, V]
            elif get_origin(self.type_hint) in (list, dict, tuple, set):
                value = json.loads(data.decode())
                debug_ctx.log_serialization("deserialize", str(self.type_hint), len(data))
                return value
            
            # Handle Pydantic models
            elif hasattr(self.type_hint, 'model_validate_json'):
                value = self.type_hint.model_validate_json(data)
                debug_ctx.log_serialization("deserialize", "Pydantic", len(data))
                return value
            
            # Handle datetime
            elif self.type_hint == datetime:
                value = datetime.fromisoformat(data.decode())
                debug_ctx.log_serialization("deserialize", "datetime", len(data))
                return value
            
            # Handle UUID
            elif self.type_hint == UUID:
                value = UUID(data.decode())
                debug_ctx.log_serialization("deserialize", "UUID", len(data))
                return value
            
            else:
                # Try JSON first, fallback to pickle
                try:
                    value = json.loads(data.decode())
                    debug_ctx.log_serialization("deserialize", "JSON", len(data))
                    return value
                except (json.JSONDecodeError, UnicodeDecodeError):
                    value = pickle.loads(data)
                    debug_ctx.log_serialization("deserialize", "pickle", len(data))
                    return value
                    
        except Exception as e:
            debug_ctx.log_serialization("deserialize", str(self.type_hint), error=e, success=False)
            
            # Log the error but return default value instead of raising
            debug_ctx.log(DebugLevel.WARNING, f"Deserialization failed for {self.name}, using default: {e}")
            return self.default_value
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics for this state descriptor."""
        return self.metrics
    
    def reset_performance_metrics(self):
        """Reset performance metrics for this state descriptor."""
        self.metrics = PerformanceMetrics()
