"""
OaaS SDK Performance Monitoring

This module provides performance monitoring and metrics collection
for the OaaS SDK simplified interface.
"""

import asyncio
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Dict, Union

from .errors import get_debug_context, DebugLevel


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
