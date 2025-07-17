"""
OaaS SDK Objects

This module provides simplified base class with automatic state management
for the OaaS SDK simplified interface.
"""

from typing import Any, Dict, Optional, get_type_hints, TYPE_CHECKING

from ..obj import BaseObject
from .state_descriptor import StateDescriptor

if TYPE_CHECKING:
    pass


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
        except Exception:
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
        # Import here to avoid circular imports
        from .service import OaasService
        
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
        # Import here to avoid circular imports
        from .service import OaasService
        
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

    # =============================================================================
    # AGENT MANAGEMENT METHODS
    # =============================================================================

    @classmethod
    async def start_agent(cls, obj_id: int = None, partition_id: int = None, 
                         loop: Any = None) -> str:
        """
        Start agent for this service class.
        
        Convenience method that delegates to OaasService.start_agent.
        """
        from .service import OaasService
        return await OaasService.start_agent(cls, obj_id, partition_id, loop)

    @classmethod
    async def stop_agent(cls, obj_id: int = None) -> None:
        """
        Stop agent for this service class.
        
        Convenience method that delegates to OaasService.stop_agent.
        """
        from .service import OaasService
        await OaasService.stop_agent(service_class=cls, obj_id=obj_id)

    async def start_instance_agent(self, loop: Any = None) -> str:
        """Start agent for this specific object instance."""
        from .service import OaasService
        return await OaasService.start_agent(
            service_class=self.__class__,
            obj_id=self.object_id,
            loop=loop
        )

    async def stop_instance_agent(self) -> None:
        """Stop agent for this specific object instance."""
        from .service import OaasService
        await OaasService.stop_agent(
            service_class=self.__class__,
            obj_id=self.object_id
        )
