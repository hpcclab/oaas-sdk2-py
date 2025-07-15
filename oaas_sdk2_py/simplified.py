"""
OaaS SDK Simplified Interface - Phase 1 Week 1 Implementation

This module provides a simplified interface for the OaaS SDK that maintains
backward compatibility while offering a more intuitive developer experience.

Key Components:
- OaasObject: Simplified base class with auto-serialization
- OaasService: Global registry and decorator system
- OaasConfig: Unified configuration object
- State descriptors: Automatic state management

Design Philosophy:
- Maintain 100% backward compatibility with existing BaseObject, ClsMeta, FuncMeta
- Provide simplified interface on top of existing robust architecture
- Support automatic session management and state serialization
- Use modern Python patterns (type hints, descriptors, decorators)
"""

import json
import inspect
import pickle
import threading
import weakref
import asyncio
import logging
import traceback
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar, Union, get_type_hints, get_origin, get_args, List, Callable
from uuid import UUID
from functools import wraps
from contextlib import contextmanager
import time
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, HttpUrl, Field
from pydantic_settings import BaseSettings

from .obj import BaseObject
from .model import ClsMeta, FuncMeta
from .engine import Oparaca
from .session import Session
from .config import OprcConfig

# Type variables for generic typing
T = TypeVar('T')
StateType = TypeVar('StateType')


# =============================================================================
# ERROR HANDLING AND DEBUGGING SUPPORT
# =============================================================================

