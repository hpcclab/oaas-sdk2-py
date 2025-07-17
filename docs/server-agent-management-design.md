# Server and Agent Management Integration Design

## Overview

This document specifies the design for integrating gRPC server and agent management functionality into the new simplified OaaS API. The design maintains full backward compatibility while providing a more intuitive and type-safe interface.

## Current State Analysis

### Existing Server Management in [`Oparaca`](../oaas_sdk2_py/engine.py)

- **`start_grpc_server(loop=None, port=8080)`** - Starts gRPC server with async/sync mode detection
- **`stop_server()`** - Stops the server via `engine.stop_server()`
- **Mode Detection**: Uses `self.async_mode` to choose `AsyncInvocationHandler` vs `SyncInvocationHandler`

### Existing Agent Management in [`Oparaca`](../oaas_sdk2_py/engine.py)

- **`run_agent(loop, cls_meta, obj_id, partition_id)`** - Starts agent for specific service/object
- **`stop_agent(cls_meta, obj_id, partition_id)`** - Stops agent for specific service/object
- **Method Detection**: Iterates through `cls_meta.func_dict` to find methods with `serve_with_agent=True`
- **Key Generation**: Creates different keys for stateless vs stateful functions

## Design Goals

1. **Simplicity**: Reduce boilerplate and complexity
2. **Consistency**: Align with new API patterns using `@oaas.service` decorators
3. **Backward Compatibility**: Maintain existing functionality
4. **Type Safety**: Leverage Python type hints
5. **Error Handling**: Comprehensive error management
6. **Independence**: Servers and agents operate independently - agents can run without servers

## Architecture Clarification

### Server vs Agent Distinction

**Server (`start_grpc_server`)**:
- Hosts the entire service definitions/classes
- Provides gRPC endpoint for external client access
- Handles incoming requests for all registered services
- Uses `InvocationHandler` to route requests

**Agent (`run_agent`)**:
- Hosts specific object instances with `serve_with_agent=True` methods
- Listens on specific message queue keys for function invocations
- Handles method calls for specific object instances
- **Can run independently** - no server required
- Uses `serve_function` for specific method/object combinations

### Independence Model
```
┌─────────────────┐    ┌─────────────────┐
│   gRPC Server   │    │      Agent      │
│                 │    │                 │
│ • All services  │    │ • Specific obj  │
│ • External API  │    │ • Method calls  │
│ • Routing       │    │ • Independent   │
└─────────────────┘    └─────────────────┘
        │                       │
        └───────────────────────┘
              Can operate separately
```

## Server Management API Integration

Add server management methods to [`OaasService`](../oaas_sdk2_py/simplified.py):

```python
class OaasService:
    # Server state tracking
    _server_running: bool = False
    _server_port: Optional[int] = None
    _server_loop: Optional[Any] = None

    @staticmethod
    def start_server(port: int = 8080, loop: Any = None, async_mode: bool = None) -> None:
        """
        Start gRPC server with simplified configuration.
        
        Args:
            port: Port to bind server to (default: 8080)
            loop: Event loop for async mode (auto-detected if None)
            async_mode: Override global async mode setting
            
        Raises:
            ServerError: If server already running or start fails
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
```

## Agent Management API Integration

```python
class OaasService:
    # Agent state tracking
    _running_agents: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    async def start_agent(service_class: Type[OaasObject], obj_id: int = None, 
                         partition_id: int = None, loop: Any = None) -> str:
        """
        Start agent for service class or specific object instance.
        
        Args:
            service_class: Service class decorated with @oaas.service
            obj_id: Specific object ID (if None, serves all instances)
            partition_id: Partition ID (uses default if None)
            loop: Event loop (auto-detected if None)
            
        Returns:
            Agent ID for tracking/stopping
            
        Raises:
            AgentError: If agent start fails or service invalid
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
    async def stop_agent(agent_id: str = None, service_class: Type[OaasObject] = None, 
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
```

## Error Handling Classes

```python
class ServerError(OaasError):
    """Raised when server operations fail."""
    pass

class AgentError(OaasError):
    """Raised when agent operations fail."""
    pass
```

## Enhanced OaasObject Integration

```python
class OaasObject(BaseObject):
    @classmethod
    async def start_agent(cls, obj_id: int = None, partition_id: int = None, 
                         loop: Any = None) -> str:
        """
        Start agent for this service class.
        
        Convenience method that delegates to OaasService.start_agent.
        """
        return await OaasService.start_agent(cls, obj_id, partition_id, loop)

    @classmethod
    async def stop_agent(cls, obj_id: int = None) -> None:
        """
        Stop agent for this service class.
        
        Convenience method that delegates to OaasService.stop_agent.
        """
        await OaasService.stop_agent(service_class=cls, obj_id=obj_id)

    async def start_instance_agent(self, loop: Any = None) -> str:
        """Start agent for this specific object instance."""
        return await OaasService.start_agent(
            service_class=self.__class__,
            obj_id=self.object_id,
            loop=loop
        )

    async def stop_instance_agent(self) -> None:
        """Stop agent for this specific object instance."""
        await OaasService.stop_agent(
            service_class=self.__class__,
            obj_id=self.object_id
        )
```

## Usage Examples

### Server-Only Mode (External gRPC Access)

