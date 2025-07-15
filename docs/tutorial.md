# OaaS SDK Tutorial

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Basic Concepts](#basic-concepts)
5. [Creating Your First OaaS Class](#creating-your-first-oaas-class)
6. [Working with Objects](#working-with-objects)
7. [Sessions and Transactions](#sessions-and-transactions)
8. [Function Types and Decorators](#function-types-and-decorators)
9. [Data Management](#data-management)
10. [Remote Procedure Calls](#remote-procedure-calls)
11. [Event-Driven Programming](#event-driven-programming)
12. [Testing with Mock Mode](#testing-with-mock-mode)
13. [Advanced Topics](#advanced-topics)
14. [Best Practices](#best-practices)

## Introduction

The OaaS (Objects as a Service) SDK is a Python framework for building distributed, stateful applications. It provides a simple yet powerful abstraction for creating object-oriented services that can be distributed across multiple processes or machines.

### Conceptual Overview

The OaaS SDK is a helper library designed to simplify the development of classes that run on the **Object-as-a-Service (OaaS) Platform**. The platform manages the lifecycle, state, and communication of distributed objects, allowing you to focus on business logic rather than infrastructure.

Think of the OaaS platform as a managed environment for your Python objects. You define the behavior and state of your objects using this SDK, and the platform takes care of:

-   **Persistence**: Automatically saving and loading the state of your objects.
-   **Distribution**: Making your objects accessible across a network.
-   **Concurrency**: Handling multiple requests to your objects.
-   **Scalability**: Running many instances of your objects.

This SDK provides the necessary building blocks (`Oparaca`, `BaseObject`, decorators, etc.) to make your Python classes compatible with the OaaS platform, effectively turning them into scalable, stateful microservices.

### Key Features

- **Distributed Objects**: Create objects that can be accessed remotely across processes
- **Stateful Services**: Objects maintain state that persists between method calls
- **Async/Sync Support**: Full support for both synchronous and asynchronous operations
- **Type Safety**: Built-in support for Pydantic models and type hints
- **Event-Driven Architecture**: Trigger-based event system for reactive programming
- **Transaction Support**: Session-based transactions for consistency
- **Mock Support**: Built-in mocking for testing and development

## Installation

```bash
pip install oaas-sdk2-py
```

## Getting Started

### Quick Start Example

```python
from oaas_sdk2_py import Oparaca, BaseObject
from pydantic import BaseModel

# Create OaaS instance
oaas = Oparaca()

# Define request/response models
class GreetRequest(BaseModel):
    name: str

class GreetResponse(BaseModel):
    message: str

# Create a class metadata
greeter_cls = oaas.new_cls("Greeter", pkg="example")

@greeter_cls
class Greeter(BaseObject):
    @greeter_cls.func()
    async def greet(self, req: GreetRequest) -> GreetResponse:
        return GreetResponse(message=f"Hello, {req.name}!")

# Usage
async def main():
    session = oaas.new_session()
    greeter = session.create_object(greeter_cls)
    response = await greeter.greet(GreetRequest(name="World"))
    print(response.message)  # Output: Hello, World!
```

## Basic Concepts

### 1. Oparaca Engine

The [`Oparaca`](oaas_sdk2_py/engine.py:17) class is the main engine that manages the entire OaaS system:

```python
from oaas_sdk2_py import Oparaca
from oaas_sdk2_py.config import OprcConfig

# Basic configuration
config = OprcConfig(
    oprc_odgm_url="http://localhost:10000",
    oprc_partition_default=0
)

oaas = Oparaca(
    default_pkg="my_package",
    config=config,
    mock_mode=False,  # Set to True for testing
    async_mode=True   # Enable async server mode
)
```

### 2. Class Metadata

Before creating objects, you need to define class metadata using [`new_cls()`](oaas_sdk2_py/engine.py:59):

```python
# Create class metadata
my_cls = oaas.new_cls(name="MyService", pkg="my_package")
```

### 3. BaseObject

All OaaS objects must inherit from [`BaseObject`](oaas_sdk2_py/obj.py:10):

```python
from oaas_sdk2_py import BaseObject

@my_cls
class MyService(BaseObject):
    pass
```

### 4. Sessions

Sessions manage object lifecycle and provide transaction boundaries:

```python
session = oaas.new_session(partition_id=0)
obj = session.create_object(my_cls)
```

## Creating Your First OaaS Class

Let's create a simple counter service:

```python
from oaas_sdk2_py import Oparaca, BaseObject
from pydantic import BaseModel
import json

# Initialize OaaS
oaas = Oparaca()

# Define models
class IncrementRequest(BaseModel):
    amount: int = 1

class CounterResponse(BaseModel):
    count: int

# Create class metadata
counter_cls = oaas.new_cls("Counter", pkg="example")

@counter_cls
class Counter(BaseObject):
    async def get_count(self) -> int:
        """Get current count from persistent storage"""
        raw = await self.get_data_async(0)
        return json.loads(raw.decode()) if raw else 0
    
    async def set_count(self, count: int):
        """Set count in persistent storage"""
        await self.set_data_async(0, json.dumps(count).encode())
    
    @counter_cls.func()
    async def increment(self, req: IncrementRequest) -> CounterResponse:
        """Increment counter by specified amount"""
        current = await self.get_count()
        new_count = current + req.amount
        await self.set_count(new_count)
        return CounterResponse(count=new_count)
    
    @counter_cls.func()
    async def get_value(self) -> CounterResponse:
        """Get current counter value"""
        count = await self.get_count()
        return CounterResponse(count=count)
    
    @counter_cls.func()
    async def reset(self) -> CounterResponse:
        """Reset counter to zero"""
        await self.set_count(0)
        return CounterResponse(count=0)
```

### Usage Example

```python
async def main():
    # Create session
    session = oaas.new_session()
    
    # Create counter object
    counter = session.create_object(counter_cls, obj_id=1)
    
    # Use the counter
    result = await counter.increment(IncrementRequest(amount=5))
    print(f"Count after increment: {result.count}")
    
    result = await counter.get_value()
    print(f"Current count: {result.count}")
    
    # Commit changes
    await session.commit_async()
```

## Working with Objects

### Object Creation

There are two ways to work with objects:

1. **Create new objects**: Use [`create_object()`](oaas_sdk2_py/session.py:59)
2. **Load existing objects**: Use [`load_object()`](oaas_sdk2_py/session.py:95)

```python
# Create new object
new_obj = session.create_object(my_cls, obj_id=123, local=False)

# Load existing object
existing_obj = session.load_object(my_cls, obj_id=123)
```

### Local vs Remote Objects

Objects can be local (in-process) or remote (distributed):

```python
# Local object (stays in current process)
local_obj = session.create_object(my_cls, local=True)

# Remote object (can be distributed)
remote_obj = session.create_object(my_cls, local=False)
```

### Object Deletion

```python
# Delete object
session.delete_object(my_cls, obj_id=123)
await session.commit_async()

# Or delete from the object itself
obj.delete()
await obj.commit_async()
```

## Sessions and Transactions

### Session Management

Sessions provide transaction boundaries and object lifecycle management:

```python
# Create session with specific partition
session = oaas.new_session(partition_id=1)

# Create objects within session
obj1 = session.create_object(cls1)
obj2 = session.create_object(cls2)

# Commit all changes
await session.commit_async()
```

### Transaction Semantics

Changes are not persisted until you commit:

```python
async def transfer_data():
    session = oaas.new_session()
    
    source = session.load_object(account_cls, source_id)
    target = session.load_object(account_cls, target_id)
    
    # Modify objects
    await source.withdraw(amount)
    await target.deposit(amount)
    
    # Commit both changes atomically
    await session.commit_async()
```

## Function Types and Decorators

### Basic Function Decorator

The [`@cls.func()`](oaas_sdk2_py/model.py:176) decorator registers methods as OaaS functions:

```python
@my_cls.func()
async def my_method(self, req: MyRequest) -> MyResponse:
    # Method implementation
    return MyResponse(...)
```

### Decorator Parameters

- **`name`**: Override function name
- **`stateless`**: Function doesn't modify object state
- **`serve_with_agent`**: Function can be served by an agent

```python
@my_cls.func(name="custom_name", stateless=True, serve_with_agent=True)
async def my_stateless_function(self, req: MyRequest) -> MyResponse:
    # Stateless function implementation
    return MyResponse(...)
```

### Stateless Functions

Stateless functions don't require a specific object instance:

```python
@my_cls.func(stateless=True)
async def utility_function(self, req: UtilityRequest) -> UtilityResponse:
    # This function doesn't use object state
    return UtilityResponse(result=req.input.upper())
```

### Function Parameter Types

Functions can accept various parameter types:

```python
# Pydantic model
@my_cls.func()
async def with_model(self, req: MyModel) -> MyResponse:
    pass

# Raw bytes
@my_cls.func()
async def with_bytes(self, data: bytes) -> MyResponse:
    pass

# String
@my_cls.func()
async def with_string(self, data: str) -> MyResponse:
    pass

# Dictionary
@my_cls.func()
async def with_dict(self, data: dict) -> MyResponse:
    pass

# Request object
@my_cls.func()
async def with_request(self, req: ObjectInvocationRequest) -> MyResponse:
    pass

# Model and request
@my_cls.func()
async def with_both(self, model: MyModel, req: ObjectInvocationRequest) -> MyResponse:
    pass
```

## Data Management

### Persistent Data Storage

Objects can store persistent data using indexed storage:

```python
@my_cls
class DataService(BaseObject):
    async def store_user_data(self, user_id: int, data: dict):
        """Store user data at index based on user_id"""
        serialized = json.dumps(data).encode()
        await self.set_data_async(user_id, serialized)
    
    async def get_user_data(self, user_id: int) -> dict:
        """Retrieve user data by user_id"""
        raw = await self.get_data_async(user_id)
        return json.loads(raw.decode()) if raw else {}
```

### Data Helpers

Create helper methods for common data operations:

```python
@my_cls
class ConfigService(BaseObject):
    CONFIG_INDEX = 0
    
    async def get_config(self) -> dict:
        """Get configuration dictionary"""
        raw = await self.get_data_async(self.CONFIG_INDEX)
        return json.loads(raw.decode()) if raw else {}
    
    async def set_config(self, config: dict):
        """Set configuration dictionary"""
        await self.set_data_async(self.CONFIG_INDEX, json.dumps(config).encode())
    
    async def update_config(self, key: str, value: any):
        """Update a single config value"""
        config = await self.get_config()
        config[key] = value
        await self.set_config(config)
```

## Remote Procedure Calls

### RPC Behavior

When objects are remote, method calls automatically become RPC calls:

```python
async def rpc_example():
    session = oaas.new_session()
    
    # Create remote object
    remote_obj = session.create_object(my_cls, local=False)
    
    # This will be an RPC call
    result = await remote_obj.my_method(MyRequest(...))
    
    # Create local object
    local_obj = session.create_object(my_cls, local=True)
    
    # This will be a local call
    result = await local_obj.my_method(MyRequest(...))
```

### Manual RPC

You can also perform manual RPC calls:

```python
from oaas_sdk2_py import ObjectInvocationRequest, InvocationRequest

# Object method RPC
request = ObjectInvocationRequest(
    cls_id="my_pkg.MyClass",
    partition_id=0,
    object_id=123,
    fn_id="my_method",
    payload=json.dumps({"param": "value"}).encode()
)
response = await session.obj_rpc_async(request)

# Static function RPC
request = InvocationRequest(
    cls_id="my_pkg.MyClass",
    fn_id="my_static_method",
    payload=json.dumps({"param": "value"}).encode()
)
response = await session.fn_rpc_async(request)
```

## Event-Driven Programming

### Triggers

Objects can register triggers to respond to events:

```python
from oprc_py.oprc_py import DataTriggerType, FnTriggerType

@my_cls
class EventDrivenService(BaseObject):
    @my_cls.func()
    async def on_data_change(self, req: ChangeNotification):
        # Handle data change event
        pass
    
    @my_cls.func()
    async def setup_triggers(self):
        # Trigger on data change at index 0
        self.trigger(
            source=0,  # Data index
            target_fn=self.on_data_change,
            event_type=DataTriggerType.OnSet
        )
        
        # Trigger on function completion
        self.trigger(
            source=self.some_function,
            target_fn=self.on_function_complete,
            event_type=FnTriggerType.OnSuccess
        )
```

### Managing Triggers

```python
# Add trigger
obj.trigger(source, target_fn, event_type)

# Remove trigger
obj.suppress(source, target_fn, event_type)
```

## Testing with Mock Mode

### Mock Mode Setup

Enable mock mode for testing:

```python
# Create mock instance
mock_oaas = oaas.mock()

# Or create with mock mode enabled
oaas = Oparaca(mock_mode=True)
```

### Mock Testing Example

```python
import pytest
from oaas_sdk2_py import Oparaca, BaseObject

@pytest.mark.asyncio
async def test_counter_service():
    # Setup mock environment
    oaas = Oparaca(mock_mode=True)
    counter_cls = oaas.new_cls("Counter", pkg="test")
    
    @counter_cls
    class Counter(BaseObject):
        @counter_cls.func()
        async def increment(self, req: IncrementRequest) -> CounterResponse:
            # Implementation
            pass
    
    # Test the service
    session = oaas.new_session()
    counter = session.create_object(counter_cls)
    
    result = await counter.increment(IncrementRequest(amount=5))
    assert result.count == 5
    
    await session.commit_async()
```

## Advanced Topics

### Server Mode

Run OaaS as a server:

```python
import asyncio

async def run_server():
    oaas = Oparaca(async_mode=True)
    
    # Define your classes here
    # ...
    
    # Start server
    loop = asyncio.get_event_loop()
    oaas.start_grpc_server(loop, port=8080)
    
    try:
        await asyncio.Event().wait()  # Run forever
    finally:
        oaas.stop_server()

if __name__ == "__main__":
    asyncio.run(run_server())
```

### Agent Mode

Run functions as agents:

```python
async def run_agent():
    oaas = Oparaca(async_mode=True)
    
    # Run agent for specific object and class
    loop = asyncio.get_event_loop()
    await oaas.run_agent(loop, my_cls, obj_id=123)
```

### Configuration

Configure OaaS with [`OprcConfig`](oaas_sdk2_py/config.py:5):

```python
from oaas_sdk2_py.config import OprcConfig

config = OprcConfig(
    oprc_odgm_url="http://localhost:10000",
    oprc_zenoh_peers="peer1:7447,peer2:7447",
    oprc_partition_default=0
)

oaas = Oparaca(config=config)
```

### Metadata Export

Export class metadata for external tools:

```python
# Print package metadata
oaas.meta_repo.print_pkg()

# Export as dictionary
pkg_dict = oaas.meta_repo.export_pkg()
```

## Best Practices

### 1. Error Handling

Always handle errors appropriately:

```python
from oaas_sdk2_py import InvocationResponse, InvocationResponseCode

@my_cls.func()
async def safe_function(self, req: MyRequest) -> MyResponse:
    try:
        # Your logic here
        return MyResponse(success=True)
    except Exception as e:
        return InvocationResponse(
            status=int(InvocationResponseCode.AppError),
            payload=str(e).encode()
        )
```

### 2. Resource Management

Use proper resource management:

```python
async def process_data():
    session = oaas.new_session()
    try:
        obj = session.create_object(my_cls)
        # Process data
        await obj.process()
    finally:
        await session.commit_async()
```

### 3. Type Safety

Use Pydantic models for type safety:

```python
from pydantic import BaseModel, Field

class UserRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')

@my_cls.func()
async def create_user(self, req: UserRequest) -> UserResponse:
    # Type checking is automatic
    pass
```

### 4. Async Best Practices

Use async consistently:

```python
@my_cls.func()
async def async_function(self, req: MyRequest) -> MyResponse:
    # Use async versions of methods
    data = await self.get_data_async(0)
    await self.set_data_async(0, new_data)
    await self.commit_async()
    return MyResponse(...)
```

### 5. Testing

Write comprehensive tests:

```python
import pytest
from oaas_sdk2_py import Oparaca

@pytest.fixture
def mock_oaas():
    return Oparaca(mock_mode=True)

@pytest.mark.asyncio
async def test_my_service(mock_oaas):
    # Test implementation
    pass
```

This tutorial covers the essential aspects of the OaaS SDK. For detailed API documentation, refer to the [API Reference](reference.md).