class OaasError(Exception):
    """Base exception class for OaaS SDK errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = datetime.now()
        self.traceback_info = traceback.format_exc() if sys.exc_info()[0] else None


class SerializationError(OaasError):
    """Raised when serialization/deserialization fails."""
    pass


class DeserializationError(OaasError):
    """Raised when deserialization fails."""
    pass


class ValidationError(OaasError):
    """Raised when validation fails."""
    pass


class ConfigurationError(OaasError):
    """Raised when configuration is invalid."""
    pass


class SessionError(OaasError):
    """Raised when session operations fail."""
    pass


class DecoratorError(OaasError):
    """Raised when decorator operations fail."""
    pass


class DebugLevel(Enum):
    """Debug levels for OaaS SDK"""
    NONE = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5


@dataclass
class DebugContext:
    """Context for debugging information"""
    level: DebugLevel = DebugLevel.INFO
    enabled: bool = True
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger('oaas_sdk'))
    trace_calls: bool = False
    trace_serialization: bool = False
    trace_session_operations: bool = False
    performance_monitoring: bool = False
    
    def __post_init__(self):
        # Configure logger
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(self._get_log_level())
    
    def _get_log_level(self) -> int:
        """Convert DebugLevel to logging level"""
        mapping = {
            DebugLevel.NONE: logging.CRITICAL + 1,
            DebugLevel.ERROR: logging.ERROR,
            DebugLevel.WARNING: logging.WARNING,
            DebugLevel.INFO: logging.INFO,
            DebugLevel.DEBUG: logging.DEBUG,
            DebugLevel.TRACE: logging.DEBUG
        }
        return mapping.get(self.level, logging.INFO)
    
    def log(self, level: DebugLevel, message: str, **kwargs):
        """Log a message with context"""
        if not self.enabled or level.value > self.level.value:
            return
            
        log_level = self._get_log_level()
        extra_info = ""
        if kwargs:
            extra_info = f" | {json.dumps(kwargs, default=str)}"
        
        self.logger.log(log_level, f"{message}{extra_info}")
    
    def trace_call(self, func_name: str, args: tuple, kwargs: dict, result: Any = None, error: Exception = None):
        """Trace function calls"""
        if not self.trace_calls:
            return
            
        call_info = {
            'function': func_name,
            'args_count': len(args),
            'kwargs_keys': list(kwargs.keys()),
            'success': error is None
        }
        
        if error:
            call_info['error'] = str(error)
            call_info['error_type'] = type(error).__name__
        
        self.log(DebugLevel.TRACE, f"Function call: {func_name}", **call_info)
    
    def log_serialization(self, operation: str, data_type: str, size: int = None, success: bool = True, error: Exception = None):
        """Log serialization operations"""
        if not self.trace_serialization:
            return
            
        ser_info = {
            'operation': operation,
            'data_type': data_type,
            'success': success
        }
        
        if size is not None:
            ser_info['size_bytes'] = size
        
        if error:
            ser_info['error'] = str(error)
            ser_info['error_type'] = type(error).__name__
        
        self.log(DebugLevel.TRACE, f"Serialization: {operation}", **ser_info)


# Global debug context
_debug_context = DebugContext()


def get_debug_context() -> DebugContext:
    """Get the global debug context"""
    return _debug_context


def configure_debug(level: DebugLevel = DebugLevel.INFO,
                   trace_calls: bool = False,
                   trace_serialization: bool = False,
                   trace_session_operations: bool = False,
                   performance_monitoring: bool = False):
    """Configure global debug settings"""
    global _debug_context
    _debug_context.level = level
    _debug_context.trace_calls = trace_calls
    _debug_context.trace_serialization = trace_serialization
    _debug_context.trace_session_operations = trace_session_operations
    _debug_context.performance_monitoring = performance_monitoring
    _debug_context.logger.setLevel(_debug_context._get_log_level())


def debug_wrapper(func: Callable) -> Callable:
    """Decorator for debugging function calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        debug_ctx = get_debug_context()
        start_time = time.time() if debug_ctx.performance_monitoring else None
        
        try:
            result = func(*args, **kwargs)
            
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                debug_ctx.log(DebugLevel.DEBUG, f"Performance: {func.__name__} took {duration:.4f}s")
            
            debug_ctx.trace_call(func.__name__, args, kwargs, result=result)
            return result
            
        except Exception as e:
            debug_ctx.trace_call(func.__name__, args, kwargs, error=e)
            raise
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        debug_ctx = get_debug_context()
        start_time = time.time() if debug_ctx.performance_monitoring else None
        
        try:
            result = await func(*args, **kwargs)
            
            if debug_ctx.performance_monitoring and start_time:
                duration = time.time() - start_time
                debug_ctx.log(DebugLevel.DEBUG, f"Performance: {func.__name__} took {duration:.4f}s")
            
            debug_ctx.trace_call(func.__name__, args, kwargs, result=result)
            return result
            
        except Exception as e:
            debug_ctx.trace_call(func.__name__, args, kwargs, error=e)
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""
    call_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    error_count: int = 0
    
    def record_call(self, duration: float, success: bool = True):
        """Record a function call"""
        self.call_count += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        
        if not success:
            self.error_count += 1
    
    @property
    def average_duration(self) -> float:
        """Get average call duration"""
        return self.total_duration / self.call_count if self.call_count > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Get success rate"""
        return (self.call_count - self.error_count) / self.call_count if self.call_count > 0 else 1.0


# Global performance metrics
_performance_metrics: Dict[str, PerformanceMetrics] = {}


def get_performance_metrics(func_name: str = None) -> Union[PerformanceMetrics, Dict[str, PerformanceMetrics]]:
    """Get performance metrics for a function or all functions"""
    if func_name:
        return _performance_metrics.get(func_name, PerformanceMetrics())
    return _performance_metrics.copy()


def reset_performance_metrics():
    """Reset all performance metrics"""
    global _performance_metrics
    _performance_metrics.clear()


class AutoSessionManager:
    """
    Automatic session lifecycle management for OaaS SDK.
    
    This class provides transparent session management with auto-commit functionality,
    thread-safe session handling, and integration with the existing Session class.
    
    Features:
    - Automatic session creation and cleanup
    - Background auto-commit for state changes
    - Thread-safe session handling
    - Integration with existing Oparaca engine
    - Backward compatibility with manual session management
    """
    
    def __init__(self, oparaca: 'Oparaca'):
        self.oparaca = oparaca
        self._thread_sessions: Dict[int, 'Session'] = {}
        self._session_lock = threading.RLock()
        self._auto_commit_enabled = True
        self._auto_commit_interval = 1.0  # seconds
        self._auto_commit_timer = None
        self._pending_commits: set = set()
        self._commit_lock = threading.Lock()
        
        # Weak references to objects for cleanup
        self._managed_objects: weakref.WeakSet = weakref.WeakSet()
        
        # Start background auto-commit timer
        self._start_auto_commit_timer()
    
    def get_session(self, partition_id: Optional[int] = None) -> 'Session':
        """
        Get or create a session for the current thread.
        
        Args:
            partition_id: Optional partition ID (uses default if not provided)
            
        Returns:
            Session instance for the current thread
        """
        thread_id = threading.get_ident()
        
        with self._session_lock:
            if thread_id not in self._thread_sessions:
                session = self.oparaca.new_session(partition_id)
                self._thread_sessions[thread_id] = session
            return self._thread_sessions[thread_id]
    
    def create_object(self, cls_meta: 'ClsMeta', obj_id: Optional[int] = None,
                     local: bool = None, partition_id: Optional[int] = None) -> 'OaasObject':
        """
        Create a new object with automatic session management.
        
        Args:
            cls_meta: Class metadata
            obj_id: Optional object ID
            local: Whether to create locally
            partition_id: Optional partition ID
            
        Returns:
            Created object with auto-commit enabled
        """
        session = self.get_session(partition_id)
        obj = session.create_object(cls_meta, obj_id=obj_id, local=local or self.oparaca.mock_mode)
        
        # Enable auto-commit for the object
        obj._auto_commit = True
        obj._auto_session_manager = self
        
        # Add to managed objects
        self._managed_objects.add(obj)
        
        return obj
    
    def load_object(self, cls_meta: 'ClsMeta', obj_id: int,
                   partition_id: Optional[int] = None) -> 'OaasObject':
        """
        Load an existing object with automatic session management.
        
        Args:
            cls_meta: Class metadata
            obj_id: Object ID to load
            partition_id: Optional partition ID
            
        Returns:
            Loaded object with auto-commit enabled
        """
        session = self.get_session(partition_id)
        obj = session.load_object(cls_meta, obj_id)
        
        # Enable auto-commit for the object
        obj._auto_commit = True
        obj._auto_session_manager = self
        
        # Add to managed objects
        self._managed_objects.add(obj)
        
        return obj
    
    def schedule_commit(self, obj: 'OaasObject') -> None:
        """
        Schedule an object for auto-commit.
        
        Args:
            obj: Object to commit
        """
        if self._auto_commit_enabled:
            with self._commit_lock:
                self._pending_commits.add(obj)
    
    def commit_all(self) -> None:
        """
        Commit all pending changes across all managed sessions.
        """
        with self._session_lock:
            for session in self._thread_sessions.values():
                try:
                    session.commit()
                except Exception as e:
                    # Log error but continue with other sessions
                    import logging
                    logging.error(f"Error committing session: {e}")
        
        # Clear pending commits
        with self._commit_lock:
            self._pending_commits.clear()
    
    async def commit_all_async(self) -> None:
        """
        Asynchronously commit all pending changes across all managed sessions.
        """
        with self._session_lock:
            sessions = list(self._thread_sessions.values())
        
        # Commit all sessions concurrently
        commit_tasks = []
        for session in sessions:
            try:
                task = asyncio.create_task(session.commit_async())
                commit_tasks.append(task)
            except Exception as e:
                # Log error but continue with other sessions
                import logging
                logging.error(f"Error creating commit task: {e}")
        
        if commit_tasks:
            await asyncio.gather(*commit_tasks, return_exceptions=True)
        
        # Clear pending commits
        with self._commit_lock:
            self._pending_commits.clear()
    
    def _start_auto_commit_timer(self) -> None:
        """Start the background auto-commit timer."""
        if self._auto_commit_enabled:
            self._auto_commit_timer = threading.Timer(
                self._auto_commit_interval,
                self._auto_commit_background
            )
            self._auto_commit_timer.daemon = True
            self._auto_commit_timer.start()
    
    def _auto_commit_background(self) -> None:
        """Background auto-commit function."""
        try:
            if self._pending_commits:
                self.commit_all()
        except Exception as e:
            import logging
            logging.error(f"Error in background auto-commit: {e}")
        finally:
            # Restart timer
            self._start_auto_commit_timer()
    
    def cleanup_session(self, thread_id: Optional[int] = None) -> None:
        """
        Clean up session for a specific thread or current thread.
        
        Args:
            thread_id: Thread ID to clean up (uses current thread if not provided)
        """
        if thread_id is None:
            thread_id = threading.get_ident()
            
        with self._session_lock:
            if thread_id in self._thread_sessions:
                session = self._thread_sessions[thread_id]
                try:
                    session.commit()  # Final commit before cleanup
                except Exception as e:
                    import logging
                    logging.error(f"Error during session cleanup: {e}")
                del self._thread_sessions[thread_id]
    
    def shutdown(self) -> None:
        """
        Shutdown the auto session manager and clean up resources.
        """
        # Stop auto-commit timer
        if self._auto_commit_timer:
            self._auto_commit_timer.cancel()
            self._auto_commit_timer = None
        
        # Final commit of all sessions
        self.commit_all()
        
        # Clean up all sessions
        with self._session_lock:
            self._thread_sessions.clear()
        
        # Clear managed objects
        self._managed_objects.clear()
        
        # Clear pending commits
        with self._commit_lock:
            self._pending_commits.clear()
    
    @contextmanager
    def session_scope(self, partition_id: Optional[int] = None):
        """
        Context manager for explicit session scoping.
        
        Args:
            partition_id: Optional partition ID
            
        Yields:
            Session instance
        """
        session = self.get_session(partition_id)
        try:
            yield session
        finally:
            # Commit any pending changes in this scope
            try:
                session.commit()
            except Exception as e:
                import logging
                logging.error(f"Error committing session in scope: {e}")


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
            
            # Schedule auto-commit if enabled
            if hasattr(obj, '_auto_commit') and obj._auto_commit and hasattr(obj, '_auto_session_manager'):
                obj._auto_session_manager.schedule_commit(obj)
            
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
                    except:
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
            non_none_type = next(t for t in type_args if t != type(None))
            try:
                return non_none_type(value)
            except:
                return value
        
        # Try each type in the union
        for union_type in type_args:
            try:
                if isinstance(value, union_type):
                    return value
                return union_type(value)
            except:
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


class OaasObject(BaseObject):
    """
    Simplified base class with automatic state management and serialization.
    
    This class extends BaseObject to provide:
    - Automatic state detection from type hints
    - Transparent serialization/deserialization
    - Simplified object lifecycle management
    - Backward compatibility with existing BaseObject API
    """
    
    _state_fields: Dict[str, StateDescriptor] = {}
    _state_index_counter: int = 0
    
    def __init_subclass__(cls, **kwargs):
        """
        Automatically set up state management for subclasses.
        
        This method analyzes class annotations and creates StateDescriptor
        instances for each typed attribute, providing automatic serialization.
        """
        super().__init_subclass__(**kwargs)
        
        # Initialize state management
        cls._state_fields = {}
        cls._state_index_counter = 0
        
        # Get type hints for this class (not inherited ones)
        try:
            type_hints = get_type_hints(cls)
        except:
            # If type hints fail, skip state management
            type_hints = {}
        
        # Process each annotated attribute
        for name, type_hint in type_hints.items():
            if not name.startswith('_') and name not in ('meta', 'session'):  # Skip private attributes and BaseObject internals
                # Get default value if it exists
                default_value = getattr(cls, name, None)
                
                # Create descriptor for this field
                descriptor = StateDescriptor(
                    name=name,
                    type_hint=type_hint,
                    default_value=default_value,
                    index=cls._state_index_counter
                )
                
                # Replace class attribute with descriptor
                setattr(cls, name, descriptor)
                cls._state_fields[name] = descriptor
                cls._state_index_counter += 1
    
    @classmethod
    def create(cls, obj_id: Optional[int] = None, local: bool = None) -> 'OaasObject':
        """
        Create a new instance of this service with automatic session management.
        
        Args:
            obj_id: Optional object ID (auto-generated if not provided)
            local: Whether to create a local object (defaults to True in mock mode)
            
        Returns:
            New instance of the service
        """
        # Use the global service registry to get the class metadata
        service_name = getattr(cls, '_oaas_service_name', cls.__name__)
        package = getattr(cls, '_oaas_package', 'default')
        
        # Get or create the global oaas instance
        global_oaas = OaasService._get_global_oaas()
        
        # Default to local=True in mock mode for better testing
        if local is None:
            local = global_oaas.mock_mode
        
        # Get class metadata
        cls_meta = getattr(cls, '_oaas_cls_meta', None)
        
        if cls_meta is None:
            # Create metadata if not already created
            cls_meta = global_oaas.new_cls(service_name, package)
            cls._oaas_cls_meta = cls_meta
        
        # Use AutoSessionManager for automatic session management
        auto_session_manager = OaasService._get_auto_session_manager()
        obj = auto_session_manager.create_object(cls_meta, obj_id=obj_id, local=local)
        
        return obj
    
    @classmethod
    def load(cls, obj_id: int) -> 'OaasObject':
        """
        Load an existing instance of this service.
        
        Args:
            obj_id: ID of the object to load
            
        Returns:
            Loaded instance of the service
        """
        service_name = getattr(cls, '_oaas_service_name', cls.__name__)
        package = getattr(cls, '_oaas_package', 'default')
        
        # Get or create the global oaas instance
        global_oaas = OaasService._get_global_oaas()
        
        # Get class metadata
        cls_meta = getattr(cls, '_oaas_cls_meta', None)
        
        if cls_meta is None:
            # Create metadata if not already created
            cls_meta = global_oaas.new_cls(service_name, package)
            cls._oaas_cls_meta = cls_meta
        
        # Use AutoSessionManager for automatic session management
        auto_session_manager = OaasService._get_auto_session_manager()
        obj = auto_session_manager.load_object(cls_meta, obj_id)
        
        return obj


class OaasConfig(BaseSettings):
    """
    Unified configuration object for OaaS SDK.
    
    This class provides a cleaner interface for configuration while
    maintaining compatibility with the existing OprcConfig.
    """
    
    # Core server configuration
    server_url: HttpUrl = Field(default="http://localhost:10000", description="OaaS data manager URL")
    peers: Optional[str] = Field(default=None, description="Comma-separated list of Zenoh peers")
    default_partition: int = Field(default=0, description="Default partition ID")
    
    # Operational modes
    mock_mode: bool = Field(default=False, description="Enable mock mode for testing")
    async_mode: bool = Field(default=True, description="Enable async mode by default")
    
    # Performance settings
    auto_commit: bool = Field(default=True, description="Enable automatic transaction commits")
    batch_size: int = Field(default=100, description="Batch size for bulk operations")
    
    def to_oprc_config(self) -> OprcConfig:
        """Convert to legacy OprcConfig for backward compatibility."""
        return OprcConfig(
            oprc_odgm_url=self.server_url,
            oprc_zenoh_peers=self.peers,
            oprc_partition_default=self.default_partition
        )
    
    def get_zenoh_peers(self) -> Optional[list[str]]:
        """Get Zenoh peers as a list."""
        if self.peers is None:
            return None
        return self.peers.split(",")


class EnhancedMethodDecorator:
    """
    Enhanced method decorator with full feature parity to FuncMeta.
    
    This decorator provides all the features of FuncMeta while maintaining
    a simplified interface and adding comprehensive error handling.
    """
    
    def __init__(self, name: str = "", stateless: bool = False, strict: bool = False,
                 serve_with_agent: bool = False, timeout: Optional[float] = None,
                 retry_count: int = 0, retry_delay: float = 1.0):
        self.name = name
        self.stateless = stateless
        self.strict = strict
        self.serve_with_agent = serve_with_agent
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.metrics = PerformanceMetrics()
        
    def __call__(self, func):
        """Apply the enhanced method decorator"""
        debug_ctx = get_debug_context()
        
        # Store original function info
        original_func = func
        func_name = self.name if self.name else func.__name__
        
        # Create enhanced wrapper with full error handling
        if asyncio.iscoroutinefunction(func):
            enhanced_func = self._create_async_enhanced_wrapper(func, func_name)
        else:
            enhanced_func = self._create_sync_enhanced_wrapper(func, func_name)
        
        # Mark for OaaS processing
        enhanced_func._oaas_method = True
        enhanced_func._oaas_method_config = {
            'name': func_name,
            'stateless': self.stateless,
            'strict': self.strict,
            'serve_with_agent': self.serve_with_agent,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay
        }
        
        debug_ctx.log(DebugLevel.DEBUG, f"Enhanced method decorator applied to {func_name}")
        return enhanced_func
    
    def _create_async_enhanced_wrapper(self, func, func_name):
        """Create enhanced async wrapper with full error handling"""
        @wraps(func)
        async def enhanced_async_wrapper(obj_self, *args, **kwargs):
            debug_ctx = get_debug_context()
            start_time = time.time()
            
            try:
                # Performance monitoring
                if debug_ctx.performance_monitoring:
                    debug_ctx.log(DebugLevel.DEBUG, f"Starting async method {func_name}")
                
                # Apply retry logic
                last_exception = None
                for attempt in range(self.retry_count + 1):
                    try:
                        # Apply timeout if specified
                        if self.timeout:
                            result = await asyncio.wait_for(func(obj_self, *args, **kwargs), timeout=self.timeout)
                        else:
                            result = await func(obj_self, *args, **kwargs)
                        
                        # Record successful call
                        if debug_ctx.performance_monitoring:
                            duration = time.time() - start_time
                            self.metrics.record_call(duration, success=True)
                            debug_ctx.log(DebugLevel.DEBUG, f"Async method {func_name} completed in {duration:.4f}s")
                        
                        return result
                        
                    except asyncio.TimeoutError as e:
                        last_exception = e
                        debug_ctx.log(DebugLevel.WARNING, f"Timeout in async method {func_name}, attempt {attempt + 1}")
                        
                        if attempt < self.retry_count:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        break
                        
                    except Exception as e:
                        last_exception = e
                        debug_ctx.log(DebugLevel.WARNING, f"Error in async method {func_name}, attempt {attempt + 1}: {e}")
                        
                        if attempt < self.retry_count:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        break
                
                # Record failed call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=False)
                
                # If no retries were configured, re-raise the original exception
                if self.retry_count == 0:
                    raise last_exception
                
                # All retries failed
                raise DecoratorError(
                    f"Method {func_name} failed after {self.retry_count + 1} attempts",
                    error_code="METHOD_EXECUTION_ERROR",
                    details={
                        'method_name': func_name,
                        'attempts': self.retry_count + 1,
                        'last_error': str(last_exception)
                    }
                ) from last_exception
                
            except Exception as e:
                # Record failed call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=False)
                
                debug_ctx.log(DebugLevel.ERROR, f"Unhandled error in async method {func_name}: {e}")
                raise
        
        return enhanced_async_wrapper
    
    def _create_sync_enhanced_wrapper(self, func, func_name):
        """Create enhanced sync wrapper with full error handling"""
        @wraps(func)
        def enhanced_sync_wrapper(obj_self, *args, **kwargs):
            debug_ctx = get_debug_context()
            start_time = time.time()
            
            try:
                # Performance monitoring
                if debug_ctx.performance_monitoring:
                    debug_ctx.log(DebugLevel.DEBUG, f"Starting sync method {func_name}")
                
                # Apply retry logic
                last_exception = None
                for attempt in range(self.retry_count + 1):
                    try:
                        result = func(obj_self, *args, **kwargs)
                        
                        # Record successful call
                        if debug_ctx.performance_monitoring:
                            duration = time.time() - start_time
                            self.metrics.record_call(duration, success=True)
                            debug_ctx.log(DebugLevel.DEBUG, f"Sync method {func_name} completed in {duration:.4f}s")
                        
                        return result
                        
                    except Exception as e:
                        last_exception = e
                        debug_ctx.log(DebugLevel.WARNING, f"Error in sync method {func_name}, attempt {attempt + 1}: {e}")
                        
                        if attempt < self.retry_count:
                            time.sleep(self.retry_delay)
                            continue
                        break
                
                # Record failed call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=False)
                
                # If no retries were configured, re-raise the original exception
                if self.retry_count == 0:
                    raise last_exception
                
                # All retries failed
                raise DecoratorError(
                    f"Method {func_name} failed after {self.retry_count + 1} attempts",
                    error_code="METHOD_EXECUTION_ERROR",
                    details={
                        'method_name': func_name,
                        'attempts': self.retry_count + 1,
                        'last_error': str(last_exception)
                    }
                ) from last_exception
                
            except Exception as e:
                # Record failed call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=False)
                
                debug_ctx.log(DebugLevel.ERROR, f"Unhandled error in sync method {func_name}: {e}")
                raise
        
        return enhanced_sync_wrapper
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics for this method decorator."""
        return self.metrics
    
    def reset_performance_metrics(self):
        """Reset performance metrics for this method decorator."""
        self.metrics = PerformanceMetrics()


