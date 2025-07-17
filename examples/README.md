# OaaS SDK Examples

This directory contains examples demonstrating how to use the OaaS SDK simplified interface.

## Examples Overview

### 1. HelloWorld (`helloworld/`)

A simple example demonstrating basic OaaS service creation and method invocation.

**Features:**
- Basic service definition with `@oaas.service` decorator
- Simple methods with `@oaas.method()` decorator
- Local object creation and method calls
- Server management (start/stop)

**Usage:**
```bash
cd helloworld
python -m helloworld          # Run server only
python -m helloworld agent    # Run with agent
python -m helloworld test     # Test locally
```

### 2. Device (`device/`)

A more complex example showing system monitoring and agent-based processing.

**Features:**
- System metrics monitoring using `psutil`
- Agent-based method execution with `serve_with_agent=True`
- Continuous monitoring and data collection
- Enhanced server and agent management

**Components:**
- `__main__.py`: Main device monitoring service
- `image.py`: Image processing service example

**Usage:**
```bash
cd device
python -m device              # Run server only
python -m device agent       # Run device agent
python -m device test        # Test locally
```

## API Migration

These examples have been updated to use the new simplified OaaS SDK interface:

### Old API → New API

```python
# Old API
from oaas_sdk2_py import Oparaca
from oaas_sdk2_py.engine import BaseObject

oaas = Oparaca(config=OprcConfig())
my_cls = oaas.new_cls(pkg="example", name="MyClass")

@my_cls
class MyClass(BaseObject):
    @my_cls.func()
    async def my_method(self, req: InvocationRequest):
        # ... implementation
        return InvocationResponse(payload=...)

# New API
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig

config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)

@oaas.service("MyClass", package="example")
class MyClass(OaasObject):
    @oaas.method()
    async def my_method(self, param: str) -> str:
        # ... implementation
        return result
```

### Key Benefits of New API

1. **Simplified Setup**: No need for complex configuration and class creation
2. **Type Safety**: Direct parameter and return type annotations
3. **Better Error Handling**: Built-in error classes and handling
4. **Agent Management**: Easy agent lifecycle management
5. **Server Management**: Simplified server start/stop operations

## Running Examples

### Prerequisites

```bash
# Install dependencies
pip install -e .
pip install psutil  # For device example
```

### Docker Support

Each example can also be run using Docker:

```bash
# Build and run with docker-compose
docker-compose up --build

# Or build individual examples
docker build -t oaas-helloworld .
docker run -p 8080:8080 oaas-helloworld
```

## Development

To add a new example:

1. Create a new directory under `examples/`
2. Add a `__main__.py` file with your service implementation
3. Use the simplified API patterns shown in existing examples
4. Add appropriate error handling and logging
5. Update this README with documentation

## Server and Agent Management

The new API provides comprehensive server and agent management:

```python
# Start server
oaas.start_server(port=8080)

# Start agent for a service
agent_id = await oaas.start_agent(MyService)

# List all agents
agents = oaas.list_agents()

# Stop specific agent
await oaas.stop_agent(agent_id)

# Stop all agents
await oaas.stop_all_agents()

# Stop server
oaas.stop_server()
```

## Configuration

The simplified API supports various configuration options:

```python
from oaas_sdk2_py.simplified import OaasConfig

config = OaasConfig(
    async_mode=True,           # Enable async operations
    mock_mode=False,           # Disable mock mode for real services
    auto_session=True,         # Enable automatic session management
    default_timeout=30.0,      # Default method timeout
    max_retries=3              # Maximum retry attempts
)

oaas.configure(config)
```