```python
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig

# Configure and start server only
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)

@oaas.service("Calculator", package="math")
class Calculator(OaasObject):
    result: float = 0.0
    
    @oaas.method()  # Regular method - served by gRPC server
    async def add(self, value: float) -> float:
        self.result += value
        return self.result
    
    @oaas.method(serve_with_agent=True)  # Agent method - requires agent
    async def complex_calculation(self, data: list) -> float:
        # This method can only be called if an agent is running
        return sum(data) * self.result

# Start gRPC server (no agents needed for regular methods)
oaas.start_server(port=8080)

# External clients can now call Calculator.add() via gRPC
# But Calculator.complex_calculation() requires an agent to be running

print(f"Server running: {oaas.is_server_running()}")
print(f"Server info: {oaas.get_server_info()}")
```

### Agent-Only Mode (No External Access)

```python
# Don't start server - only run agents for background processing

@oaas.service("BackgroundProcessor", package="worker")
class BackgroundProcessor(OaasObject):
    @oaas.method(serve_with_agent=True)
    async def process_data(self, data: dict) -> dict:
        # Heavy background processing
        await asyncio.sleep(5)  # Simulate work
        return {"processed": True, "result": data}

# Start agent only - no gRPC server needed
agent_id = await oaas.start_agent(BackgroundProcessor, obj_id=123)

# This agent now listens for process_data() calls via message queue
# Other services can invoke this via internal message passing

print(f"Agent running: {agent_id}")
print(f"No server needed: {not oaas.is_server_running()}")
```

### Combined Mode (Server + Agents)

```python
@oaas.service("HybridService", package="hybrid")
class HybridService(OaasObject):
    @oaas.method()  # Served by gRPC server
    async def quick_info(self) -> str:
        return "This is served by the server"
    
    @oaas.method(serve_with_agent=True)  # Served by agent
    async def heavy_work(self, data: list) -> dict:
        return {"processed_count": len(data)}

# Start both server and agent
oaas.start_server(port=8080)
agent_id = await oaas.start_agent(HybridService, obj_id=456)

# Now:
# - External clients can call quick_info() via gRPC
# - Internal/external systems can call heavy_work() via message queue
# - They operate completely independently
```

### Independence Demonstration

```python
# Scenario 1: Agent without server
await oaas.start_agent(BackgroundProcessor, obj_id=1)
# Agent runs and processes messages - no server needed

# Scenario 2: Server without agents  
oaas.start_server(port=8080)
# External clients can call regular methods - no agents needed

# Scenario 3: Multiple agents, no server
agent1 = await oaas.start_agent(Worker, obj_id=1)
agent2 = await oaas.start_agent(Worker, obj_id=2) 
agent3 = await oaas.start_agent(Calculator, obj_id=100)
# All agents run independently, handling different object instances
```

## Backward Compatibility

```python
# Add convenience function for backward compatibility
def get_global_oaas() -> Oparaca:
    """Get global Oparaca instance for direct server/agent access."""
    return OaasService._get_global_oaas()

# Existing code continues to work
oparaca = get_global_oaas()
oparaca.start_grpc_server(port=8080)
await oparaca.run_agent(loop, cls_meta, obj_id)
```

## Integration Points

1. **Server lifecycle tied to OaasService lifecycle**
2. **Agent management integrated with service registry**
3. **Enhanced error handling and debugging**
4. **Performance monitoring for server/agent operations**
5. **Thread-safe operation with existing AutoSessionManager**

## Migration from Current API

### Before (Current API)
```python
from oaas_sdk2_py.engine import Oparaca
from oaas_sdk2_py.config import OaasConfig

config = OaasConfig()
oparaca = Oparaca(config=config, async_mode=True)

# Start server (hosts all service definitions)
oparaca.start_grpc_server(port=8080)

# Start agent (hosts specific object instance methods)
import asyncio
loop = asyncio.get_event_loop()
await oparaca.run_agent(loop, cls_meta, obj_id=123)

# Stop agent
await oparaca.stop_agent(cls_meta, obj_id=123)

# Stop server
oparaca.stop_server()
```

### After (New API)
```python
from oaas_sdk2_py.simplified import oaas, OaasConfig

config = OaasConfig(async_mode=True)
oaas.configure(config)

# Start server (hosts all service definitions for gRPC access)
oaas.start_server(port=8080)

# Start agent (hosts specific object instance for serve_with_agent methods)
agent_id = await oaas.start_agent(MyService, obj_id=123)

# Stop agent
await oaas.stop_agent(agent_id)

# Stop server
oaas.stop_server()
```

### Key Improvements

1. **Clearer Separation**: Explicit distinction between server (gRPC endpoint) and agent (object instance processor)
2. **Independence**: Can run agents without servers, or servers without agents
3. **Better Tracking**: Agent IDs for easier management
4. **Type Safety**: Strongly typed service classes instead of raw metadata
5. **Simplified API**: No need to manage event loops or metadata manually

## Implementation Priority

1. **Phase 1**: Server management integration
2. **Phase 2**: Agent management integration  
3. **Phase 3**: Enhanced OaasObject methods
4. **Phase 4**: Comprehensive testing and documentation

This design provides a **simplified, type-safe, and feature-rich API** for server and agent management while maintaining full backward compatibility and integrating seamlessly with the existing OaaS SDK architecture.