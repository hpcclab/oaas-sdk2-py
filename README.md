# OaaS-SDK2

This library helps you develop a runtime that can be run in a Object as a Service (OaaS) serverless platform. For more information on the OaaS model, visit [https://github.com/hpcclab/OaaS](https://github.com/hpcclab/OaaS).

## Table of Contents
- [Documentation](#documentation)
- [Installation](#installation)
- [Features](#features)
- [Quick Start](#quick-start)
- [Examples](#examples)
- [API Overview](#api-overview)
- [Build the project](#build-the-project)

## Documentation

For a comprehensive guide and API reference, please see the `docs` directory:

- **[Tutorial](docs/tutorial.md)**: A step-by-step guide to getting started with the OaaS SDK.
- **[API Reference](docs/reference.md)**: A detailed reference of all classes, methods, and functions.

## Installation

To install `oaas-sdk2-py`, you can use pip:

```bash
pip install oaas-sdk2-py
```
Or, if you are using `uv`:
```bash
# For adding/installing packages with uv, the command is 'uv pip install'
uv add oaas-sdk2-py
```

## Features

- **Simplified API**: Easy-to-use decorators and type-safe method definitions
- **Type Safety**: Full Pydantic model support with automatic validation
- **Async/Sync Support**: Built with `async/await` for non-blocking operations
- **Data Persistence**: Object data is persisted and can be retrieved
- **Remote Procedure Calls (RPC)**: Invoke methods on objects remotely
- **Mocking Framework**: Includes a mocking utility for testing your OaaS applications
- **Rust-Powered Core**: High-performance core components written in Rust for speed and efficiency

## Quick Start

### Basic Service Definition

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

# Define your service
@oaas.service("Greeter", package="example")
class Greeter(OaasObject):
    counter: int = 0
    
    @oaas.method()
    async def greet(self, req: GreetRequest) -> GreetResponse:
        return GreetResponse(message=f"Hello, {req.name}!")
    
    @oaas.method()
    async def count_greetings(self) -> int:
        self.counter += 1
        return self.counter
    
    @oaas.method()
    async def is_popular(self, threshold: int = 10) -> bool:
        return self.counter > threshold

# Usage
async def main():
    # Create and use locally
    greeter = Greeter.create(local=True)
    
    # Test with different types
    response = await greeter.greet(GreetRequest(name="World"))
    count = await greeter.count_greetings()  # Returns int
    popular = await greeter.is_popular(5)     # Returns bool
    
    print(f"{response.message} (Count: {count}, Popular: {popular})")
```

### Server & Agent Management

```python
# Start gRPC server (for external access)
oaas.start_server(port=8080)

# Start agent (for background processing)
agent_id = await oaas.start_agent(Greeter, obj_id=123)

# Check status
print(f"Server running: {oaas.is_server_running()}")
print(f"Agents: {oaas.list_agents()}")

# Cleanup
await oaas.stop_agent(agent_id)
oaas.stop_server()
```


## API Overview

### Core Components

- **`@oaas.service`**: Decorator to define OaaS services
- **`@oaas.method`**: Decorator to expose methods as RPC endpoints
- **`OaasObject`**: Base class for all OaaS objects with persistence
- **`OaasConfig`**: Configuration for OaaS runtime

### Supported Types

The SDK natively supports these Python types:
- **Primitives**: `int`, `float`, `bool`, `str`
- **Collections**: `list`, `dict`
- **Binary**: `bytes`
- **Models**: Pydantic `BaseModel` classes

## Examples

### System Monitoring Service

```python
import psutil
from oaas_sdk2_py import oaas, OaasObject

@oaas.service("ComputeDevice", package="monitoring")
class ComputeDevice(OaasObject):
    metrics: dict = {}

    @oaas.method()
    async def get_cpu_usage(self) -> float:
        """Get current CPU usage as a percentage."""
        return psutil.cpu_percent(interval=0.1)

    @oaas.method()
    async def get_process_count(self) -> int:
        """Get number of running processes."""
        return len(psutil.pids())

    @oaas.method()
    async def is_healthy(self, cpu_threshold: float = 80.0) -> bool:
        """Check if system is healthy."""
        cpu_usage = await self.get_cpu_usage()
        return cpu_usage < cpu_threshold

    @oaas.method()
    async def monitor_continuously(self, duration: int) -> dict:
        """Monitor for specified duration and return metrics."""
        samples = []
        for _ in range(duration):
            cpu = psutil.cpu_percent(interval=1.0)
            samples.append(cpu)
        
        return {
            "avg_cpu": sum(samples) / len(samples),
            "samples": len(samples),
            "duration": duration
        }

# Usage
device = ComputeDevice.create(local=True)
cpu_usage = await device.get_cpu_usage()      # Returns float
process_count = await device.get_process_count()  # Returns int
is_healthy = await device.is_healthy(75.0)    # Returns bool
metrics = await device.monitor_continuously(5)  # Returns dict
```

### Counter Service with State

```python
from oaas_sdk2_py import oaas, OaasObject

@oaas.service("Counter", package="example")
class Counter(OaasObject):
    count: int = 0
    history: list = []

    @oaas.method()
    async def increment(self, amount: int = 1) -> int:
        """Increment counter by amount."""
        self.count += amount
        self.history.append(f"Added {amount}")
        return self.count

    @oaas.method()
    async def get_value(self) -> int:
        """Get current counter value."""
        return self.count

    @oaas.method()
    async def get_history(self) -> list:
        """Get operation history."""
        return self.history

    @oaas.method()
    async def reset(self) -> bool:
        """Reset counter to zero."""
        self.count = 0
        self.history.clear()
        return True

# Usage
counter = Counter.create(local=True)
value = await counter.increment(5)    # Returns int: 5
current = await counter.get_value()   # Returns int: 5
history = await counter.get_history() # Returns list: ["Added 5"]
reset = await counter.reset()         # Returns bool: True
```

### Testing with Mock Mode

```python
import pytest
from oaas_sdk2_py import oaas, OaasConfig

# Configure for testing
@pytest.fixture
def setup_mock():
    config = OaasConfig(mock_mode=True, async_mode=True)
    oaas.configure(config)

@pytest.mark.asyncio
async def test_counter_service(setup_mock):
    counter = Counter.create(local=True)
    
    # Test increment
    result = await counter.increment(10)
    assert result == 10
    assert isinstance(result, int)
    
    # Test history
    history = await counter.get_history()
    assert history == ["Added 10"]
    assert isinstance(history, list)
    
    # Test reset
    reset_result = await counter.reset()
    assert reset_result is True
    assert isinstance(reset_result, bool)
```

### Running as Server/Agent

Create a main module to run your service:

```python
# main.py
import asyncio
import sys
from oaas_sdk2_py import oaas, OaasConfig

async def run_server():
    """Run gRPC server for external access."""
    config = OaasConfig(async_mode=True, mock_mode=False)
    oaas.configure(config)
    
    oaas.start_server(port=8080)
    print("🚀 Server running on port 8080")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
    finally:
        oaas.stop_server()

async def run_agent():
    """Run agent for background processing."""
    config = OaasConfig(async_mode=True, mock_mode=False)
    oaas.configure(config)
    
    # Start both server and agent
    oaas.start_server(port=8080)
    agent_id = await oaas.start_agent(Counter, obj_id=1)
    print(f"🤖 Agent started: {agent_id}")
    
    try:
        while True:
            await asyncio.sleep(5)
            print(f"📊 Server: {oaas.is_server_running()}, Agents: {len(oaas.list_agents())}")
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
    finally:
        await oaas.stop_all_agents()
        oaas.stop_server()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "agent":
        asyncio.run(run_agent())
    else:
        asyncio.run(run_server())
```

Run with:
```bash
# Server only
python main.py

# Server + Agent
python main.py agent
```


## Run on OaaS

### Prerequisites
- cargo (install via [rust](https://rustup.rs/))
- oprc-cli `cargo install --git https://github.com/pawissanutt/oaas-rs.git oprc-cli`
- OaaS Platform (Oparaca)
    - Kubernetes Cluster (e.g., k3d with Docker runtime)

### Deployment

1. **Package your service**:
```bash
# Generate package metadata
python -m your_service gen

# Build Docker image
docker build -t your-service:latest .
```

2. **Deploy to OaaS platform**:
```bash
# Deploy service definition
oprc-cli deploy service your-service.yaml

# Create object instances
oprc-cli create object your-service/YourClass --id 123
```

3. **Monitor and manage**:
```bash
# Check status
oprc-cli list objects
oprc-cli get object your-service/YourClass/123

# Scale agents
oprc-cli scale agents your-service/YourClass --replicas 3
```


## Build the project

You don't need to follow this guide unless you want to build the Python package on your own.

### Prerequisites
- Python
- cargo (install via [rust](https://rustup.rs/))
- [uv](https://github.com/astral-sh/uv) (python package manager)

### Build

```bash
uv sync
uv build
```


