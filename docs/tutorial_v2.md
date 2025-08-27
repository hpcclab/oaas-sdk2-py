# OaaS SDK Tutorial (Updated)

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

Conceptually, the OaaS SDK helps you author classes that run on the OaaS platform. You write business logic; the platform handles persistence, distribution, concurrency, and scalability.

Key features:
- Simplified decorators (`@oaas.service`, `@oaas.method`, etc.)
- Automatic state management on typed attributes
- Native support for Python primitives, collections, Pydantic models
- Server (gRPC) and agents managed independently
- Async/sync support
- Event triggers on data/functions
- Mock mode for tests

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

Use `OaasConfig` (Pydantic BaseSettings) for runtime settings:

```python
from oaas_sdk2_py import oaas, OaasConfig

config = OaasConfig(
    async_mode=True,           # Enable async operations
    mock_mode=False,           # Use real platform
    oprc_partition_default=0,  # Default partition
    oprc_zenoh_peers="tcp/localhost:7447",  # Optional peers
    auto_commit=True,
)

oaas.configure(config)
```

### 2. Service Definition

```python
@oaas.service("MyService", package="my_package")
class MyService(OaasObject):
    pass
```

### 3. Method Exposure

```python
@oaas.method()
async def my_method(self, param: int) -> str:
    return f"Received: {param}"
```

### 4. Object Creation

```python
# Local object (in-process)
obj = MyService.create(local=True)

# Remote object (distributed)
obj = MyService.create(obj_id=123)
```

## Creating Your First OaaS Service

```python
from oaas_sdk2_py import oaas, OaasObject, OaasConfig
from pydantic import BaseModel
from typing import Dict, List, Any

config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)

class IncrementRequest(BaseModel):
    amount: int = 1

class SetValueRequest(BaseModel):
    value: int

class CounterResponse(BaseModel):
    value: int
    message: str

@oaas.service("Counter", package="example")
class Counter(OaasObject):
    count: int = 0
    history: List[str] = []
    metadata: Dict[str, Any] = {}
    
    @oaas.method()
    async def increment(self, req: IncrementRequest) -> int:
        self.count += req.amount
        self.history.append(f"Incremented by {req.amount}")
        return self.count
    
    @oaas.method()
    async def get_value(self) -> int:
        return self.count
    
    @oaas.method()
    async def get_history(self) -> List[str]:
        return self.history.copy()
    
    @oaas.method()
    async def get_metadata(self) -> Dict[str, Any]:
        return {
            "current_value": self.count,
            "operation_count": len(self.history),
            "last_operation": self.history[-1] if self.history else None,
        }
    
    @oaas.method()
    async def is_positive(self) -> bool:
        return self.count > 0
    
    @oaas.method()
    async def get_status(self) -> str:
        if self.count == 0:
            return "zero"
        return "positive" if self.count > 0 else "negative"
    
    @oaas.method()
    async def get_value_as_bytes(self) -> bytes:
        return str(self.count).encode("utf-8")
    
    @oaas.method()
    async def get_detailed_info(self) -> CounterResponse:
        return CounterResponse(value=self.count, message=f"Counter has been operated {len(self.history)} times")
    
    @oaas.method()
    async def reset(self) -> bool:
        self.count = 0
        self.history.clear()
        self.metadata.clear()
        return True
    
    @oaas.method()
    async def batch_increment(self, amounts: List[int]) -> List[int]:
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
    counter = Counter.create(local=True)
    value = await counter.increment(IncrementRequest(amount=5))
    print(f"Counter value: {value}")
    print(await counter.get_history())
```

## Working with Objects

### Object Creation Patterns

```python
local_obj = MyService.create(local=True)   # Local object
remote_obj = MyService.create()            # Remote object (auto id)
specific_obj = MyService.create(obj_id=123)
existing_obj = MyService.load(obj_id=123)  # Load
```

### Object Lifecycle

```python
obj = MyService.create(obj_id=42)
result = await obj.some_method()
obj.delete()  # delete() is synchronous
```

## Type System

### Supported Types (examples)

