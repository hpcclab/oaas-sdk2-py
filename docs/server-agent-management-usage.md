# Server and Agent Management

This document describes the server and agent management functionality implemented in the OaaS SDK simplified interface.

## Overview

The OaaS SDK now provides comprehensive server and agent management capabilities through the `OaasService` class and convenient methods on `OaasObject` instances. This implementation follows the design specification to provide:

- Simplified server lifecycle management
- Automatic agent deployment and monitoring
- Type-safe error handling
- Full backward compatibility

## Server Management

### Starting a Server

```python
from oaas_sdk2_py.simplified import oaas, OaasConfig

# Configure OaaS
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)

# Start server
oaas.start_server(port=8080)
```

### Server Status and Information

```python
# Check if server is running
if oaas.is_server_running():
    print("Server is running")

# Get detailed server information
server_info = oaas.get_server_info()
print(f"Port: {server_info['port']}")
print(f"Async mode: {server_info['async_mode']}")
print(f"Mock mode: {server_info['mock_mode']}")
print(f"Registered services: {server_info['registered_services']}")
```

### Stopping and Restarting Server

```python
# Stop server
oaas.stop_server()

# Restart server with new configuration
oaas.restart_server(port=8081, async_mode=True)
```

## Agent Management

### Service Definition

Services must be decorated with `@oaas.service` and have methods marked with `serve_with_agent=True`:

```python
@oaas.service("Calculator", package="math")
class Calculator(OaasObject):
    result: int = 0
    
    @oaas.method(serve_with_agent=True)
    async def increment(self) -> int:
        self.result += 1
        return self.result
    
    @oaas.method(serve_with_agent=True)
    async def get_result(self) -> int:
        return self.result
```

### Starting Agents

```python
# Start agent for service class (serves all instances)
agent_id = await oaas.start_agent(Calculator)

# Start agent for specific object instance
agent_id = await oaas.start_agent(Calculator, obj_id=123)

# Start agent with specific partition
agent_id = await oaas.start_agent(Calculator, partition_id=1)
```

### Managing Agents

```python
# List all running agents
agents = oaas.list_agents()
for agent_id, info in agents.items():
    print(f"Agent: {agent_id}")
    print(f"  Service: {info['service_name']}")
    print(f"  Package: {info['package']}")
    print(f"  Object ID: {info['obj_id']}")
    print(f"  Started: {info['started_at']}")

# Stop specific agent
await oaas.stop_agent(agent_id)

# Stop agent by service class
await oaas.stop_agent(service_class=Calculator, obj_id=123)

# Stop all agents
await oaas.stop_all_agents()
```

## Convenience Methods

### Class-Level Methods

```python
# Start agent for the service class
agent_id = await Calculator.start_agent()

# Start agent for specific object
agent_id = await Calculator.start_agent(obj_id=123)

# Stop agent
await Calculator.stop_agent()
await Calculator.stop_agent(obj_id=123)
```

### Instance-Level Methods

```python
# Create service instance
calc = Calculator.create(obj_id=456)

# Start agent for this specific instance
agent_id = await calc.start_instance_agent()

# Stop agent for this instance
await calc.stop_instance_agent()
```

## Error Handling

The system provides specific error types for different failure scenarios:

```python
from oaas_sdk2_py.simplified import ServerError, AgentError

# Server errors
try:
    oaas.start_server(port=8080)
    oaas.start_server(port=8081)  # This will fail
except ServerError as e:
    print(f"Server error: {e}")

# Agent errors
try:
    await oaas.start_agent(UnregisteredService)  # This will fail
except AgentError as e:
    print(f"Agent error: {e}")
```

## Complete Example

```python
import asyncio
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig

@oaas.service("Calculator", package="math")
class Calculator(OaasObject):
    result: int = 0
    
    @oaas.method(serve_with_agent=True)
    async def increment(self) -> int:
        self.result += 1
        return self.result

async def main():
    # Configure and start server
    config = OaasConfig(async_mode=True, mock_mode=False)
    oaas.configure(config)
    
    # Start gRPC server
    oaas.start_server(port=8080)
    
    # Start agent for Calculator service
    agent_id = await oaas.start_agent(Calculator)
    
    print(f"Server running: {oaas.is_server_running()}")
    print(f"Agent started: {agent_id}")
    
    # Server and agent are now running and ready to handle requests
    # ... do work ...
    
    # Cleanup
    await oaas.stop_agent(agent_id)
    oaas.stop_server()

if __name__ == "__main__":
    asyncio.run(main())
```

## Backward Compatibility

The new functionality maintains full backward compatibility with existing code:

```python
# Direct access to global Oparaca instance
oparaca = oaas.get_global_oaas()
oparaca.start_grpc_server(port=8080)
await oparaca.run_agent(loop, cls_meta, obj_id)
oparaca.stop_server()
```

## Implementation Notes

- All server operations are synchronous
- All agent operations are asynchronous (use `await`)
- Server must be running before starting agents
- Agent IDs are automatically generated based on service name and object ID
- Multiple agents can run simultaneously for different services or objects
- The system tracks agent state and provides detailed information
- Error handling is comprehensive with specific error types for different scenarios

## Integration with Session Management

The server and agent management system integrates seamlessly with the existing AutoSessionManager:

- Agents automatically handle session lifecycle
- Object state is preserved across agent restarts
- Performance metrics are tracked automatically
- Debug logging provides detailed operation tracing
