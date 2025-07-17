"""
OaaS SDK Enhanced Decorators

This module provides enhanced decorators for the OaaS SDK
simplified interface with comprehensive error handling.
"""

import asyncio
import time
from functools import wraps
from typing import Optional

from .errors import DecoratorError, get_debug_context, DebugLevel
from .performance import PerformanceMetrics


class EnhancedFunctionDecorator:
    """
    Enhanced function decorator for stateless functions that don't require object instances.
    
    This decorator provides stateless function capabilities with full error handling
    and integration with the auto-session management system.
    """
    
    def __init__(self, name: str = "", serve_with_agent: bool = False,
                 timeout: Optional[float] = None, retry_count: int = 0,
                 retry_delay: float = 1.0):
        self.name = name
        self.serve_with_agent = serve_with_agent
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.metrics = PerformanceMetrics()
        
    def __call__(self, func):
        """Apply the enhanced function decorator"""
        debug_ctx = get_debug_context()
        
        # Store original function info
        func_name = self.name if self.name else func.__name__
        
        # Create enhanced wrapper with full error handling
        if asyncio.iscoroutinefunction(func):
            enhanced_func = self._create_async_enhanced_wrapper(func, func_name)
        else:
            enhanced_func = self._create_sync_enhanced_wrapper(func, func_name)
        
        # Mark for OaaS processing
        enhanced_func._oaas_function = True
        enhanced_func._oaas_function_config = {
            'name': func_name,
            'stateless': True,  # Functions are always stateless
            'serve_with_agent': self.serve_with_agent,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay
        }
        
        debug_ctx.log(DebugLevel.DEBUG, f"Enhanced function decorator applied to {func_name}")
        return enhanced_func
    
    def _create_async_enhanced_wrapper(self, func, func_name):
        """Create enhanced async wrapper for stateless functions"""
        @wraps(func)
        async def enhanced_async_wrapper(*args, **kwargs):
            debug_ctx = get_debug_context()
            start_time = time.time()
            
            try:
                # Performance monitoring
                if debug_ctx.performance_monitoring:
                    debug_ctx.log(DebugLevel.DEBUG, f"Starting async function {func_name}")
                
                # Get session for stateless function execution
                from .service import OaasService
                auto_session_manager = OaasService._get_auto_session_manager()
                auto_session_manager.get_session()
                
                # Apply retry logic
                last_exception = None
                for attempt in range(self.retry_count + 1):
                    try:
                        # Apply timeout if specified
                        if self.timeout:
                            result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)
                        else:
                            result = await func(*args, **kwargs)
                        
                        # Record successful call
                        if debug_ctx.performance_monitoring:
                            duration = time.time() - start_time
                            self.metrics.record_call(duration, success=True)
                            debug_ctx.log(DebugLevel.DEBUG, f"Async function {func_name} completed in {duration:.4f}s")
                        
                        return result
                        
                    except asyncio.TimeoutError as e:
                        last_exception = e
                        debug_ctx.log(DebugLevel.WARNING, f"Timeout in async function {func_name}, attempt {attempt + 1}")
                        
                        if attempt < self.retry_count:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        break
                        
                    except Exception as e:
                        last_exception = e
                        debug_ctx.log(DebugLevel.WARNING, f"Error in async function {func_name}, attempt {attempt + 1}: {e}")
                        
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
                    f"Function {func_name} failed after {self.retry_count + 1} attempts",
                    error_code="FUNCTION_EXECUTION_ERROR",
                    details={
                        'function_name': func_name,
                        'attempts': self.retry_count + 1,
                        'last_error': str(last_exception)
                    }
                ) from last_exception
                
            except Exception as e:
                # Record failed call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=False)
                
                debug_ctx.log(DebugLevel.ERROR, f"Unhandled error in async function {func_name}: {e}")
                raise
        
        return enhanced_async_wrapper
    
    def _create_sync_enhanced_wrapper(self, func, func_name):
        """Create enhanced sync wrapper for stateless functions"""
        @wraps(func)
        def enhanced_sync_wrapper(*args, **kwargs):
            debug_ctx = get_debug_context()
            start_time = time.time()
            
            try:
                # Performance monitoring
                if debug_ctx.performance_monitoring:
                    debug_ctx.log(DebugLevel.DEBUG, f"Starting sync function {func_name}")
                
                # Get session for stateless function execution
                from .service import OaasService
                auto_session_manager = OaasService._get_auto_session_manager()
                auto_session_manager.get_session()
                
                # Apply retry logic
                last_exception = None
                for attempt in range(self.retry_count + 1):
                    try:
                        result = func(*args, **kwargs)
                        
                        # Record successful call
                        if debug_ctx.performance_monitoring:
                            duration = time.time() - start_time
                            self.metrics.record_call(duration, success=True)
                            debug_ctx.log(DebugLevel.DEBUG, f"Sync function {func_name} completed in {duration:.4f}s")
                        
                        return result
                        
                    except Exception as e:
                        last_exception = e
                        debug_ctx.log(DebugLevel.WARNING, f"Error in sync function {func_name}, attempt {attempt + 1}: {e}")
                        
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
                    f"Function {func_name} failed after {self.retry_count + 1} attempts",
                    error_code="FUNCTION_EXECUTION_ERROR",
                    details={
                        'function_name': func_name,
                        'attempts': self.retry_count + 1,
                        'last_error': str(last_exception)
                    }
                ) from last_exception
                
            except Exception as e:
                # Record failed call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=False)
                
                debug_ctx.log(DebugLevel.ERROR, f"Unhandled error in sync function {func_name}: {e}")
                raise
        
        return enhanced_sync_wrapper
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics for this function decorator."""
        return self.metrics
    
    def reset_performance_metrics(self):
        """Reset performance metrics for this function decorator."""
        self.metrics = PerformanceMetrics()


class ConstructorDecorator:
    """
    Constructor decorator for custom object initialization logic.
    
    This decorator provides custom initialization capabilities that integrate
    seamlessly with the create() pattern and auto-session management.
    """
    
    def __init__(self, validate: bool = True, timeout: Optional[float] = None,
                 error_handling: str = "strict"):
        self.validate = validate
        self.timeout = timeout
        self.error_handling = error_handling
        self.metrics = PerformanceMetrics()
        
    def __call__(self, func):
        """Apply the constructor decorator"""
        debug_ctx = get_debug_context()
        
        # Store original function info
        func_name = func.__name__
        
        # Create enhanced wrapper with full error handling
        if asyncio.iscoroutinefunction(func):
            enhanced_func = self._create_async_enhanced_wrapper(func, func_name)
        else:
            enhanced_func = self._create_sync_enhanced_wrapper(func, func_name)
        
        # Mark for OaaS processing
        enhanced_func._oaas_constructor = True
        enhanced_func._oaas_constructor_config = {
            'name': func_name,
            'validate': self.validate,
            'timeout': self.timeout,
            'error_handling': self.error_handling
        }
        
        debug_ctx.log(DebugLevel.DEBUG, f"Constructor decorator applied to {func_name}")
        return enhanced_func
    
    def _create_async_enhanced_wrapper(self, func, func_name):
        """Create enhanced async wrapper for constructor"""
        @wraps(func)
        async def enhanced_async_wrapper(obj_self, *args, **kwargs):
            debug_ctx = get_debug_context()
            start_time = time.time()
            
            try:
                # Performance monitoring
                if debug_ctx.performance_monitoring:
                    debug_ctx.log(DebugLevel.DEBUG, f"Starting async constructor {func_name}")
                
                # Apply timeout if specified
                if self.timeout:
                    result = await asyncio.wait_for(func(obj_self, *args, **kwargs), timeout=self.timeout)
                else:
                    result = await func(obj_self, *args, **kwargs)
                
                # Record successful call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=True)
                    debug_ctx.log(DebugLevel.DEBUG, f"Async constructor {func_name} completed in {duration:.4f}s")
                
                return result
                
            except Exception as e:
                # Record failed call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=False)
                
                debug_ctx.log(DebugLevel.ERROR, f"Error in async constructor {func_name}: {e}")
                
                # Handle constructor errors based on error_handling setting
                if self.error_handling == "strict":
                    raise DecoratorError(
                        f"Constructor {func_name} failed during object initialization",
                        error_code="CONSTRUCTOR_ERROR",
                        details={
                            'constructor_name': func_name,
                            'error': str(e),
                            'object_id': getattr(obj_self, 'object_id', 'unknown')
                        }
                    ) from e
                else:
                    # Log error but allow object creation to continue
                    debug_ctx.log(DebugLevel.WARNING, f"Constructor {func_name} failed but continuing: {e}")
                    return None
        
        return enhanced_async_wrapper
    
    def _create_sync_enhanced_wrapper(self, func, func_name):
        """Create enhanced sync wrapper for constructor"""
        @wraps(func)
        def enhanced_sync_wrapper(obj_self, *args, **kwargs):
            debug_ctx = get_debug_context()
            start_time = time.time()
            
            try:
                # Performance monitoring
                if debug_ctx.performance_monitoring:
                    debug_ctx.log(DebugLevel.DEBUG, f"Starting sync constructor {func_name}")
                
                result = func(obj_self, *args, **kwargs)
                
                # Record successful call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=True)
                    debug_ctx.log(DebugLevel.DEBUG, f"Sync constructor {func_name} completed in {duration:.4f}s")
                
                return result
                
            except Exception as e:
                # Record failed call
                if debug_ctx.performance_monitoring:
                    duration = time.time() - start_time
                    self.metrics.record_call(duration, success=False)
                
                debug_ctx.log(DebugLevel.ERROR, f"Error in sync constructor {func_name}: {e}")
                
                # Handle constructor errors based on error_handling setting
                if self.error_handling == "strict":
                    raise DecoratorError(
                        f"Constructor {func_name} failed during object initialization",
                        error_code="CONSTRUCTOR_ERROR",
                        details={
                            'constructor_name': func_name,
                            'error': str(e),
                            'object_id': getattr(obj_self, 'object_id', 'unknown')
                        }
                    ) from e
                else:
                    # Log error but allow object creation to continue
                    debug_ctx.log(DebugLevel.WARNING, f"Constructor {func_name} failed but continuing: {e}")
                    return None
        
        return enhanced_sync_wrapper
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics for this constructor decorator."""
        return self.metrics
    
    def reset_performance_metrics(self):
        """Reset performance metrics for this constructor decorator."""
        self.metrics = PerformanceMetrics()


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