class OaasService:
    """
    Enhanced global service registry and decorator system.
    
    This class provides the main decorators and utilities for the simplified
    interface while maintaining full compatibility with the existing system.
    """
    
    _global_oaas: Optional[Oparaca] = None
    _global_config: Optional[OaasConfig] = None
    _auto_session_manager: Optional[AutoSessionManager] = None
    _registered_services: Dict[str, Type[OaasObject]] = {}
    _service_metrics: Dict[str, PerformanceMetrics] = {}
    
    @staticmethod
    def _get_global_oaas() -> Oparaca:
        """Get or create the global Oparaca instance."""
        if OaasService._global_oaas is None:
            config = OaasService._global_config
            if config is None:
                config = OaasConfig()
                OaasService._global_config = config
            
            # Create Oparaca instance with converted config
            oprc_config = config.to_oprc_config()
            OaasService._global_oaas = Oparaca(
                default_pkg="default",
                config=oprc_config,
                mock_mode=config.mock_mode,
                async_mode=config.async_mode
            )
        
        return OaasService._global_oaas
    
    @staticmethod
    def _get_auto_session_manager() -> AutoSessionManager:
        """Get or create the global AutoSessionManager instance."""
        if OaasService._auto_session_manager is None:
            global_oaas = OaasService._get_global_oaas()
            OaasService._auto_session_manager = AutoSessionManager(global_oaas)
        
        return OaasService._auto_session_manager
    
    @staticmethod
    def configure(config: OaasConfig) -> None:
        """Configure the global OaaS instance."""
        OaasService._global_config = config
        # Reset global oaas to force recreation with new config
        OaasService._global_oaas = None
        # Reset auto session manager to use new config
        if OaasService._auto_session_manager:
            OaasService._auto_session_manager.shutdown()
            OaasService._auto_session_manager = None
    
    @staticmethod
    def service(name: str, package: str = "default", update_callback: Optional[Callable] = None):
        """
        Enhanced decorator to register a class as an OaaS service with full feature parity.
        
        Args:
            name: Service name
            package: Package name (default: "default")
            update_callback: Optional callback function called after service registration
            
        Returns:
            Decorated class with OaaS service capabilities
        """
        def decorator(cls: Type[OaasObject]) -> Type[OaasObject]:
            debug_ctx = get_debug_context()
            start_time = time.time()
            
            try:
                debug_ctx.log(DebugLevel.DEBUG, f"Registering service {name} in package {package}")
                
                # Store service metadata
                cls._oaas_service_name = name
                cls._oaas_package = package
                
                # Get global oaas instance
                global_oaas = OaasService._get_global_oaas()
                
                # Create class metadata with enhanced error handling
                try:
                    cls_meta = global_oaas.new_cls(name, package)
                    if update_callback:
                        cls_meta.update = update_callback
                except Exception as e:
                    raise DecoratorError(
                        f"Failed to create class metadata for service {name}",
                        error_code="SERVICE_REGISTRATION_ERROR",
                        details={'service_name': name, 'package': package}
                    ) from e
                
                # Process methods marked with @oaas.method with enhanced configuration
                enhanced_methods = {}
                for attr_name in dir(cls):
                    if not attr_name.startswith('_'):
                        attr = getattr(cls, attr_name)
                        if callable(attr) and hasattr(attr, '_oaas_method'):
                            try:
                                # Get enhanced method configuration
                                method_config = getattr(attr, '_oaas_method_config', {})
                                
                                # Apply the legacy func decorator with enhanced configuration
                                decorated_method = cls_meta.func(
                                    name=method_config.get('name', attr_name),
                                    stateless=method_config.get('stateless', False),
                                    strict=method_config.get('strict', False),
                                    serve_with_agent=method_config.get('serve_with_agent', False)
                                )(attr)
                                
                                # Replace the method on the class
                                setattr(cls, attr_name, decorated_method)
                                enhanced_methods[attr_name] = method_config
                                
                                debug_ctx.log(DebugLevel.DEBUG, f"Enhanced method {attr_name} registered")
                                
                            except Exception as e:
                                debug_ctx.log(DebugLevel.ERROR, f"Failed to process method {attr_name}: {e}")
                                raise DecoratorError(
                                    f"Failed to process method {attr_name} in service {name}",
                                    error_code="METHOD_PROCESSING_ERROR",
                                    details={
                                        'service_name': name,
                                        'method_name': attr_name,
                                        'error': str(e)
                                    }
                                ) from e
                
                # Apply the legacy decorator to maintain compatibility
                decorated_cls = cls_meta(cls)
                
                # Store the class metadata for later use
                decorated_cls._oaas_cls_meta = cls_meta
                decorated_cls._oaas_enhanced_methods = enhanced_methods
                
                # Register the service with performance metrics
                service_key = f"{package}.{name}"
                OaasService._registered_services[service_key] = decorated_cls
                OaasService._service_metrics[service_key] = PerformanceMetrics()
                
                # Performance monitoring
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    OaasService._service_metrics[service_key].record_call(duration, success=True)
                    debug_ctx.log(DebugLevel.DEBUG, f"Service {name} registered in {duration:.4f}s")
                
                debug_ctx.log(DebugLevel.INFO, f"Service {name} successfully registered")
                return decorated_cls
                
            except Exception as e:
                # Performance monitoring for failed registration
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    service_key = f"{package}.{name}"
                    if service_key in OaasService._service_metrics:
                        OaasService._service_metrics[service_key].record_call(duration, success=False)
                
                debug_ctx.log(DebugLevel.ERROR, f"Failed to register service {name}: {e}")
                raise
        
        return decorator
    
    @staticmethod
    def method(func_or_name=None, *, name: str = "", stateless: bool = False, strict: bool = False,
               serve_with_agent: bool = False, timeout: Optional[float] = None,
               retry_count: int = 0, retry_delay: float = 1.0):
        """
        Enhanced decorator to register a method as an OaaS service method with full feature parity.
        
        This decorator provides all the features of FuncMeta while maintaining a simplified interface.
        Can be used as @oaas.method or @oaas.method(name="custom") for backward compatibility.
        
        Args:
            func_or_name: Function (for @oaas.method) or name (for @oaas.method(name="custom"))
            name: Optional method name override
            stateless: Whether the function doesn't modify object state
            strict: Whether to use strict validation when deserializing models
            serve_with_agent: Whether to serve with agent support
            timeout: Optional timeout in seconds for method execution
            retry_count: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
            
        Returns:
            Decorated method with enhanced OaaS capabilities
        """
        def decorator(func):
            debug_ctx = get_debug_context()
            debug_ctx.log(DebugLevel.DEBUG, f"Applying enhanced method decorator to {func.__name__}")
            
            # Create enhanced method decorator
            enhanced_decorator = EnhancedMethodDecorator(
                name=name,
                stateless=stateless,
                strict=strict,
                serve_with_agent=serve_with_agent,
                timeout=timeout,
                retry_count=retry_count,
                retry_delay=retry_delay
            )
            
            # Apply the enhanced decorator
            return enhanced_decorator(func)
        
        # Handle both @oaas.method and @oaas.method() usage
        if func_or_name is None:
            # Called as @oaas.method() - return decorator
            return decorator
        elif callable(func_or_name):
            # Called as @oaas.method - apply directly
            return decorator(func_or_name)
        else:
            # Called as @oaas.method("name") - treat first arg as name
            name = func_or_name
            return decorator
    
    @staticmethod
    def get_service(name: str, package: str = "default") -> Optional[Type[OaasObject]]:
        """Get a registered service by name with enhanced error handling."""
        debug_ctx = get_debug_context()
        service_key = f"{package}.{name}"
        
        try:
            service = OaasService._registered_services.get(service_key)
            if service:
                debug_ctx.log(DebugLevel.DEBUG, f"Retrieved service {name} from package {package}")
            else:
                debug_ctx.log(DebugLevel.WARNING, f"Service {name} not found in package {package}")
            return service
        except Exception as e:
            debug_ctx.log(DebugLevel.ERROR, f"Error retrieving service {name}: {e}")
            return None
    
    @staticmethod
    def list_services() -> Dict[str, Type[OaasObject]]:
        """List all registered services with enhanced information."""
        debug_ctx = get_debug_context()
        debug_ctx.log(DebugLevel.DEBUG, f"Listing {len(OaasService._registered_services)} registered services")
        return OaasService._registered_services.copy()
    
    @staticmethod
    def get_service_metrics(name: str = None, package: str = "default") -> Union[PerformanceMetrics, Dict[str, PerformanceMetrics]]:
        """
        Get performance metrics for a service or all services.
        
        Args:
            name: Optional service name (returns all if not provided)
            package: Package name for specific service
            
        Returns:
            Performance metrics for the service or all services
        """
        if name:
            service_key = f"{package}.{name}"
            return OaasService._service_metrics.get(service_key, PerformanceMetrics())
        return OaasService._service_metrics.copy()
    
    @staticmethod
    def reset_service_metrics(name: str = None, package: str = "default"):
        """
        Reset performance metrics for a service or all services.
        
        Args:
            name: Optional service name (resets all if not provided)
            package: Package name for specific service
        """
        if name:
            service_key = f"{package}.{name}"
            if service_key in OaasService._service_metrics:
                OaasService._service_metrics[service_key] = PerformanceMetrics()
        else:
            OaasService._service_metrics.clear()
    
    @staticmethod
    def get_service_info(name: str, package: str = "default") -> Dict[str, Any]:
        """
        Get comprehensive information about a registered service.
        
        Args:
            name: Service name
            package: Package name
            
        Returns:
            Dictionary with service information
        """
        service_key = f"{package}.{name}"
        service_cls = OaasService._registered_services.get(service_key)
        
        if not service_cls:
            return {}
        
        info = {
            'name': name,
            'package': package,
            'class_name': service_cls.__name__,
            'service_key': service_key,
            'state_fields': list(getattr(service_cls, '_state_fields', {}).keys()),
            'enhanced_methods': getattr(service_cls, '_oaas_enhanced_methods', {}),
            'metrics': OaasService._service_metrics.get(service_key, PerformanceMetrics()).__dict__
        }
        
        return info
    
    @staticmethod
    def validate_service_configuration(name: str, package: str = "default") -> Dict[str, Any]:
        """
        Validate service configuration and return validation results.
        
        Args:
            name: Service name
            package: Package name
            
        Returns:
            Dictionary with validation results
        """
        debug_ctx = get_debug_context()
        service_key = f"{package}.{name}"
        service_cls = OaasService._registered_services.get(service_key)
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        if not service_cls:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Service {name} not found in package {package}")
            return validation_results
        
        try:
            # Check if service has required metadata
            if not hasattr(service_cls, '_oaas_cls_meta'):
                validation_results['warnings'].append("Service missing class metadata")
            
            # Check state fields
            state_fields = getattr(service_cls, '_state_fields', {})
            if state_fields:
                validation_results['info'].append(f"Service has {len(state_fields)} state fields")
            
            # Check enhanced methods
            enhanced_methods = getattr(service_cls, '_oaas_enhanced_methods', {})
            if enhanced_methods:
                validation_results['info'].append(f"Service has {len(enhanced_methods)} enhanced methods")
            
            # Check performance metrics
            metrics = OaasService._service_metrics.get(service_key)
            if metrics and metrics.call_count > 0:
                validation_results['info'].append(f"Service has performance metrics: {metrics.call_count} calls")
                
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation error: {e}")
            debug_ctx.log(DebugLevel.ERROR, f"Service validation error for {name}: {e}")
        
        return validation_results
    
    @staticmethod
    def commit_all() -> None:
        """
        Commit all pending changes across all managed sessions.
        
        This provides a global commit function for backward compatibility
        and manual session management when needed.
        """
        auto_session_manager = OaasService._get_auto_session_manager()
        auto_session_manager.commit_all()
    
    @staticmethod
    async def commit_all_async() -> None:
        """
        Asynchronously commit all pending changes across all managed sessions.
        
        This provides a global async commit function for backward compatibility
        and manual session management when needed.
        """
        auto_session_manager = OaasService._get_auto_session_manager()
        await auto_session_manager.commit_all_async()
    
    @staticmethod
    def get_session(partition_id: Optional[int] = None) -> 'Session':
        """
        Get a session for the current thread.
        
        This provides access to the underlying session for advanced use cases
        while maintaining backward compatibility.
        
        Args:
            partition_id: Optional partition ID
            
        Returns:
            Session instance for the current thread
        """
        auto_session_manager = OaasService._get_auto_session_manager()
        return auto_session_manager.get_session(partition_id)
    
    @staticmethod
    @contextmanager
    def session_scope(partition_id: Optional[int] = None):
        """
        Context manager for explicit session scoping.
        
        Args:
            partition_id: Optional partition ID
            
        Yields:
            Session instance
        """
        auto_session_manager = OaasService._get_auto_session_manager()
        with auto_session_manager.session_scope(partition_id) as session:
            yield session
    
    @staticmethod
    def cleanup_session(thread_id: Optional[int] = None) -> None:
        """
        Clean up session for a specific thread or current thread.
        
        Args:
            thread_id: Thread ID to clean up (uses current thread if not provided)
        """
        auto_session_manager = OaasService._get_auto_session_manager()
        auto_session_manager.cleanup_session(thread_id)
    
    @staticmethod
    def shutdown() -> None:
        """
        Enhanced shutdown of the global OaaS service and clean up resources.
        
        This should be called when the application is shutting down to ensure
        all resources are properly cleaned up.
        """
        debug_ctx = get_debug_context()
        debug_ctx.log(DebugLevel.INFO, "Shutting down OaaS service")
        
        try:
            # Shutdown auto session manager
            if OaasService._auto_session_manager:
                debug_ctx.log(DebugLevel.DEBUG, "Shutting down AutoSessionManager")
                OaasService._auto_session_manager.shutdown()
                OaasService._auto_session_manager = None
            
            # Cleanup global oaas instance
            if OaasService._global_oaas:
                debug_ctx.log(DebugLevel.DEBUG, "Cleaning up global Oparaca instance")
                OaasService._global_oaas = None
            
            # Clear registered services
            service_count = len(OaasService._registered_services)
            if service_count > 0:
                debug_ctx.log(DebugLevel.DEBUG, f"Clearing {service_count} registered services")
                OaasService._registered_services.clear()
            
            # Clear service metrics
            metrics_count = len(OaasService._service_metrics)
            if metrics_count > 0:
                debug_ctx.log(DebugLevel.DEBUG, f"Clearing {metrics_count} service metrics")
                OaasService._service_metrics.clear()
            
            # Reset global config
            OaasService._global_config = None
            
            # Clear global performance metrics
            reset_performance_metrics()
            
            debug_ctx.log(DebugLevel.INFO, "OaaS service shutdown completed")
            
        except Exception as e:
            debug_ctx.log(DebugLevel.ERROR, f"Error during OaaS service shutdown: {e}")
            raise
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Get comprehensive system information about the OaaS service.
        
        Returns:
            Dictionary with system information
        """
        debug_ctx = get_debug_context()
        
        system_info = {
            'services': {
                'registered_count': len(OaasService._registered_services),
                'services': list(OaasService._registered_services.keys())
            },
            'performance': {
                'service_metrics': {k: v.__dict__ for k, v in OaasService._service_metrics.items()},
                'global_metrics': {k: v.__dict__ for k, v in get_performance_metrics().items()}
            },
            'configuration': {
                'has_global_config': OaasService._global_config is not None,
                'has_global_oaas': OaasService._global_oaas is not None,
                'has_auto_session_manager': OaasService._auto_session_manager is not None,
                'mock_mode': OaasService._global_config.mock_mode if OaasService._global_config else None
            },
            'debug': {
                'level': debug_ctx.level.name,
                'enabled': debug_ctx.enabled,
                'trace_calls': debug_ctx.trace_calls,
                'trace_serialization': debug_ctx.trace_serialization,
                'trace_session_operations': debug_ctx.trace_session_operations,
                'performance_monitoring': debug_ctx.performance_monitoring
            }
        }
        
        return system_info
    
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """
        Perform a health check of the OaaS service.
        
        Returns:
            Dictionary with health check results
        """
        debug_ctx = get_debug_context()
        health_status = {
            'healthy': True,
            'issues': [],
            'warnings': [],
            'info': []
        }
        
        try:
            # Check global oaas instance
            if OaasService._global_oaas is None:
                health_status['warnings'].append("Global Oparaca instance not initialized")
            else:
                health_status['info'].append("Global Oparaca instance is healthy")
            
            # Check auto session manager
            if OaasService._auto_session_manager is None:
                health_status['warnings'].append("AutoSessionManager not initialized")
            else:
                health_status['info'].append("AutoSessionManager is healthy")
            
            # Check registered services
            service_count = len(OaasService._registered_services)
            if service_count == 0:
                health_status['warnings'].append("No services registered")
            else:
                health_status['info'].append(f"{service_count} services registered")
            
            # Check service configurations
            invalid_services = []
            for service_key, service_cls in OaasService._registered_services.items():
                if not hasattr(service_cls, '_oaas_cls_meta'):
                    invalid_services.append(service_key)
            
            if invalid_services:
                health_status['healthy'] = False
                health_status['issues'].append(f"Services with invalid configuration: {invalid_services}")
            
            # Check performance metrics
            total_calls = sum(metrics.call_count for metrics in OaasService._service_metrics.values())
            total_errors = sum(metrics.error_count for metrics in OaasService._service_metrics.values())
            
            if total_calls > 0:
                error_rate = total_errors / total_calls
                if error_rate > 0.1:  # More than 10% error rate
                    health_status['warnings'].append(f"High error rate: {error_rate:.2%}")
                
                health_status['info'].append(f"Total calls: {total_calls}, errors: {total_errors}")
            
        except Exception as e:
            health_status['healthy'] = False
            health_status['issues'].append(f"Health check failed: {e}")
            debug_ctx.log(DebugLevel.ERROR, f"Health check error: {e}")
        
        return health_status


# Global instance for convenient access
oaas = OaasService()


# Convenience functions for backward compatibility
def create_object(cls: Type[OaasObject], obj_id: Optional[int] = None, local: bool = False) -> OaasObject:
    """Create an object instance (convenience function)."""
    return cls.create(obj_id=obj_id, local=local)

def load_object(cls: Type[OaasObject], obj_id: int) -> OaasObject:
    """Load an object instance (convenience function)."""
    return cls.load(obj_id=obj_id)


# Backward compatibility layer for existing Session API
class LegacySessionAdapter:
    """
    Adapter to provide backward compatibility with existing Session API.
    
    This class wraps the AutoSessionManager to provide the same interface
    as the traditional Session class while benefiting from automatic management.
    """
    
    def __init__(self, auto_session_manager: AutoSessionManager, partition_id: Optional[int] = None):
        self.auto_session_manager = auto_session_manager
        self._partition_id = partition_id
        self._underlying_session = auto_session_manager.get_session(partition_id)
    
    def create_object(self, cls_meta: 'ClsMeta', obj_id: Optional[int] = None, local: bool = False) -> 'OaasObject':
        """Create an object using the legacy Session API."""
        return self.auto_session_manager.create_object(cls_meta, obj_id=obj_id, local=local, partition_id=self._partition_id)
    
    def load_object(self, cls_meta: 'ClsMeta', obj_id: int) -> 'OaasObject':
        """Load an object using the legacy Session API."""
        return self.auto_session_manager.load_object(cls_meta, obj_id, partition_id=self._partition_id)
    
    def delete_object(self, cls_meta: 'ClsMeta', obj_id: int, partition_id: Optional[int] = None):
        """Delete an object using the legacy Session API."""
        return self._underlying_session.delete_object(cls_meta, obj_id, partition_id or self._partition_id)
    
    def commit(self):
        """Commit changes using the legacy Session API."""
        return self._underlying_session.commit()
    
    async def commit_async(self):
        """Asynchronously commit changes using the legacy Session API."""
        return await self._underlying_session.commit_async()
    
    def obj_rpc(self, req) -> Any:
        """Perform object RPC using the legacy Session API."""
        return self._underlying_session.obj_rpc(req)
    
    async def obj_rpc_async(self, req) -> Any:
        """Asynchronously perform object RPC using the legacy Session API."""
        return await self._underlying_session.obj_rpc_async(req)
    
    def fn_rpc(self, req) -> Any:
        """Perform function RPC using the legacy Session API."""
        return self._underlying_session.fn_rpc(req)
    
    async def fn_rpc_async(self, req) -> Any:
        """Asynchronously perform function RPC using the legacy Session API."""
        return await self._underlying_session.fn_rpc_async(req)
    
    def invoke_local(self, req) -> Any:
        """Invoke function locally using the legacy Session API."""
        return self._underlying_session.invoke_local(req)
    
    async def invoke_local_async(self, req) -> Any:
        """Asynchronously invoke function locally using the legacy Session API."""
        return await self._underlying_session.invoke_local_async(req)
    
    # Expose underlying session attributes for full compatibility
    @property
    def local_obj_dict(self):
        return self._underlying_session.local_obj_dict
    
    @property
    def remote_obj_dict(self):
        return self._underlying_session.remote_obj_dict
    
    @property
    def delete_obj_set(self):
        return self._underlying_session.delete_obj_set
    
    @property
    def partition_id(self):
        return self._partition_id if self._partition_id is not None else self._underlying_session.partition_id
    
    @property
    def rpc_manager(self):
        return self._underlying_session.rpc_manager
    
    @property
    def data_manager(self):
        return self._underlying_session.data_manager
    
    @property
    def meta_repo(self):
        return self._underlying_session.meta_repo
    
    @property
    def local_only(self):
        return self._underlying_session.local_only


# Enhanced backward compatibility functions
def new_session(partition_id: Optional[int] = None) -> LegacySessionAdapter:
    """
    Create a new session with backward compatibility.
    
    This function provides the same interface as the traditional session creation
    but uses the new AutoSessionManager underneath.
    
    Args:
        partition_id: Optional partition ID
        
    Returns:
        Legacy session adapter with automatic management
    """
    auto_session_manager = OaasService._get_auto_session_manager()
    return LegacySessionAdapter(auto_session_manager, partition_id)


def get_global_oaas() -> Oparaca:
    """
    Get the global Oparaca instance for backward compatibility.
    
    Returns:
        Global Oparaca instance
    """
    return OaasService._get_global_oaas()


def configure_oaas(config: OaasConfig) -> None:
    """
    Configure the global OaaS instance.
    
    Args:
        config: OaaS configuration object
    """
    OaasService.configure(config)


# Auto-commit control functions
def enable_auto_commit() -> None:
    """Enable automatic commit functionality."""
    auto_session_manager = OaasService._get_auto_session_manager()
    auto_session_manager._auto_commit_enabled = True


def disable_auto_commit() -> None:
    """Disable automatic commit functionality."""
    auto_session_manager = OaasService._get_auto_session_manager()
    auto_session_manager._auto_commit_enabled = False


def set_auto_commit_interval(seconds: float) -> None:
    """
    Set the interval for automatic commits.
    
    Args:
        seconds: Interval in seconds between auto-commits
    """
    auto_session_manager = OaasService._get_auto_session_manager()
    auto_session_manager._auto_commit_interval = seconds
    
    # Restart timer with new interval
    if auto_session_manager._auto_commit_timer:
        auto_session_manager._auto_commit_timer.cancel()
        auto_session_manager._start_auto_commit_timer()