```python
@oaas.method()
async def return_int(self) -> int: return 42

@oaas.method()
async def return_float(self) -> float: return 3.14

@oaas.method()
async def return_bool(self) -> bool: return True

@oaas.method()
async def return_str(self) -> str: return "Hello"

@oaas.method()
async def return_list(self) -> List[int]: return [1,2,3]

@oaas.method()
async def return_dict(self) -> Dict[str, Any]: return {"k": "v"}

@oaas.method()
async def return_bytes(self) -> bytes: return b"Binary"

from pydantic import BaseModel
class UserData(BaseModel): id: int; name: str; email: str
@oaas.method()
async def return_model(self) -> UserData: return UserData(id=1, name="John", email="john@example.com")
```

### Method Parameters

- Recommended: one parameter (+ self). For multiple values use a Pydantic model or a dict.
- Advanced: a second parameter of type `InvocationRequest` or `ObjectInvocationRequest` is supported to access request metadata/options.

```python
# Good: single parameter
@oaas.method()
async def increment(self, amount: int) -> int:
    return self.count + amount

# Good: use a Pydantic model
from pydantic import BaseModel
class ProcessRequest(BaseModel): count: int; rate: float; enabled: bool
@oaas.method()
async def process(self, req: ProcessRequest) -> float:
    return req.count * req.rate if req.enabled else 0.0

# Good: include request as second param (advanced)
from oprc_py import InvocationRequest
@oaas.method()
async def process_with_req(self, req_model: ProcessRequest, req: InvocationRequest) -> float:
    return req_model.count * req_model.rate
```

### Type Conversion

Use models instead of multiple scalar parameters:

```python
class FractionRequest(BaseModel): numerator: int; denominator: int
@oaas.method()
async def calculate_percentage(self, data: FractionRequest) -> float:
    return (data.numerator / data.denominator) * 100.0

class ThresholdRequest(BaseModel): percentage: float; threshold: float = 50.0
@oaas.method()
async def is_significant(self, data: ThresholdRequest) -> bool:
    return data.percentage >= data.threshold
```

## Server and Agent Management

### Server Management

```python
# Start gRPC server
oaas.start_server(port=8080)

# Status
if oaas.is_server_running():
    print("Server is running")
    print(oaas.get_server_info())

# Stop
oaas.stop_server()
```

### Agent Management

```python
# Start agent for a specific service/object
agent_id = await oaas.start_agent(MyService, obj_id=123)
print("Agents:", oaas.list_agents())  # dict of agent info

# Stop specific agent
await oaas.stop_agent(agent_id)

# Stop all
await oaas.stop_all_agents()
```

### Server + Agent Example

```python
import asyncio
from oaas_sdk2_py import oaas, OaasConfig

async def run_service():
    oaas.configure(OaasConfig(async_mode=True, mock_mode=False))
    oaas.start_server(port=8080)
    agent_id = await oaas.start_agent(Counter, obj_id=1)
    try:
        while True:
            await asyncio.sleep(5)
            print({"server": oaas.is_server_running(), "agents": len(oaas.list_agents())})
    finally:
        await oaas.stop_all_agents()
        oaas.stop_server()

if __name__ == "__main__":
    asyncio.run(run_service())
```

## Configuration

### OaasConfig Options (current)

```python
from oaas_sdk2_py import OaasConfig

config = OaasConfig(
    async_mode=True,
    mock_mode=False,
    oprc_partition_default=0,
    oprc_zenoh_peers=None,
    auto_commit=True,
)
```

### Environment Variables

`OaasConfig` fields map to env vars automatically (Pydantic BaseSettings):

| Env Var | Field | Example |
| --- | --- | --- |
| `OPRC_ZENOH_PEERS` | `oprc_zenoh_peers` | `tcp/localhost:7447` |
| `OPRC_PARTITION_DEFAULT` | `oprc_partition_default` | `0` |
| `MOCK_MODE` | `mock_mode` | `true` |
| `ASYNC_MODE` | `async_mode` | `true` |
| `AUTO_COMMIT` | `auto_commit` | `true` |

## Testing with Mock Mode

```python
import pytest
from oaas_sdk2_py import oaas, OaasConfig

@pytest.fixture
def setup_mock():
    oaas.configure(OaasConfig(mock_mode=True, async_mode=True))

@pytest.mark.asyncio
async def test_counter_increment(setup_mock):
    counter = Counter.create(local=True)
    result = await counter.increment(IncrementRequest(amount=10))
    assert result == 10
    assert isinstance(result, int)
```

## Advanced Topics

### Real-World System Monitoring Example

