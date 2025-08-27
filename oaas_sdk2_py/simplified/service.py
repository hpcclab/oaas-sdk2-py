"""
OaaS SDK Service Registry

This module provides the main service registry and decorator system
for the OaaS SDK simplified interface.
"""

import asyncio
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Type, Union, TYPE_CHECKING

from .config import OaasConfig
from .decorators import EnhancedFunctionDecorator, ConstructorDecorator, EnhancedMethodDecorator
from .accessors import collect_accessor_members, build_accessor_wrapper, AccessorKind
from .errors import DecoratorError, ServerError, AgentError, get_debug_context, DebugLevel
from .performance import PerformanceMetrics, get_performance_metrics, reset_performance_metrics
from .session_manager import AutoSessionManager, LegacySessionAdapter

if TYPE_CHECKING:
    from ..engine import Oparaca
    from ..session import Session
    from .objects import OaasObject


class OaasService:
    """
    Enhanced global service registry and decorator system.
    
    This class provides the main decorators and utilities for the simplified
    interface while maintaining full compatibility with the existing system.
    """
    
    _global_oaas: Optional['Oparaca'] = None
    _global_config: Optional[OaasConfig] = None
    _auto_session_manager: Optional[AutoSessionManager] = None
    _registered_services: Dict[str, Type['OaasObject']] = {}
    _service_metrics: Dict[str, PerformanceMetrics] = {}
    
    # Server state tracking
    _server_running: bool = False
    _server_port: Optional[int] = None
    _server_loop: Optional[Any] = None
    
    # Agent state tracking
    _running_agents: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def _get_global_oaas() -> 'Oparaca':
        """Get or create the global Oparaca instance."""
        if OaasService._global_oaas is None:
            config = OaasService._global_config
            if config is None:
                config = OaasConfig()
                OaasService._global_config = config
            
            # Create Oparaca instance with config
            from ..engine import Oparaca
            OaasService._global_oaas = Oparaca(
                default_pkg="default",
                config=config,  # OaasConfig can be used directly now
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
            # Set the auto session manager on the Oparaca instance for handler integration
            global_oaas._auto_session_manager = OaasService._auto_session_manager
        
        return OaasService._auto_session_manager
    
    @staticmethod
    def print_pkg() -> str:
        repo = OaasService._global_oaas.meta_repo
        return repo.print_pkg()

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
        def decorator(cls: Type['OaasObject']) -> Type['OaasObject']:
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
                
                # Process methods, functions, and constructors marked with @oaas decorators
                enhanced_methods = {}
                enhanced_functions = {}
                enhanced_constructors = {}
                
                for attr_name in dir(cls):
                    if not attr_name.startswith('_'):
                        attr = getattr(cls, attr_name)
                        if callable(attr):
                            # Process methods marked with @oaas.method
                            if hasattr(attr, '_oaas_method'):
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
                            
                            # Process functions marked with @oaas.function
                            elif hasattr(attr, '_oaas_function'):
                                try:
                                    # Get enhanced function configuration
                                    function_config = getattr(attr, '_oaas_function_config', {})
                                    
                                    # Apply the legacy func decorator with stateless configuration
                                    decorated_function = cls_meta.func(
                                        name=function_config.get('name', attr_name),
                                        stateless=True,  # Functions are always stateless
                                        serve_with_agent=function_config.get('serve_with_agent', False)
                                    )(attr)
                                    
                                    # Replace the function on the class
                                    setattr(cls, attr_name, decorated_function)
                                    enhanced_functions[attr_name] = function_config
                                    
                                    debug_ctx.log(DebugLevel.DEBUG, f"Enhanced function {attr_name} registered")
                                    
                                except Exception as e:
                                    debug_ctx.log(DebugLevel.ERROR, f"Failed to process function {attr_name}: {e}")
                                    raise DecoratorError(
                                        f"Failed to process function {attr_name} in service {name}",
                                        error_code="FUNCTION_PROCESSING_ERROR",
                                        details={
                                            'service_name': name,
                                            'function_name': attr_name,
                                            'error': str(e)
                                        }
                                    ) from e
                            
                            # Process constructors marked with @oaas.constructor
                            elif hasattr(attr, '_oaas_constructor'):
                                try:
                                    # Get enhanced constructor configuration
                                    constructor_config = getattr(attr, '_oaas_constructor_config', {})
                                    
                                    # Apply the legacy func decorator for constructor
                                    decorated_constructor = cls_meta.func(
                                        name=constructor_config.get('name', attr_name),
                                        stateless=False,  # Constructors work with object state
                                        serve_with_agent=False  # Constructors don't serve with agent
                                    )(attr)
                                    
                                    # Replace the constructor on the class
                                    setattr(cls, attr_name, decorated_constructor)
                                    enhanced_constructors[attr_name] = constructor_config
                                    
                                    debug_ctx.log(DebugLevel.DEBUG, f"Enhanced constructor {attr_name} registered")
                                    
                                except Exception as e:
                                    debug_ctx.log(DebugLevel.ERROR, f"Failed to process constructor {attr_name}: {e}")
                                    raise DecoratorError(
                                        f"Failed to process constructor {attr_name} in service {name}",
                                        error_code="CONSTRUCTOR_PROCESSING_ERROR",
                                        details={
                                            'service_name': name,
                                            'constructor_name': attr_name,
                                            'error': str(e)
                                        }
                                    ) from e
                
                # Build accessor wrappers but don't register them as functions
                accessor_configs = collect_accessor_members(cls)
                accessor_specs = {}
                for m_name, cfg in accessor_configs.items():
                    try:
                        original = getattr(cls, m_name)
                        wrapper, spec = build_accessor_wrapper(cls, m_name, original, cfg)
                        # Replace the method with the wrapper but don't register as function
                        setattr(cls, m_name, wrapper)
                        accessor_specs[m_name] = spec
                    except Exception as e:
                        debug_ctx.log(DebugLevel.ERROR, f"Failed to process accessor {m_name}: {e}")
                        raise DecoratorError(
                            f"Failed to process accessor {m_name} in service {name}",
                            error_code="ACCESSOR_PROCESSING_ERROR",
                            details={
                                'service_name': name,
                                'accessor_name': m_name,
                                'error': str(e)
                            }
                        ) from e

                # Apply the legacy decorator to maintain compatibility
                decorated_cls = cls_meta(cls)
                # Attach accessor specs on class for later export/introspection
                decorated_cls._oaas_accessors = accessor_specs
                # Persist on metadata too for repo export
                try:
                    cls_meta.accessor_dict = accessor_specs
                except Exception:
                    pass
                
                # Store the class metadata for later use
                decorated_cls._oaas_cls_meta = cls_meta
                decorated_cls._oaas_enhanced_methods = enhanced_methods
                decorated_cls._oaas_enhanced_functions = enhanced_functions
                decorated_cls._oaas_enhanced_constructors = enhanced_constructors
                
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
    def function(name: str = "", serve_with_agent: bool = False,
                 timeout: Optional[float] = None, retry_count: int = 0,
                 retry_delay: float = 1.0):
        """
        Enhanced decorator for stateless functions that don't require object instances.
        
        This decorator provides stateless function capabilities with full error handling
        and integration with the auto-session management system.
        
        Args:
            name: Optional function name override
            serve_with_agent: Whether to serve with agent support
            timeout: Optional timeout in seconds for function execution
            retry_count: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
            
        Returns:
            Decorated function with enhanced OaaS capabilities
        """
        def decorator(func):
            debug_ctx = get_debug_context()
            debug_ctx.log(DebugLevel.DEBUG, f"Applying enhanced function decorator to {func.__name__}")
            
            # Create enhanced function decorator
            enhanced_decorator = EnhancedFunctionDecorator(
                name=name,
                serve_with_agent=serve_with_agent,
                timeout=timeout,
                retry_count=retry_count,
                retry_delay=retry_delay
            )
            
            # Apply the enhanced decorator
            return enhanced_decorator(func)
        
        return decorator
    
    @staticmethod
    def constructor(validate: bool = True, timeout: Optional[float] = None,
                    error_handling: str = "strict"):
        """
        Enhanced decorator for custom object initialization logic.
        
        This decorator provides custom initialization capabilities that integrate
        seamlessly with the create() pattern and auto-session management.
        
        Args:
            validate: Whether to validate initialization parameters
            timeout: Optional timeout in seconds for constructor execution
            error_handling: Error handling strategy ("strict" or "lenient")
            
        Returns:
            Decorated constructor with enhanced OaaS capabilities
        """
        def decorator(func):
            debug_ctx = get_debug_context()
            debug_ctx.log(DebugLevel.DEBUG, f"Applying constructor decorator to {func.__name__}")
            
            # Create constructor decorator
            constructor_decorator = ConstructorDecorator(
                validate=validate,
                timeout=timeout,
                error_handling=error_handling
            )
            
            # Apply the constructor decorator
            return constructor_decorator(func)
        
        return decorator
    
    @staticmethod
    def get_service(name: str, package: str = "default") -> Optional[Type['OaasObject']]:
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
    def list_services() -> Dict[str, Type['OaasObject']]:
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
            'enhanced_functions': getattr(service_cls, '_oaas_enhanced_functions', {}),
            'enhanced_constructors': getattr(service_cls, '_oaas_enhanced_constructors', {}),
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
            
            # Check enhanced functions
            enhanced_functions = getattr(service_cls, '_oaas_enhanced_functions', {})
            if enhanced_functions:
                validation_results['info'].append(f"Service has {len(enhanced_functions)} enhanced functions")
            
            # Check enhanced constructors
            enhanced_constructors = getattr(service_cls, '_oaas_enhanced_constructors', {})
            if enhanced_constructors:
                validation_results['info'].append(f"Service has {len(enhanced_constructors)} enhanced constructors")
            
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

    # =============================================================================
    # SERVER MANAGEMENT
    # =============================================================================

    @staticmethod
    def start_server(port: int = 8080, loop: Any = None, async_mode: bool = None) -> None:
        """
        Start gRPC server to host all registered service definitions for external access.
        
        IMPORTANT: The server provides gRPC endpoints for external clients to call 
        service methods. It operates independently of agents - clients can call 
        regular methods through the server even if no agents are running.
        
        Args:
            port: Port to bind server to (default: 8080)
            loop: Event loop for async mode (auto-detected if None)
            async_mode: Override global async mode setting
            
        Raises:
            ServerError: If server already running or start fails
            
        Note:
            - Server hosts ALL registered @oaas.service classes
            - Provides gRPC API for external client access
            - Independent of agents - can run without any agents
            - Handles regular method calls (not serve_with_agent=True methods)
        """
        if OaasService._server_running:
            raise ServerError("gRPC server is already running")
        
        debug_ctx = get_debug_context()
        debug_ctx.log(DebugLevel.INFO, f"Starting gRPC server on port {port}")
        
        try:
            global_oaas = OaasService._get_global_oaas()
            if async_mode is not None:
                global_oaas.async_mode = async_mode
            
            global_oaas.start_grpc_server(loop=loop, port=port)
            
            OaasService._server_port = port
            OaasService._server_loop = loop
            OaasService._server_running = True
            
            debug_ctx.log(DebugLevel.INFO, f"gRPC server started on port {port}")
            
        except Exception as e:
            raise ServerError(f"Failed to start gRPC server: {e}") from e

    @staticmethod
    def stop_server() -> None:
        """
        Stop gRPC server and clean up resources.
        
        Raises:
            ServerError: If server not running or stop fails
        """
        if not OaasService._server_running:
            raise ServerError("gRPC server is not running")
        
        debug_ctx = get_debug_context()
        debug_ctx.log(DebugLevel.INFO, "Stopping gRPC server")
        
        try:
            global_oaas = OaasService._get_global_oaas()
            global_oaas.stop_server()
            
            OaasService._server_port = None
            OaasService._server_loop = None
            OaasService._server_running = False
            
            debug_ctx.log(DebugLevel.INFO, "gRPC server stopped")
            
        except Exception as e:
            raise ServerError(f"Failed to stop gRPC server: {e}") from e

    @staticmethod
    def is_server_running() -> bool:
        """Check if gRPC server is currently running."""
        return OaasService._server_running

    @staticmethod
    def get_server_info() -> Dict[str, Any]:
        """Get comprehensive server status and configuration."""
        return {
            'running': OaasService._server_running,
            'port': OaasService._server_port,
            'async_mode': OaasService._global_oaas.async_mode if OaasService._global_oaas else None,
            'mock_mode': OaasService._global_config.mock_mode if OaasService._global_config else None,
            'registered_services': len(OaasService._registered_services)
        }

    @staticmethod
    def restart_server(port: int = None, loop: Any = None, async_mode: bool = None) -> None:
        """Restart server with new configuration."""
        if OaasService._server_running:
            OaasService.stop_server()
        
        final_port = port or OaasService._server_port or 8080
        OaasService.start_server(port=final_port, loop=loop, async_mode=async_mode)

    # =============================================================================
    # AGENT MANAGEMENT
    # =============================================================================

    @staticmethod
    async def start_agent(service_class: Type['OaasObject'], obj_id: int = None, 
                         partition_id: int = None, loop: Any = None) -> str:
        """
        Start agent for specific object instance to handle serve_with_agent=True methods.
        
        IMPORTANT: Agents operate independently of gRPC servers. An agent listens on 
        message queue keys for specific object method invocations and can run without 
        a server being active.
        
        Args:
            service_class: Service class decorated with @oaas.service
            obj_id: Specific object ID (default: 1 if None)
            partition_id: Partition ID (uses default if None)
            loop: Event loop (auto-detected if None)
            
        Returns:
            Agent ID for tracking/stopping (format: "package.service_name:obj_id")
            
        Raises:
            AgentError: If agent start fails or service invalid
            
        Note:
            - Agents handle only methods marked with serve_with_agent=True
            - Each agent serves ONE specific object instance
            - Multiple agents can run for different object instances of same service
            - Agents use message queue communication, not gRPC
        """
        if not hasattr(service_class, '_oaas_cls_meta'):
            raise AgentError(f"Service class {service_class.__name__} not registered with @oaas.service")
        
        # Generate unique agent ID
        agent_id = f"{service_class._oaas_package}.{service_class._oaas_service_name}"
        if obj_id is not None:
            agent_id += f":{obj_id}"
        
        if agent_id in OaasService._running_agents:
            raise AgentError(f"Agent {agent_id} is already running")
        
        debug_ctx = get_debug_context()
        debug_ctx.log(DebugLevel.INFO, f"Starting agent {agent_id}")
        
        try:
            global_oaas = OaasService._get_global_oaas()
            cls_meta = service_class._oaas_cls_meta
            
            # Use default partition if not specified
            if partition_id is None:
                partition_id = global_oaas.default_partition_id
            
            # Use default object ID if not specified
            if obj_id is None:
                obj_id = 1  # Default object ID for class-level agents
            
            # Start the agent
            await global_oaas.run_agent(
                loop=loop or asyncio.get_event_loop(),
                cls_meta=cls_meta,
                obj_id=obj_id,
                parition_id=partition_id  # Note: keeping original typo for compatibility
            )
            
            # Track agent state
            OaasService._running_agents[agent_id] = {
                'service_class': service_class,
                'obj_id': obj_id,
                'partition_id': partition_id,
                'loop': loop,
                'started_at': datetime.now()
            }
            
            debug_ctx.log(DebugLevel.INFO, f"Agent {agent_id} started successfully")
            return agent_id
            
        except Exception as e:
            raise AgentError(f"Failed to start agent {agent_id}: {e}") from e

    @staticmethod
    async def stop_agent(agent_id: str = None, service_class: Type['OaasObject'] = None, 
                        obj_id: int = None) -> None:
        """
        Stop agent by ID or service class/object.
        
        Args:
            agent_id: Specific agent ID to stop
            service_class: Service class (alternative to agent_id)
            obj_id: Object ID (used with service_class)
            
        Raises:
            AgentError: If agent not found or stop fails
        """
        # Resolve agent ID if not provided
        if agent_id is None:
            if service_class is None:
                raise AgentError("Either agent_id or service_class must be provided")
            
            agent_id = f"{service_class._oaas_package}.{service_class._oaas_service_name}"
            if obj_id is not None:
                agent_id += f":{obj_id}"
        
        if agent_id not in OaasService._running_agents:
            raise AgentError(f"Agent {agent_id} is not running")
        
        debug_ctx = get_debug_context()
        debug_ctx.log(DebugLevel.INFO, f"Stopping agent {agent_id}")
        
        try:
            agent_info = OaasService._running_agents[agent_id]
            global_oaas = OaasService._get_global_oaas()
            
            # Stop the agent
            await global_oaas.stop_agent(
                cls_meta=agent_info['service_class']._oaas_cls_meta,
                obj_id=agent_info['obj_id'],
                partition_id=agent_info['partition_id']
            )
            
            # Remove from tracking
            del OaasService._running_agents[agent_id]
            
            debug_ctx.log(DebugLevel.INFO, f"Agent {agent_id} stopped successfully")
            
        except Exception as e:
            raise AgentError(f"Failed to stop agent {agent_id}: {e}") from e

    @staticmethod
    def list_agents() -> Dict[str, Dict[str, Any]]:
        """List all running agents with their information."""
        return {
            agent_id: {
                'service_name': info['service_class']._oaas_service_name,
                'package': info['service_class']._oaas_package,
                'obj_id': info['obj_id'],
                'partition_id': info['partition_id'],
                'started_at': info['started_at'].isoformat(),
                'running_duration': str(datetime.now() - info['started_at'])
            }
            for agent_id, info in OaasService._running_agents.items()
        }

    @staticmethod
    async def stop_all_agents() -> None:
        """Stop all running agents."""
        agent_ids = list(OaasService._running_agents.keys())
        for agent_id in agent_ids:
            try:
                await OaasService.stop_agent(agent_id)
            except Exception as e:
                debug_ctx = get_debug_context()
                debug_ctx.log(DebugLevel.ERROR, f"Error stopping agent {agent_id}: {e}")
    

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


def get_global_oaas() -> 'Oparaca':
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


# Convenience functions for backward compatibility
def create_object(cls: Type['OaasObject'], obj_id: Optional[int] = None, local: bool = False) -> 'OaasObject':
    """Create an object instance (convenience function)."""
    return cls.create(obj_id=obj_id, local=local)


def load_object(cls: Type['OaasObject'], obj_id: int) -> 'OaasObject':
    """Load an object instance (convenience function)."""
    return cls.load(obj_id=obj_id)


# Global instance for convenient access
oaas = OaasService()
