# OaaS SDK API Reference

## Table of Contents
1. [Simplified Interface](#simplified-interface)
2. [Core Decorators](#core-decorators)
3. [Base Classes](#base-classes)
4. [Configuration](#configuration)
5. [Type System](#type-system)
6. [Server and Agent Management](#server-and-agent-management)
7. [Error Handling](#error-handling)
8. [Legacy API](#legacy-api)

## Simplified Interface

The OaaS SDK provides a simplified interface through the global `oaas` object and decorators.

### Module Import

```python
from oaas_sdk2_py import oaas, OaasObject, OaasConfig
```

### Global Configuration

**Function:** `oaas.configure(config: OaasConfig)`

Configure the global OaaS runtime.

```python
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)
```

## Core Decorators

### @oaas.service

**Decorator:** `@oaas.service(name: str, package: str = "default")`

Define an OaaS service class.

**Parameters:**
- `name` (str): Service name
- `package` (str): Package name (default: "default")

**Usage:**
```python
@oaas.service("MyService", package="example")
class MyService(OaasObject):
    pass
```

### @oaas.method

**Decorator:** `@oaas.method(name: str = None, serve_with_agent: bool = False)`

Expose a method as an OaaS RPC endpoint.

**Parameters:**
- `name` (str, optional): Override method name
- `serve_with_agent` (bool): Whether method can be served by an agent

**Usage:**
```python
@oaas.method()
async def my_method(self, param: int) -> str:
    return f"Result: {param}"

@oaas.method(name="custom_name", serve_with_agent=True)
async def background_task(self) -> bool:
    # Long-running task suitable for agent execution
    return True
```

## Base Classes

### OaasObject

**Module:** `oaas_sdk2_py.simplified.objects`

Base class for all OaaS service objects.

#### Class Methods

| Method | Description |
| --- | --- |
| `create(obj_id: int = None, local: bool = False) -> Self` | Create new object instance |
| `load(obj_id: int) -> Self` | Load existing object by ID |

#### Instance Methods

| Method | Description |
| --- | --- |
| `delete() -> None` | Mark object for deletion |
| `commit() -> None` | Commit changes (sync) |
| `commit_async() -> None` | Commit changes (async) |

#### State Management

OaaS objects automatically persist their attributes:

```python
@oaas.service("Counter", package="example")
class Counter(OaasObject):
    count: int = 0          # Automatically persisted
    history: list = []      # Automatically persisted
    metadata: dict = {}     # Automatically persisted
    
    @oaas.method()
    async def increment(self, amount: int = 1) -> int:
        self.count += amount  # Change is automatically tracked
        self.history.append(f"Added {amount}")
        return self.count
```

## Configuration

### OaasConfig

**Module:** `oaas_sdk2_py.simplified.config`

Configuration class for OaaS runtime settings.

#### Attributes

| Attribute | Type | Default | Description |
| --- | --- | --- | --- |
| `async_mode` | `bool` | `True` | Enable async operations |
| `mock_mode` | `bool` | `False` | Use mock implementation for testing |
| `server_url` | `str` | `"http://localhost:10000"` | OaaS platform URL |
| `default_partition` | `int` | `0` | Default partition ID |
| `log_level` | `str` | `"INFO"` | Logging level |
| `timeout` | `float` | `30.0` | Request timeout in seconds |

#### Usage

```python
config = OaasConfig(
    async_mode=True,
    mock_mode=False,
    server_url="http://localhost:10000",
    default_partition=0,
    log_level="DEBUG",
    timeout=60.0
)
oaas.configure(config)
```

## Type System

### Supported Types

The OaaS SDK natively supports these Python types for method parameters and return values:

#### Primitive Types

| Type | Description | Example |
| --- | --- | --- |
| `int` | Integer numbers | `42`, `-10`, `0` |
| `float` | Floating point numbers | `3.14`, `-2.5`, `0.0` |
| `bool` | Boolean values | `True`, `False` |
| `str` | String values | `"Hello"`, `""` |

#### Collection Types

| Type | Description | Example |
| --- | --- | --- |
| `list` | Lists of any supported type | `[1, 2, 3]`, `["a", "b"]` |
| `dict` | Dictionaries with string keys | `{"key": "value", "count": 42}` |

#### Binary Data

| Type | Description | Example |
| --- | --- | --- |
| `bytes` | Binary data | `b"binary data"`, `"text".encode()` |

#### Pydantic Models

| Type | Description | Example |
| --- | --- | --- |
| `BaseModel` | Pydantic models for structured data | Custom model classes |

### Method Parameter Limitation

**Important**: OaaS methods support only **one parameter** (plus `self`). For multiple values, use a dictionary or Pydantic model:

```python
# ❌ Multiple parameters NOT supported
@oaas.method()
async def bad_method(self, param1: int, param2: str) -> str:
    # This will cause errors
    pass

# ✅ Use Pydantic model (RECOMMENDED)
class MyRequest(BaseModel):
    param1: int
    param2: str

@oaas.method()
async def good_method(self, request: MyRequest) -> str:
    return f"{request.param1}: {request.param2}"

# ✅ Use dictionary for simple cases
@oaas.method()
async def dict_method(self, params: Dict[str, Any]) -> str:
    return f"{params['param1']}: {params['param2']}"
```

### Type Examples

```python
from pydantic import BaseModel
from typing import List, Dict, Any

class UserRequest(BaseModel):
    name: str
    age: int
    email: str

class UserResponse(BaseModel):
    id: int
    name: str
    created: bool

@oaas.service("UserService", package="example")
class UserService(OaasObject):
    users: Dict[int, Dict[str, Any]] = {}
    next_id: int = 1
    
    @oaas.method()
    async def create_user(self, request: UserRequest) -> UserResponse:
        """Create user with Pydantic model."""
        user_id = self.next_id
        self.next_id += 1
        
        self.users[user_id] = {
            "name": request.name,
            "age": request.age,
            "email": request.email
        }
        
        return UserResponse(id=user_id, name=request.name, created=True)
    
    @oaas.method()
    async def get_user_count(self) -> int:
        """Return count as integer."""
        return len(self.users)
    
    @oaas.method()
    async def get_average_age(self) -> float:
        """Return average age as float."""
        if not self.users:
            return 0.0
        total_age = sum(user["age"] for user in self.users.values())
        return total_age / len(self.users)
    
    @oaas.method()
    async def has_users(self) -> bool:
        """Return boolean status."""
        return len(self.users) > 0
    
    @oaas.method()
    async def get_user_names(self) -> List[str]:
        """Return list of names."""
        return [user["name"] for user in self.users.values()]
    
    @oaas.method()
    async def get_user_stats(self) -> Dict[str, Any]:
        """Return statistics as dictionary."""
        return {
            "total_users": len(self.users),
            "average_age": await self.get_average_age(),
            "has_users": await self.has_users()
        }
    
    @oaas.method()
    async def export_users(self) -> bytes:
        """Export users as JSON bytes."""
        import json
        data = json.dumps(self.users)
        return data.encode('utf-8')
    
    @oaas.method()
    async def get_status_message(self) -> str:
        """Return status as string."""
        count = len(self.users)
        if count == 0:
            return "No users registered"
        elif count == 1:
            return "1 user registered"
        else:
            return f"{count} users registered"
```

### Type Conversion

The SDK automatically handles type conversion between Python objects and the OaaS platform:

```python
@oaas.method()
async def calculate_percentage(self, correct: int, total: int) -> float:
    """Automatically converts result to float."""
    return (correct / total) * 100.0  # int division result becomes float

@oaas.method() 
async def format_percentage(self, percentage: float) -> str:
    """Automatically converts float to string."""
    return f"{percentage:.2f}%"  # String formatting

@oaas.method()
async def is_passing_grade(self, percentage: float) -> bool:
    """Automatically converts comparison to bool."""
    return percentage >= 60.0  # Comparison result becomes bool
```

## Server and Agent Management

### Server Management

Servers host service definitions and handle gRPC requests from external clients.

#### Functions

| Function | Description |
| --- | --- |
| `oaas.start_server(port: int = 8080, loop = None)` | Start gRPC server |
| `oaas.stop_server()` | Stop running server |
| `oaas.is_server_running() -> bool` | Check if server is running |
| `oaas.get_server_info() -> Dict[str, Any]` | Get server information |

#### Usage

```python
# Start server
oaas.start_server(port=8080)

# Check status
if oaas.is_server_running():
    info = oaas.get_server_info()
    print(f"Server running on port {info.get('port', 'unknown')}")

# Stop server
oaas.stop_server()
```

### Agent Management

Agents host specific object instances and handle background processing.

#### Functions

| Function | Description |
| --- | --- |
| `oaas.start_agent(service_class, obj_id: int = None) -> str` | Start agent for service instance |
| `oaas.stop_agent(agent_id: str)` | Stop specific agent |
| `oaas.list_agents() -> List[str]` | List all running agents |
| `oaas.stop_all_agents()` | Stop all running agents |

#### Usage

```python
# Start agent for specific object
agent_id = await oaas.start_agent(MyService, obj_id=123)
print(f"Started agent: {agent_id}")

# List all agents
agents = oaas.list_agents()
print(f"Running agents: {agents}")

# Stop specific agent
await oaas.stop_agent(agent_id)

# Stop all agents
await oaas.stop_all_agents()
```

### Combined Server + Agent Example

```python
import asyncio

async def run_service():
    # Start server for external access
    oaas.start_server(port=8080)
    
    # Start agents for background processing
    agent1 = await oaas.start_agent(UserService, obj_id=1)
    agent2 = await oaas.start_agent(Counter, obj_id=1)
    
    print(f"Server running: {oaas.is_server_running()}")
    print(f"Agents: {oaas.list_agents()}")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Cleanup
        await oaas.stop_all_agents()
        oaas.stop_server()

if __name__ == "__main__":
    asyncio.run(run_service())
```

## Error Handling

### OaasError

**Module:** `oaas_sdk2_py.simplified.errors`

Base exception class for OaaS-specific errors.

```python
from oaas_sdk2_py.simplified.errors import OaasError

@oaas.method()
async def divide(self, a: float, b: float) -> float:
    if b == 0:
        raise OaasError("Division by zero is not allowed")
    return a / b
```

### ServerError

**Module:** `oaas_sdk2_py.simplified.errors`

Exception for server-related errors.

```python
from oaas_sdk2_py.simplified.errors import ServerError

# Raised when server operations fail
try:
    oaas.start_server(port=8080)
except ServerError as e:
    print(f"Failed to start server: {e}")
```

### AgentError

**Module:** `oaas_sdk2_py.simplified.errors`

Exception for agent-related errors.

```python
from oaas_sdk2_py.simplified.errors import AgentError

# Raised when agent operations fail
try:
    agent_id = await oaas.start_agent(MyService, obj_id=123)
except AgentError as e:
    print(f"Failed to start agent: {e}")
```

## Legacy API

The SDK maintains backward compatibility with the original API. See the legacy documentation for:

### Legacy Classes

- **Oparaca**: Main engine class
- **BaseObject**: Legacy base object class
- **Session**: Session management for transactions
- **ClsMeta**: Class metadata management

### Legacy Usage

```python
from oaas_sdk2_py import Oparaca, BaseObject

# Legacy API still works
oaas_engine = Oparaca()
cls_meta = oaas_engine.new_cls("MyClass", pkg="example")

@cls_meta
class MyLegacyClass(BaseObject):
    @cls_meta.func()
    async def my_method(self, data: str) -> str:
        return f"Processed: {data}"

# Legacy session management
session = oaas_engine.new_session()
obj = session.create_object(cls_meta, obj_id=1)
result = await obj.my_method("test")
await session.commit_async()
```

### Migration Guide

To migrate from legacy API to simplified API:

#### Before (Legacy)
```python
from oaas_sdk2_py import Oparaca, BaseObject

oaas_engine = Oparaca()
cls_meta = oaas_engine.new_cls("Counter", pkg="example")

@cls_meta
class Counter(BaseObject):
    @cls_meta.func()
    async def increment(self, amount: int) -> int:
        # Manual state management
        data = await self.get_data_async(0)
        count = int(data.decode()) if data else 0
        count += amount
        await self.set_data_async(0, str(count).encode())
        return count

# Usage
session = oaas_engine.new_session()
counter = session.create_object(cls_meta, obj_id=1)
result = await counter.increment(5)
await session.commit_async()
```

#### After (Simplified)
```python
from oaas_sdk2_py import oaas, OaasObject, OaasConfig

config = OaasConfig(async_mode=True)
oaas.configure(config)

@oaas.service("Counter", package="example")
class Counter(OaasObject):
    count: int = 0  # Automatic state management
    
    @oaas.method()
    async def increment(self, amount: int) -> int:
        self.count += amount  # Direct attribute access
        return self.count

# Usage
counter = Counter.create(obj_id=1)
result = await counter.increment(5)
# No manual commit needed - automatic persistence
```

### Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `OPRC_ODGM_URL` | OaaS platform URL | `http://localhost:10000` |
| `OPRC_PARTITION_DEFAULT` | Default partition ID | `0` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HTTP_PORT` | HTTP server port | `8080` |

### Complete Example

```python
import asyncio
from pydantic import BaseModel
from typing import List, Dict, Any
from oaas_sdk2_py import oaas, OaasObject, OaasConfig

# Configure OaaS
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)

# Define models
class TaskRequest(BaseModel):
    title: str
    description: str
    priority: int = 1

class TaskResponse(BaseModel):
    id: int
    title: str
    completed: bool

# Define service
@oaas.service("TaskManager", package="productivity")
class TaskManager(OaasObject):
    """A task management service demonstrating the complete API."""
    
    tasks: Dict[int, Dict[str, Any]] = {}
    next_id: int = 1
    
    @oaas.method()
    async def create_task(self, request: TaskRequest) -> TaskResponse:
        """Create a new task."""
        task_id = self.next_id
        self.next_id += 1
        
        self.tasks[task_id] = {
            "title": request.title,
            "description": request.description,
            "priority": request.priority,
            "completed": False
        }
        
        return TaskResponse(
            id=task_id,
            title=request.title,
            completed=False
        )
    
    @oaas.method()
    async def complete_task(self, task_id: int) -> bool:
        """Mark task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id]["completed"] = True
            return True
        return False
    
    @oaas.method()
    async def get_task_count(self) -> int:
        """Get total number of tasks."""
        return len(self.tasks)
    
    @oaas.method()
    async def get_completion_rate(self) -> float:
        """Get task completion rate as percentage."""
        if not self.tasks:
            return 0.0
        completed = sum(1 for task in self.tasks.values() if task["completed"])
        return (completed / len(self.tasks)) * 100.0
    
    @oaas.method()
    async def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks."""
        return [
            {"id": task_id, **task_data}
            for task_id, task_data in self.tasks.items()
        ]
    
    @oaas.method()
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "total_tasks": len(self.tasks),
            "completed_tasks": sum(1 for task in self.tasks.values() if task["completed"]),
            "completion_rate": await self.get_completion_rate(),
            "has_tasks": len(self.tasks) > 0
        }
    
    @oaas.method()
    async def export_data(self) -> bytes:
        """Export all tasks as JSON bytes."""
        import json
        data = json.dumps(self.tasks, indent=2)
        return data.encode('utf-8')

# Usage example
async def main():
    # Start server
    oaas.start_server(port=8080)
    
    # Start agent
    agent_id = await oaas.start_agent(TaskManager, obj_id=1)
    
    try:
        # Create and use service
        manager = TaskManager.create(obj_id=1)
        
        # Create tasks
        task1 = await manager.create_task(TaskRequest(title="Learn OaaS", description="Complete tutorial"))
        task2 = await manager.create_task(TaskRequest(title="Build app", description="Create demo", priority=2))
        
        # Complete a task
        await manager.complete_task(task1.id)
        
        # Get statistics
        stats = await manager.get_stats()
        print(f"Stats: {stats}")
        
        # Get completion rate
        rate = await manager.get_completion_rate()
        print(f"Completion rate: {rate}%")
        
        # List all tasks
        tasks = await manager.list_tasks()
        print(f"All tasks: {tasks}")
        
    finally:
        # Cleanup
        await oaas.stop_agent(agent_id)
        oaas.stop_server()

if __name__ == "__main__":
    asyncio.run(main())
```

This reference covers the complete simplified OaaS SDK API with comprehensive examples and usage patterns.