```python
import psutil
from typing import Dict, Any
from oaas_sdk2_py import oaas, OaasObject
from pydantic import BaseModel

@oaas.service("ComputeDevice", package="monitoring")
class ComputeDevice(OaasObject):
    metrics: Dict[str, Any] = {}
    
    @oaas.method(serve_with_agent=True)
    async def get_cpu_usage(self) -> float:
        return psutil.cpu_percent(interval=0.1)
    
    @oaas.method()
    async def get_memory_usage(self) -> float:
        return psutil.virtual_memory().percent
    
    @oaas.method()
    async def get_process_count(self) -> int:
        return len(psutil.pids())

class HealthCheck(BaseModel):
    cpu_threshold: float = 80.0
    memory_threshold: float = 90.0

@oaas.service("HealthMonitor", package="monitoring")
class HealthMonitor(OaasObject):
    @oaas.method()
    async def is_healthy(self, cfg: HealthCheck) -> bool:
        device = ComputeDevice.create(local=True)
        cpu_ok = await device.get_cpu_usage() < cfg.cpu_threshold
        mem_ok = await device.get_memory_usage() < cfg.memory_threshold
        return cpu_ok and mem_ok
    
    @oaas.method(serve_with_agent=True)
    async def monitor_continuously(self, duration_seconds: int) -> Dict[str, Any]:
        import asyncio
        cpu_samples = []
        mem_samples = []
        for _ in range(duration_seconds):
            cpu_samples.append(await ComputeDevice.create(local=True).get_cpu_usage())
            mem_samples.append(await ComputeDevice.create(local=True).get_memory_usage())
            await asyncio.sleep(1)
        return {
            "avg_cpu_percent": sum(cpu_samples)/len(cpu_samples),
            "avg_memory_percent": sum(mem_samples)/len(mem_samples),
            "max_cpu_percent": max(cpu_samples),
            "max_memory_percent": max(mem_samples),
            "samples_taken": len(cpu_samples),
            "duration_seconds": duration_seconds,
        }
```

### Custom Error Handling

```python
from pydantic import BaseModel
from typing import Dict, Any
from oaas_sdk2_py.simplified.errors import OaasError

class DivideRequest(BaseModel): numerator: float; denominator: float

@oaas.service("Calculator", package="math")
class Calculator(OaasObject):
    @oaas.method()
    async def divide(self, data: DivideRequest) -> float:
        if data.denominator == 0:
            raise OaasError("Division by zero is not allowed")
        return data.numerator / data.denominator
    
    @oaas.method()
    async def safe_divide(self, data: DivideRequest) -> Dict[str, Any]:
        try:
            return {"success": True, "result": await self.divide(data), "error": None}
        except OaasError as e:
            return {"success": False, "result": None, "error": str(e)}
```

### Performance Considerations

```python
from pydantic import BaseModel
from typing import Dict, Any

class ExpensiveReq(BaseModel): data_id: str; force_refresh: bool = False

@oaas.service("DataProcessor", package="performance")
class DataProcessor(OaasObject):
    cache: Dict[str, Any] = {}
    
    @oaas.method(serve_with_agent=True)
    async def expensive_computation(self, data: ExpensiveReq) -> Dict[str, Any]:
        if not data.force_refresh and data.data_id in self.cache:
            return {"result": self.cache[data.data_id], "from_cache": True}
        import asyncio
        await asyncio.sleep(2)
        result = f"processed_{data.data_id}_{len(data.data_id)}"
        self.cache[data.data_id] = result
        return {"result": result, "from_cache": False}
    
    @oaas.method()
    async def clear_cache(self) -> bool:
        self.cache.clear(); return True
    
    @oaas.method()
    async def get_cache_stats(self) -> Dict[str, Any]:
        return {"cache_size": len(self.cache), "cached_keys": list(self.cache.keys())}
```

## Best Practices

- Keep services cohesive and focused.
- Use type hints and Pydantic models for safety and clarity.
- Prefer a single parameter; use models/dicts for multiple inputs.
- Handle errors gracefully; return structured responses where helpful.
- Clean up resources and provide maintenance methods (e.g., `cleanup_all`).
- Write comprehensive tests with mock mode enabled.

This updated tutorial aligns with the current SDK implementation (config fields, method parameter rules, env vars, and APIs) and fixes earlier inconsistencies (e.g., synchronous `delete()`, avoiding multiple scalar params).
