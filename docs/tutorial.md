# OaaS SDK Tutorial

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Basic Concepts](#basic-concepts)
5. [Creating Your First OaaS Service](#creating-your-first-oaas-service)
6. [Working with Objects](#working-with-objects)
7. [Type System](#type-system)
8. [Server and Agent Management](#server-and-agent-management)
9. [Configuration](#configuration)
10. [Testing with Mock Mode](#testing-with-mock-mode)
11. [Advanced Topics](#advanced-topics)
12. [Best Practices](#best-practices)

## Introduction

The OaaS (Objects as a Service) SDK is a Python framework for building distributed, stateful applications. It provides a simple yet powerful abstraction for creating object-oriented services that can be distributed across multiple processes or machines.

### Conceptual Overview

The OaaS SDK is a helper library designed to simplify the development of classes that run on the **Object-as-a-Service (OaaS) Platform**. The platform manages the lifecycle, state, and communication of distributed objects, allowing you to focus on business logic rather than infrastructure.

Think of the OaaS platform as a managed environment for your Python objects. You define the behavior and state of your objects using this SDK, and the platform takes care of:

-   **Persistence**: Automatically saving and loading the state of your objects.
-   **Distribution**: Making your objects accessible across a network.
-   **Concurrency**: Handling multiple requests to your objects.
-   **Scalability**: Running many instances of your objects.

This SDK provides the necessary building blocks (`@oaas.service`, `@oaas.method`, `OaasObject`, etc.) to make your Python classes compatible with the OaaS platform, effectively turning them into scalable, stateful microservices.

### Key Features

- **Simplified API**: Easy-to-use decorators with minimal boilerplate
- **Native Type Support**: Built-in support for Python primitives (`int`, `float`, `bool`, `str`, `list`, `dict`, `bytes`) and Pydantic models
- **Server/Agent Independence**: Servers host service definitions, agents host object instances
- **Async/Sync Support**: Full support for both synchronous and asynchronous operations
- **State Management**: Objects maintain persistent state across method calls
- **Event-Driven Architecture**: Trigger-based event system for reactive programming
- **Mock Support**: Built-in mocking for testing and development

## Installation

```bash
pip install oaas-sdk2-py
```

## Getting Started

### Quick Start Example

```python
from oaas_sdk2_py import oaas, OaasObject, OaasConfig
from pydantic import BaseModel

# Configure OaaS
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)

# Define request/response models
class GreetRequest(BaseModel):
    name: str

class GreetResponse(BaseModel):
    message: str

# Create your service
@oaas.service("Greeter", package="example")
class Greeter(OaasObject):
    greeting_count: int = 0
    
    @oaas.method()
    async def greet(self, req: GreetRequest) -> GreetResponse:
        self.greeting_count += 1
        return GreetResponse(message=f"Hello, {req.name}! (Greeting #{self.greeting_count})")
    
    @oaas.method()
    async def get_count(self) -> int:
        return self.greeting_count

# Usage
async def main():
    greeter = Greeter.create(local=True)
    response = await greeter.greet(GreetRequest(name="World"))
    count = await greeter.get_count()
    print(f"{response.message} | Total greetings: {count}")
```

## Basic Concepts

### 1. OaaS Configuration

Configure the OaaS runtime using [`OaasConfig`](oaas_sdk2_py/simplified/config.py):

```python
from oaas_sdk2_py import oaas, OaasConfig

# Basic configuration
config = OaasConfig(
    async_mode=True,          # Enable async operations
    mock_mode=False,          # Use real OaaS platform
    server_url="http://localhost:10000",
    default_partition=0
)

oaas.configure(config)
```

### 2. Service Definition

Define services using the [`@oaas.service`](oaas_sdk2_py/simplified/service.py) decorator:

```python
@oaas.service("MyService", package="my_package")
class MyService(OaasObject):
    pass
```

### 3. Method Exposure

Expose methods as RPC endpoints using [`@oaas.method`](oaas_sdk2_py/simplified/service.py):

```python
@oaas.method()
async def my_method(self, param: int) -> str:
    return f"Received: {param}"
```

### 4. Object Creation

Create object instances using the service class:

```python
# Local object (in-process)
obj = MyService.create(local=True)

# Remote object (distributed)
obj = MyService.create(obj_id=123)
```

## Creating Your First OaaS Service

Let's create a comprehensive counter service with different return types:

```python
from oaas_sdk2_py import oaas, OaasObject, OaasConfig
from pydantic import BaseModel
from typing import Dict, List, Any

# Configure OaaS
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)

# Request models
class IncrementRequest(BaseModel):
    amount: int = 1

class SetValueRequest(BaseModel):
    value: int

# Response models
class CounterResponse(BaseModel):
    value: int
    message: str

@oaas.service("Counter", package="example")
class Counter(OaasObject):
    """A counter service demonstrating different return types."""
    
    # State variables
    count: int = 0
    history: List[str] = []
    metadata: Dict[str, Any] = {}
    
    @oaas.method()
    async def increment(self, req: IncrementRequest) -> int:
        """Increment counter and return new value as int."""
        self.count += req.amount
        self.history.append(f"Incremented by {req.amount}")
        return self.count
    
    @oaas.method()
    async def get_value(self) -> int:
        """Get current counter value as int."""
        return self.count
    
    @oaas.method()
    async def get_history(self) -> List[str]:
        """Get operation history as list."""
        return self.history.copy()
    
    @oaas.method()
    async def get_metadata(self) -> Dict[str, Any]:
        """Get counter metadata as dict."""
        return {
            "current_value": self.count,
            "operation_count": len(self.history),
            "last_operation": self.history[-1] if self.history else None
        }
    
    @oaas.method()
    async def is_positive(self) -> bool:
        """Check if counter is positive as bool."""
        return self.count > 0
    
    @oaas.method()
    async def get_status(self) -> str:
        """Get counter status as string."""
        if self.count == 0:
            return "zero"
        elif self.count > 0:
            return "positive"
        else:
            return "negative"
    
    @oaas.method()
    async def get_value_as_bytes(self) -> bytes:
        """Get counter value as bytes."""
        return str(self.count).encode('utf-8')
    
    @oaas.method()
    async def get_detailed_info(self) -> CounterResponse:
        """Get detailed counter info as Pydantic model."""
        return CounterResponse(
            value=self.count,
            message=f"Counter has been operated {len(self.history)} times"
        )
    
    @oaas.method()
    async def reset(self) -> bool:
        """Reset counter and return success status."""
        self.count = 0
        self.history.clear()
        self.metadata.clear()
        return True
    
    @oaas.method()
    async def batch_increment(self, amounts: List[int]) -> List[int]:
        """Increment by multiple amounts and return values after each increment."""
        results = []
        for amount in amounts:
            self.count += amount
            self.history.append(f"Batch incremented by {amount}")
            results.append(self.count)
        return results
```

### Usage Example

```python
async def main():
    # Create counter object
    counter = Counter.create(local=True)
    
    # Test different return types
    value = await counter.increment(IncrementRequest(amount=5))
    print(f"Counter value: {value} (type: {type(value)})")  # int
    
    history = await counter.get_history()
    print(f"History: {history} (type: {type(history)})")   # list
    
    metadata = await counter.get_metadata()
    print(f"Metadata: {metadata} (type: {type(metadata)})")  # dict
    
    is_positive = await counter.is_positive()
    print(f"Is positive: {is_positive} (type: {type(is_positive)})")  # bool
    
    status = await counter.get_status()
    print(f"Status: {status} (type: {type(status)})")  # str
    
    value_bytes = await counter.get_value_as_bytes()
    print(f"Value as bytes: {value_bytes} (type: {type(value_bytes)})")  # bytes
    
    detailed = await counter.get_detailed_info()
    print(f"Detailed: {detailed} (type: {type(detailed)})")  # CounterResponse
    
    batch_results = await counter.batch_increment([1, 2, 3])
    print(f"Batch results: {batch_results} (type: {type(batch_results)})")  # list
```

## Working with Objects

### Object Creation Patterns

```python
# Local object (stays in current process)
local_obj = MyService.create(local=True)

# Remote object with auto-generated ID
remote_obj = MyService.create()

# Remote object with specific ID
specific_obj = MyService.create(obj_id=123)

# Load existing object
existing_obj = MyService.load(obj_id=123)
```

### Object Lifecycle

```python
# Create and use
obj = MyService.create(obj_id=42)

# Perform operations
result = await obj.some_method()

# Delete object
await obj.delete()
```

## Type System

### Supported Types

The OaaS SDK natively supports these Python types:

#### Primitive Types
```python
@oaas.method()
async def return_int(self) -> int:
    return 42

@oaas.method()
async def return_float(self) -> float:
    return 3.14

@oaas.method()
async def return_bool(self) -> bool:
    return True

@oaas.method()
async def return_str(self) -> str:
    return "Hello, World!"
```

#### Collection Types
```python
@oaas.method()
async def return_list(self) -> List[int]:
    return [1, 2, 3, 4, 5]

@oaas.method()
async def return_dict(self) -> Dict[str, Any]:
    return {"key": "value", "count": 42}
```

#### Binary Data
```python
@oaas.method()
async def return_bytes(self) -> bytes:
    return b"Binary data"
```

#### Pydantic Models
```python
from pydantic import BaseModel

class UserData(BaseModel):
    id: int
    name: str
    email: str

@oaas.method()
async def return_model(self) -> UserData:
    return UserData(id=1, name="John", email="john@example.com")
```

### Method Parameters

**Important Note**: OaaS methods support only **one parameter** (plus `self`). For multiple values, use a dictionary or Pydantic model:

```python
# ❌ Multiple parameters NOT supported
@oaas.method()
async def process_data(self, count: int, rate: float, enabled: bool) -> Dict[str, Any]:
    # This will cause errors
    pass

# ✅ Use a dictionary for multiple simple values
@oaas.method()
async def process_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
    count = params["count"]
    rate = params["rate"]
    enabled = params["enabled"]
    return {"processed": True, "count": count}

# ✅ Use Pydantic model for structured data (RECOMMENDED)
class ProcessRequest(BaseModel):
    count: int
    rate: float
    enabled: bool
    message: str
    items: List[str]
    config: Dict[str, Any]
    data: bytes
    user: UserData

@oaas.method()
async def process_data(self, request: ProcessRequest) -> Dict[str, Any]:
    return {
        "processed": True,
        "count": request.count,
        "rate": request.rate,
        "enabled": request.enabled,
        "message": request.message,
        "items": request.items,
        "config": request.config,
        "data_size": len(request.data),
        "user_name": request.user.name
    }

# ✅ Single parameter methods work fine
@oaas.method()
async def increment(self, amount: int) -> int:
    return self.count + amount

@oaas.method()
async def get_status(self) -> str:
    return "running"
```

### Type Conversion

The SDK automatically handles type conversion:

```python
@oaas.method()
async def calculate_percentage(self, numerator: int, denominator: int) -> float:
    """Returns a float percentage."""
    return (numerator / denominator) * 100.0

@oaas.method()
async def format_result(self, value: float) -> str:
    """Converts float to formatted string."""
    return f"{value:.2f}%"

@oaas.method()
async def is_significant(self, percentage: float, threshold: float = 50.0) -> bool:
    """Returns boolean comparison result."""
    return percentage >= threshold
```

## Server and Agent Management

### Server Management

Servers host service definitions and handle gRPC requests:

```python
# Start gRPC server
oaas.start_server(port=8080)

# Check server status
if oaas.is_server_running():
    print("Server is running")
    info = oaas.get_server_info()
    print(f"Server info: {info}")

# Stop server
oaas.stop_server()
```

### Agent Management

Agents host specific object instances and handle background processing:

```python
# Start agent for a specific service and object
agent_id = await oaas.start_agent(MyService, obj_id=123)
print(f"Started agent: {agent_id}")

# List all running agents
agents = oaas.list_agents()
print(f"Running agents: {agents}")

# Stop specific agent
await oaas.stop_agent(agent_id)

# Stop all agents
await oaas.stop_all_agents()
```

### Server + Agent Example

```python
import asyncio
from oaas_sdk2_py import oaas, OaasConfig

async def run_service():
    # Configure OaaS
    config = OaasConfig(async_mode=True, mock_mode=False)
    oaas.configure(config)
    
    # Start server for external access
    oaas.start_server(port=8080)
    print("🚀 Server started on port 8080")
    
    # Start agent for background processing
    agent_id = await oaas.start_agent(Counter, obj_id=1)
    print(f"🤖 Agent started: {agent_id}")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(5)
            print(f"📊 Status - Server: {oaas.is_server_running()}, Agents: {len(oaas.list_agents())}")
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
    finally:
        # Cleanup
        await oaas.stop_all_agents()
        oaas.stop_server()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(run_service())
```

## Configuration

### OaasConfig Options

```python
from oaas_sdk2_py import OaasConfig

config = OaasConfig(
    # Runtime settings
    async_mode=True,                    # Enable async operations
    mock_mode=False,                    # Use real OaaS platform
    
    # Server settings  
    server_url="http://localhost:10000", # OaaS platform URL
    default_partition=0,                 # Default partition ID
    
    # Optional settings
    log_level="INFO",                   # Logging level
    timeout=30.0,                       # Request timeout
)

oaas.configure(config)
```

### Environment Variables

You can also configure using environment variables:

```bash
export OPRC_ODGM_URL="http://localhost:10000"
export OPRC_PARTITION_DEFAULT="0"
export LOG_LEVEL="INFO"
export HTTP_PORT="8080"
```

## Testing with Mock Mode

### Mock Configuration

Enable mock mode for testing without connecting to the OaaS platform:

```python
# Configure for testing
config = OaasConfig(mock_mode=True, async_mode=True)
oaas.configure(config)
```

### Unit Testing Example

```python
import pytest
from oaas_sdk2_py import oaas, OaasConfig

@pytest.fixture
def setup_mock():
    """Setup mock OaaS for testing."""
    config = OaasConfig(mock_mode=True, async_mode=True)
    oaas.configure(config)

@pytest.mark.asyncio
async def test_counter_increment(setup_mock):
    """Test counter increment functionality."""
    counter = Counter.create(local=True)
    
    # Test increment
    result = await counter.increment(IncrementRequest(amount=10))
    assert result == 10
    assert isinstance(result, int)
    
    # Test get_value
    value = await counter.get_value()
    assert value == 10
    assert isinstance(value, int)

@pytest.mark.asyncio
async def test_counter_types(setup_mock):
    """Test different return types."""
    counter = Counter.create(local=True)
    
    # Setup counter
    await counter.increment(IncrementRequest(amount=5))
    
    # Test different return types
    value = await counter.get_value()
    assert isinstance(value, int)
    
    history = await counter.get_history()
    assert isinstance(history, list)
    
    metadata = await counter.get_metadata()
    assert isinstance(metadata, dict)
    
    is_positive = await counter.is_positive()
    assert isinstance(is_positive, bool)
    assert is_positive is True
    
    status = await counter.get_status()
    assert isinstance(status, str)
    assert status == "positive"
    
    value_bytes = await counter.get_value_as_bytes()
    assert isinstance(value_bytes, bytes)
    
    detailed = await counter.get_detailed_info()
    assert isinstance(detailed, CounterResponse)

@pytest.mark.asyncio
async def test_counter_reset(setup_mock):
    """Test counter reset functionality."""
    counter = Counter.create(local=True)
    
    # Increment and verify
    await counter.increment(IncrementRequest(amount=15))
    assert await counter.get_value() == 15
    
    # Reset and verify
    reset_result = await counter.reset()
    assert reset_result is True
    assert isinstance(reset_result, bool)
    
    assert await counter.get_value() == 0
    assert await counter.get_history() == []
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_service_lifecycle(setup_mock):
    """Test complete service lifecycle."""
    # Create service
    counter = Counter.create(obj_id=42)
    
    # Perform operations
    for i in range(1, 6):
        result = await counter.increment(IncrementRequest(amount=i))
        assert result == sum(range(1, i+1))
    
    # Check final state
    final_value = await counter.get_value()
    assert final_value == 15  # 1+2+3+4+5
    
    history = await counter.get_history()
    assert len(history) == 5
    
    # Test batch operations
    batch_results = await counter.batch_increment([10, 20])
    assert batch_results == [25, 45]  # 15+10, 25+20
    
    # Verify persistence simulation
    metadata = await counter.get_metadata()
    assert metadata["current_value"] == 45
    assert metadata["operation_count"] == 7  # 5 + 2
```

## Advanced Topics

### Real-World System Monitoring Example

```python
import psutil
from oaas_sdk2_py import oaas, OaasObject

@oaas.service("ComputeDevice", package="monitoring")
class ComputeDevice(OaasObject):
    """A real system monitoring service."""
    
    metrics: Dict[str, Any] = {}
    
    @oaas.method(serve_with_agent=True)
    async def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=0.1)
    
    @oaas.method()
    async def get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        memory_info = psutil.virtual_memory()
        return memory_info.percent
    
    @oaas.method()
    async def get_process_count(self) -> int:
        """Get number of running processes."""
        return len(psutil.pids())
    
    @oaas.method()
    async def is_healthy(self, cpu_threshold: float = 80.0, memory_threshold: float = 90.0) -> bool:
        """Check if system is healthy based on thresholds."""
        cpu_ok = await self.get_cpu_usage() < cpu_threshold
        memory_ok = await self.get_memory_usage() < memory_threshold
        return cpu_ok and memory_ok
    
    @oaas.method(serve_with_agent=True)
    async def monitor_continuously(self, duration_seconds: int) -> Dict[str, Any]:
        """Monitor system for specified duration and return statistics."""
        cpu_samples = []
        memory_samples = []
        
        for _ in range(duration_seconds):
            cpu_usage = psutil.cpu_percent(interval=1.0)
            memory_info = psutil.virtual_memory()
            
            cpu_samples.append(cpu_usage)
            memory_samples.append(memory_info.percent)
        
        return {
            "avg_cpu_percent": sum(cpu_samples) / len(cpu_samples),
            "avg_memory_percent": sum(memory_samples) / len(memory_samples),
            "max_cpu_percent": max(cpu_samples),
            "max_memory_percent": max(memory_samples),
            "samples_taken": len(cpu_samples),
            "duration_seconds": duration_seconds
        }

# Usage
async def monitor_system():
    device = ComputeDevice.create(local=True)
    
    # Get current metrics
    cpu = await device.get_cpu_usage()
    memory = await device.get_memory_usage()
    processes = await device.get_process_count()
    healthy = await device.is_healthy()
    
    print(f"CPU: {cpu}%, Memory: {memory}%, Processes: {processes}, Healthy: {healthy}")
    
    # Monitor for 5 seconds
    stats = await device.monitor_continuously(5)
    print(f"5-second average: CPU {stats['avg_cpu_percent']:.1f}%, Memory {stats['avg_memory_percent']:.1f}%")
```

### Custom Error Handling

```python
from oaas_sdk2_py.simplified.errors import OaasError

@oaas.service("Calculator", package="math")
class Calculator(OaasObject):
    
    @oaas.method()
    async def divide(self, numerator: float, denominator: float) -> float:
        """Divide two numbers with error handling."""
        if denominator == 0:
            raise OaasError("Division by zero is not allowed")
        return numerator / denominator
    
    @oaas.method()
    async def safe_divide(self, numerator: float, denominator: float) -> Dict[str, Any]:
        """Safe division that returns error info."""
        try:
            result = await self.divide(numerator, denominator)
            return {"success": True, "result": result, "error": None}
        except OaasError as e:
            return {"success": False, "result": None, "error": str(e)}
```

### Performance Considerations

```python
@oaas.service("DataProcessor", package="performance")
class DataProcessor(OaasObject):
    
    cache: Dict[str, Any] = {}
    
    @oaas.method(serve_with_agent=True)
    async def expensive_computation(self, data_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Expensive computation with caching."""
        if not force_refresh and data_id in self.cache:
            return {"result": self.cache[data_id], "from_cache": True}
        
        # Simulate expensive computation
        import asyncio
        await asyncio.sleep(2)  # Simulated delay
        
        result = f"processed_{data_id}_{len(data_id)}"
        self.cache[data_id] = result
        
        return {"result": result, "from_cache": False}
    
    @oaas.method()
    async def clear_cache(self) -> bool:
        """Clear the computation cache."""
        self.cache.clear()
        return True
    
    @oaas.method()
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "cached_keys": list(self.cache.keys())
        }
```

## Best Practices

### 1. Service Design

**Keep services focused and cohesive:**
```python
# Good: Focused on user management
@oaas.service("UserManager", package="auth")
class UserManager(OaasObject):
    users: Dict[int, Dict[str, Any]] = {}
    
    @oaas.method()
    async def create_user(self, name: str, email: str) -> int:
        user_id = len(self.users) + 1
        self.users[user_id] = {"name": name, "email": email}
        return user_id
    
    @oaas.method()
    async def get_user(self, user_id: int) -> Dict[str, Any]:
        return self.users.get(user_id, {})

# Avoid: Mixed responsibilities
# Don't mix user management with file operations, email sending, etc.
```

### 2. Type Safety

**Use type hints consistently:**
```python
from typing import Optional, List, Dict, Any

@oaas.method()
async def process_users(self, user_ids: List[int], include_metadata: bool = False) -> Dict[str, Any]:
    """Process multiple users with optional metadata."""
    results = []
    for user_id in user_ids:
        user = await self.get_user(user_id)
        if user:
            if include_metadata:
                user["processed_at"] = time.time()
            results.append(user)
    
    return {
        "processed_count": len(results),
        "users": results,
        "include_metadata": include_metadata
    }
```

### 3. Error Handling

**Handle errors gracefully:**
```python
@oaas.method()
async def robust_operation(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform operation with comprehensive error handling."""
    try:
        # Validate input
        if not data or "id" not in data:
            return {"success": False, "error": "Invalid input data"}
        
        # Process data
        result = await self.process_data(data)
        
        return {"success": True, "result": result, "error": None}
        
    except Exception as e:
        # Log error and return structured response
        import logging
        logging.error(f"Operation failed: {e}")
        return {"success": False, "error": str(e), "result": None}
```

### 4. Resource Management

**Clean up resources properly:**
```python
@oaas.service("FileProcessor", package="io")
class FileProcessor(OaasObject):
    
    open_files: Dict[str, Any] = {}
    
    @oaas.method()
    async def open_file(self, filename: str) -> bool:
        """Open file for processing."""
        try:
            # In real implementation, you'd open actual files
            self.open_files[filename] = {"status": "open", "size": 1024}
            return True
        except Exception:
            return False
    
    @oaas.method()
    async def close_file(self, filename: str) -> bool:
        """Close file and clean up resources."""
        if filename in self.open_files:
            del self.open_files[filename]
            return True
        return False
    
    @oaas.method()
    async def cleanup_all(self) -> int:
        """Close all open files."""
        count = len(self.open_files)
        self.open_files.clear()
        return count
```

### 5. Testing Strategy

**Write comprehensive tests:**
```python
import pytest
from oaas_sdk2_py import oaas, OaasConfig

class TestUserManager:
    
    @pytest.fixture
    def setup_mock(self):
        config = OaasConfig(mock_mode=True, async_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_user_creation(self, setup_mock):
        """Test user creation functionality."""
        manager = UserManager.create(local=True)
        
        user_id = await manager.create_user("John Doe", "john@example.com")
        assert isinstance(user_id, int)
        assert user_id > 0
        
        user = await manager.get_user(user_id)
        assert user["name"] == "John Doe"
        assert user["email"] == "john@example.com"
    
    @pytest.mark.asyncio
    async def test_nonexistent_user(self, setup_mock):
        """Test getting nonexistent user."""
        manager = UserManager.create(local=True)
        
        user = await manager.get_user(999)
        assert user == {}
    
    @pytest.mark.asyncio
    async def test_multiple_users(self, setup_mock):
        """Test processing multiple users."""
        manager = UserManager.create(local=True)
        
        # Create test users
        user_ids = []
        for i in range(3):
            user_id = await manager.create_user(f"User{i}", f"user{i}@example.com")
            user_ids.append(user_id)
        
        # Process users
        result = await manager.process_users(user_ids, include_metadata=True)
        
        assert result["processed_count"] == 3
        assert len(result["users"]) == 3
        assert result["include_metadata"] is True
        
        # Check metadata was added
        for user in result["users"]:
            assert "processed_at" in user
```

This tutorial covers the essential aspects of the new OaaS SDK API. The simplified interface makes it much easier to define services, handle different data types, and manage server/agent lifecycles while maintaining all the powerful features of the OaaS platform.
