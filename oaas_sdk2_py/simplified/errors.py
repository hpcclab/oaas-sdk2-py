"""
OaaS SDK Error Handling and Debugging Support

This module provides comprehensive error handling and debugging capabilities
for the OaaS SDK simplified interface.
"""

import json
import logging
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict

# =============================================================================
# ERROR HANDLING AND DEBUGGING SUPPORT
# =============================================================================

# Register a TRACE level for stdlib logging (lower than DEBUG)
TRACE_LEVEL_NUM = 5
if not hasattr(logging, "TRACE"):
    logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
    logging.TRACE = TRACE_LEVEL_NUM  # type: ignore[attr-defined]

    def trace(self: logging.Logger, msg, *args, **kwargs):  # pragma: no cover - thin shim
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            self._log(TRACE_LEVEL_NUM, msg, args, **kwargs)

    logging.Logger.trace = trace  # type: ignore[attr-defined]

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


class PerformanceError(OaasError):
    """Raised when there are performance-related errors."""
    pass


class SessionError(OaasError):
    """Raised when session operations fail."""
    pass


class DecoratorError(OaasError):
    """Raised when decorator operations fail."""
    pass


class ServerError(OaasError):
    """Raised when server operations fail."""
    pass


class AgentError(OaasError):
    """Raised when agent operations fail."""
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
        # Library best practice: don't configure root or attach stream handlers.
        if not self.logger.handlers:
            self.logger.addHandler(logging.NullHandler())
        # Allow application/root to handle emissions
        self.logger.propagate = True
        self.logger.setLevel(self._map_to_logging_level(self.level))
    
    def _map_to_logging_level(self, level: DebugLevel) -> int:
        """Convert DebugLevel to stdlib logging level"""
        mapping = {
            DebugLevel.NONE: logging.CRITICAL + 1,  # effectively disables
            DebugLevel.ERROR: logging.ERROR,
            DebugLevel.WARNING: logging.WARNING,
            DebugLevel.INFO: logging.INFO,
            DebugLevel.DEBUG: logging.DEBUG,
            DebugLevel.TRACE: getattr(logging, "TRACE", logging.DEBUG),
        }
        return mapping.get(level, logging.INFO)

    def _get_log_level(self) -> int:
        """Backward-compat shim: current context's level as stdlib logging level"""
        return self._map_to_logging_level(self.level)
    
    def log(self, level: DebugLevel, message: str, **kwargs):
        """Log a message with context"""
        if not self.enabled or level.value > self.level.value:
            return

        log_level = self._map_to_logging_level(level)
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


def set_debug_level(level: DebugLevel) -> None:
    """Set the global debug level."""
    global _debug_context
    _debug_context.level = level
    _debug_context.enabled = level != DebugLevel.NONE
    _debug_context.logger.setLevel(_debug_context._map_to_logging_level(level))
    _debug_context.logger.disabled = not _debug_context.enabled


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
    _debug_context.logger.setLevel(_debug_context._map_to_logging_level(level))
