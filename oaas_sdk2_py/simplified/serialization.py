"""
OaaS SDK Unified Serialization System

This module provides a unified serialization system that can be used by both
RPC parameter handling and state management, ensuring consistent type support
across the entire SDK.
"""

import json
import pickle
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, get_origin, get_args, Union, Tuple, Set
from uuid import UUID

from .errors import SerializationError, ValidationError, get_debug_context, DebugLevel
from .performance import PerformanceMetrics


class RpcSerializationError(Exception):
    """Enhanced RPC serialization error with detailed context."""
    
    def __init__(self, message: str, error_code: str, details: Dict[str, Any]):
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class RpcPerformanceMetrics:
    """Performance metrics for RPC serialization operations."""
    
    def __init__(self):
        self.serialization_metrics = PerformanceMetrics()
        self.deserialization_metrics = PerformanceMetrics()
        
    def record_serialization(self, duration: float, success: bool, data_size: int):
        """Record serialization performance metrics."""
        self.serialization_metrics.record_call(duration, success, data_size)
        
    def record_deserialization(self, duration: float, success: bool, data_size: int):
        """Record deserialization performance metrics."""
        self.deserialization_metrics.record_call(duration, success, data_size)


class UnifiedSerializer:
    """
    Unified serialization system for both RPC and state management.
    
    This class provides comprehensive type support including:
    - Basic types (int, float, str, bool, bytes)
    - Collection types (List[T], Dict[K,V], Tuple, Set)
    - Optional/Union types
    - DateTime/UUID types
    - Pydantic models with validation
    - Complex nested structures
    - Performance monitoring and error handling
    """
    
    def __init__(self):
        self.performance_metrics = RpcPerformanceMetrics()
        
    def serialize(self, value: Any, type_hint: Optional[Type] = None) -> bytes:
        """
        Serialize any value with optional type hint.
        
        Args:
            value: The value to serialize
            type_hint: Optional type hint for better serialization
            
        Returns:
            Serialized bytes
            
        Raises:
            SerializationError: If serialization fails
        """
        debug_ctx = get_debug_context()
        start_time = time.time() if debug_ctx.performance_monitoring else None
        
        try:
            result = self._serialize_value(value, type_hint)
            
            # Record performance metrics
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                self.performance_metrics.record_serialization(duration, True, len(result))
            
            return result
            
        except Exception as e:
            # Record performance metrics
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                self.performance_metrics.record_serialization(duration, False, 0)
            
            raise SerializationError(
                f"Failed to serialize value of type {type(value).__name__}",
                error_code="SERIALIZATION_ERROR",
                details={
                    'value_type': type(value).__name__,
                    'type_hint': type_hint.__name__ if type_hint else None,
                    'error': str(e)
                }
            ) from e
    
    def deserialize(self, data: bytes, type_hint: Type) -> Any:
        """
        Deserialize bytes to typed value.
        
        Args:
            data: The bytes to deserialize
            type_hint: The target type
            
        Returns:
            Deserialized value
            
        Raises:
            SerializationError: If deserialization fails
        """
        debug_ctx = get_debug_context()
        start_time = time.time() if debug_ctx.performance_monitoring else None
        
        try:
            result = self._deserialize_value(data, type_hint)
            
            # Record performance metrics
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                self.performance_metrics.record_deserialization(duration, True, len(data))
            
            return result
            
        except Exception as e:
            # Record performance metrics
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                self.performance_metrics.record_deserialization(duration, False, len(data))
            
            raise SerializationError(
                f"Failed to deserialize data to type {type_hint.__name__}",
                error_code="DESERIALIZATION_ERROR",
                details={
                    'type_hint': type_hint.__name__,
                    'data_size': len(data),
                    'error': str(e)
                }
            ) from e
    
    def convert_value(self, value: Any, target_type: Type) -> Any:
        """
        Convert value to target type with validation.
        
        Args:
            value: The value to convert
            target_type: The target type
            
        Returns:
            Converted value
            
        Raises:
            ValidationError: If conversion fails
        """
        debug_ctx = get_debug_context()
        
        try:
            return self._convert_value(value, target_type)
            
        except Exception as e:
            if isinstance(e, (ValidationError, SerializationError)):
                raise
            
            debug_ctx.log(DebugLevel.ERROR, f"Unexpected error in convert_value: {e}")
            raise ValidationError(
                f"Unexpected error converting value to {target_type.__name__}",
                error_code="CONVERSION_ERROR",
                details={'target_type': target_type.__name__, 'error': str(e)}
            ) from e
    
    def _serialize_value(self, value: Any, type_hint: Optional[Type] = None) -> bytes:
        """Internal serialization logic."""
        debug_ctx = get_debug_context()
        
        try:
            if value is None:
                debug_ctx.log_serialization("serialize", "None", 0)
                return b""
            
            # Handle basic types
            if type_hint and type_hint in (int, float, str, bool):
                data = json.dumps(value).encode()
                debug_ctx.log_serialization("serialize", type_hint.__name__, len(data))
                return data
            elif isinstance(value, (int, float, str, bool)):
                data = json.dumps(value).encode()
                debug_ctx.log_serialization("serialize", type(value).__name__, len(data))
                return data
            
            # Handle bytes
            elif isinstance(value, bytes):
                debug_ctx.log_serialization("serialize", "bytes", len(value))
                return value
            
            # Handle generic types like List[T], Dict[K, V]
            elif type_hint and get_origin(type_hint) in (list, dict, tuple, set):
                # Convert sets to lists for JSON serialization
                if isinstance(value, set):
                    data = json.dumps(list(value), default=self._json_serializer).encode()
                else:
                    data = json.dumps(value, default=self._json_serializer).encode()
                debug_ctx.log_serialization("serialize", str(type_hint), len(data))
                return data
            elif isinstance(value, (list, dict, tuple, set)):
                # Convert sets to lists for JSON serialization
                if isinstance(value, set):
                    data = json.dumps(list(value), default=self._json_serializer).encode()
                else:
                    data = json.dumps(value, default=self._json_serializer).encode()
                debug_ctx.log_serialization("serialize", type(value).__name__, len(data))
                return data
            
            # Handle Pydantic models
            elif hasattr(value, 'model_dump_json'):
                data = value.model_dump_json().encode()
                debug_ctx.log_serialization("serialize", "Pydantic", len(data))
                return data
            
            # Handle datetime
            elif isinstance(value, datetime):
                data = value.isoformat().encode()
                debug_ctx.log_serialization("serialize", "datetime", len(data))
                return data
            
            # Handle UUID
            elif isinstance(value, UUID):
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
            debug_ctx.log_serialization("serialize", str(type_hint) if type_hint else "unknown", error=e, success=False)
            raise
    
    def _deserialize_value(self, data: bytes, type_hint: Type) -> Any:
        """Internal deserialization logic."""
        debug_ctx = get_debug_context()
        
        try:
            if not data:
                debug_ctx.log_serialization("deserialize", "empty", 0)
                return None
            
            # Handle basic types
            if type_hint in (int, float, str, bool):
                value = json.loads(data.decode())
                # Validate the type after JSON parsing
                if not isinstance(value, type_hint):
                    raise SerializationError(
                        f"Type mismatch: expected {type_hint.__name__}, got {type(value).__name__}",
                        error_code="TYPE_MISMATCH_ERROR",
                        details={'expected_type': type_hint.__name__, 'actual_type': type(value).__name__}
                    )
                debug_ctx.log_serialization("deserialize", type_hint.__name__, len(data))
                return value
            
            # Handle bytes
            elif type_hint == bytes:
                debug_ctx.log_serialization("deserialize", "bytes", len(data))
                return data
            
            # Handle generic types like List[T], Dict[K, V]
            elif get_origin(type_hint) in (list, dict, tuple, set):
                value = json.loads(data.decode())
                converted_value = self._convert_value(value, type_hint)
                debug_ctx.log_serialization("deserialize", str(type_hint), len(data))
                return converted_value
            
            # Handle Pydantic models
            elif hasattr(type_hint, 'model_validate_json'):
                value = type_hint.model_validate_json(data)
                debug_ctx.log_serialization("deserialize", "Pydantic", len(data))
                return value
            
            # Handle datetime
            elif type_hint == datetime:
                value = datetime.fromisoformat(data.decode())
                debug_ctx.log_serialization("deserialize", "datetime", len(data))
                return value
            
            # Handle UUID
            elif type_hint == UUID:
                value = UUID(data.decode())
                debug_ctx.log_serialization("deserialize", "UUID", len(data))
                return value
            
            # Handle Union types
            elif get_origin(type_hint) is Union:
                # Try JSON first
                try:
                    json_value = json.loads(data.decode())
                    converted_value = self._convert_value(json_value, type_hint)
                    debug_ctx.log_serialization("deserialize", "Union", len(data))
                    return converted_value
                except:
                    # Fallback to pickle
                    value = pickle.loads(data)
                    debug_ctx.log_serialization("deserialize", "Union-pickle", len(data))
                    return value
            
            else:
                # Try JSON first, fallback to pickle
                try:
                    json_value = json.loads(data.decode())
                    converted_value = self._convert_value(json_value, type_hint)
                    debug_ctx.log_serialization("deserialize", "JSON", len(data))
                    return converted_value
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        value = pickle.loads(data)
                        debug_ctx.log_serialization("deserialize", "pickle", len(data))
                        return value
                    except Exception as pickle_error:
                        debug_ctx.log_serialization("deserialize", str(type_hint), error=pickle_error, success=False)
                        raise SerializationError(
                            f"Failed to deserialize data as JSON or pickle for type {type_hint.__name__}",
                            error_code="DESERIALIZATION_ERROR",
                            details={'type_hint': type_hint.__name__, 'data_size': len(data)}
                        ) from pickle_error
                    
        except Exception as e:
            debug_ctx.log_serialization("deserialize", str(type_hint), error=e, success=False)
            if isinstance(e, SerializationError):
                raise
            raise SerializationError(
                f"Failed to deserialize data to type {type_hint.__name__}",
                error_code="DESERIALIZATION_ERROR",
                details={'type_hint': type_hint.__name__, 'data_size': len(data), 'error': str(e)}
            ) from e
    
    def _convert_value(self, value: Any, target_type: Type) -> Any:
        """Convert value to the expected type with comprehensive error handling."""
        debug_ctx = get_debug_context()
        
        try:
            # Handle None values first
            if value is None:
                return None
            
            # Handle basic type conversions
            if target_type in (int, float, str, bool):
                try:
                    # Check if it's already the right type
                    if isinstance(value, target_type):
                        return value
                    return target_type(value)
                except (ValueError, TypeError) as e:
                    debug_ctx.log(DebugLevel.WARNING, f"Basic type conversion failed: {e}")
                    raise ValidationError(
                        f"Cannot convert {type(value).__name__} to {target_type.__name__}",
                        error_code="TYPE_CONVERSION_ERROR",
                        details={'value': str(value), 'target_type': target_type.__name__}
                    ) from e
            
            # Handle bytes
            elif target_type == bytes:
                if isinstance(value, bytes):
                    return value
                elif isinstance(value, str):
                    return value.encode()
                else:
                    return str(value).encode()
            
            # Handle generic types (List, Dict, Union, etc.)
            origin = get_origin(target_type)
            if origin is not None:
                # Handle list types
                if origin is list:
                    if isinstance(value, list):
                        return self._convert_list_elements(value, target_type)
                    elif isinstance(value, (tuple, set)):
                        return self._convert_list_elements(list(value), target_type)
                    else:
                        return [value]
                
                # Handle dict types
                elif origin is dict:
                    if isinstance(value, dict):
                        return self._convert_dict_elements(value, target_type)
                    else:
                        debug_ctx.log(DebugLevel.WARNING, f"Cannot convert {type(value).__name__} to dict")
                        return {}
                
                # Handle tuple types
                elif origin is tuple:
                    if isinstance(value, (list, tuple)):
                        return tuple(self._convert_list_elements(list(value), target_type))
                    else:
                        return (value,)
                
                # Handle set types
                elif origin is set:
                    if isinstance(value, (list, tuple, set)):
                        return set(self._convert_list_elements(list(value), target_type))
                    else:
                        return {value}
                
                # Handle Union types (including Optional)
                elif origin is Union:
                    return self._convert_union_value(value, target_type)
                
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
                if isinstance(value, target_type):
                    return value
            except TypeError:
                # isinstance failed, skip this check
                pass
            
            # Handle Pydantic models
            if hasattr(target_type, 'model_validate'):
                try:
                    if isinstance(value, dict):
                        return target_type.model_validate(value)
                    elif hasattr(value, 'model_dump'):  # Already a Pydantic model
                        return value
                    else:
                        return target_type(value)
                except Exception as e:
                    debug_ctx.log(DebugLevel.WARNING, f"Pydantic model validation failed: {e}")
                    raise ValidationError(
                        f"Invalid data for Pydantic model {target_type.__name__}",
                        error_code="PYDANTIC_VALIDATION_ERROR",
                        details={'model_type': target_type.__name__}
                    ) from e
            
            # Handle datetime
            if target_type == datetime:
                if isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value)
                    except ValueError as e:
                        raise ValidationError(
                            f"Invalid datetime format",
                            error_code="DATETIME_FORMAT_ERROR",
                            details={'value': value}
                        ) from e
                elif isinstance(value, datetime):
                    return value
            
            # Handle UUID
            if target_type == UUID:
                if isinstance(value, str):
                    try:
                        return UUID(value)
                    except ValueError as e:
                        raise ValidationError(
                            f"Invalid UUID format",
                            error_code="UUID_FORMAT_ERROR",
                            details={'value': value}
                        ) from e
                elif isinstance(value, UUID):
                    return value
            
            # For other types, try direct conversion or return as-is
            try:
                # For custom classes, try to create instance with dict data
                if isinstance(value, dict) and hasattr(target_type, '__init__'):
                    return target_type(**value)
                else:
                    return target_type(value)
            except Exception as e:
                debug_ctx.log(DebugLevel.WARNING, f"Direct type conversion failed: {e}")
                # Return the value as-is if conversion fails
                return value
                
        except Exception as e:
            if isinstance(e, (ValidationError, SerializationError)):
                raise
            
            debug_ctx.log(DebugLevel.ERROR, f"Unexpected error in _convert_value: {e}")
            raise ValidationError(
                f"Unexpected error converting value to {target_type.__name__}",
                error_code="CONVERSION_ERROR",
                details={'target_type': target_type.__name__, 'error': str(e)}
            ) from e
    
    def _convert_list_elements(self, value_list: List[Any], target_type: Type) -> List[Any]:
        """Convert list elements to the correct type if type arguments are available."""
        type_args = get_args(target_type)
        if not type_args:
            return value_list
        
        origin = get_origin(target_type)
        
        # Handle tuple with multiple type arguments
        if origin is tuple and len(type_args) > 1:
            converted_list = []
            for i, item in enumerate(value_list):
                try:
                    if i < len(type_args):
                        element_type = type_args[i]
                        if element_type == Any:
                            converted_list.append(item)
                        elif isinstance(item, element_type):
                            converted_list.append(item)
                        else:
                            converted_list.append(self._convert_value(item, element_type))
                    else:
                        # For extra elements, use the last type or Any
                        converted_list.append(item)
                except Exception as e:
                    debug_ctx = get_debug_context()
                    debug_ctx.log(DebugLevel.WARNING, f"List element conversion failed at index {i}: {e}")
                    # Keep original item if conversion fails
                    converted_list.append(item)
            return converted_list
        
        # Handle list, set, and single-type tuple
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
                    converted_list.append(self._convert_value(item, element_type))
            except Exception as e:
                debug_ctx = get_debug_context()
                debug_ctx.log(DebugLevel.WARNING, f"List element conversion failed at index {i}: {e}")
                # Keep original item if conversion fails
                converted_list.append(item)
        
        return converted_list
    
    def _convert_dict_elements(self, value_dict: Dict[Any, Any], target_type: Type) -> Dict[Any, Any]:
        """Convert dict elements to the correct type if type arguments are available."""
        type_args = get_args(target_type)
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
                    converted_key = self._convert_value(k, key_type)
                
                # Convert value
                if value_type == Any:
                    converted_value = v
                elif isinstance(v, value_type):
                    converted_value = v
                else:
                    converted_value = self._convert_value(v, value_type)
                
                converted_dict[converted_key] = converted_value
                
            except Exception as e:
                debug_ctx = get_debug_context()
                debug_ctx.log(DebugLevel.WARNING, f"Dict element conversion failed for key {k}: {e}")
                # Keep original key-value pair if conversion fails
                converted_dict[k] = v
        
        return converted_dict
    
    def _convert_union_value(self, value: Any, target_type: Type) -> Any:
        """Convert value for Union types (including Optional)."""
        type_args = get_args(target_type)
        if not type_args:
            return value
        
        # Handle Optional (Union[T, None])
        if len(type_args) == 2 and type(None) in type_args:
            if value is None:
                return None
            non_none_type = next(t for t in type_args if t is not type(None))
            try:
                return self._convert_value(value, non_none_type)
            except Exception:
                return value
        
        # Try each type in the union
        for union_type in type_args:
            try:
                if isinstance(value, union_type):
                    return value
                return self._convert_value(value, union_type)
            except Exception:
                continue
        
        # If no conversion worked, return as-is
        return value
    
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
    
    def get_performance_metrics(self) -> RpcPerformanceMetrics:
        """Get performance metrics for the serializer."""
        return self.performance_metrics
    
    def reset_performance_metrics(self):
        """Reset performance metrics."""
        self.performance_metrics = RpcPerformanceMetrics()