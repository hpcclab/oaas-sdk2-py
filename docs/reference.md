# OaaS SDK API Reference (Updated)

## Table of Contents
1. [Simplified Interface](#simplified-interface)
2. [Core Decorators](#core-decorators)
3. [Base Classes](#base-classes)
4. [Configuration](#configuration)
5. [Type System](#type-system)
6. [Server and Agent Management](#server-and-agent-management)
7. [Error Handling](#error-handling)
8. [Performance Monitoring](#performance-monitoring)
9. [Legacy API](#legacy-api)
10. [Environment Variables](#environment-variables)

> This document reflects the current implementation in `oaas_sdk2_py.simplified.*` and `oaas_sdk2_py.model`. It corrects and extends the previous reference to match actual code behavior.

---

## Simplified Interface

The OaaS SDK provides a simplified interface through the global `oaas` object and decorators.

### Module Import

```python
from oaas_sdk2_py import oaas, OaasObject, OaasConfig, ref, ObjectRef  # identity-based references
```

### Global Configuration

Function: `oaas.configure(config: OaasConfig) -> None`

```python
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)
```

You can later inspect system health and info:

```python
info = oaas.get_system_info()
health = oaas.health_check()
```

---

## Core Decorators

### @oaas.service

Decorator: `@oaas.service(name: str, package: str = "default")`

Registers a class as an OaaS service and wires enhanced decorators into the legacy runtime under the hood.

Parameters:
- name (str): Service name
- package (str): Package name (default: "default")

Usage:
```python
@oaas.service("MyService", package="example")
class MyService(OaasObject):
    pass
```

### @oaas.method

Decorator: `@oaas.method(name: str = "", stateless: bool = False, strict: bool = False, serve_with_agent: bool = False, timeout: float | None = None, retry_count: int = 0, retry_delay: float = 1.0)`

Exposes a method as an RPC endpoint with retries, optional timeout, and agent support.

- name: Override method name
- stateless: Mark method as not mutating object state
- strict: Enable strict Pydantic validation for BaseModel returns
- serve_with_agent: Allow method to be executed by an agent
- timeout: Timeout (seconds) for a single attempt
- retry_count / retry_delay: Retry policy on error/timeout

Usage:
```python
@oaas.method()
async def my_method(self, param: int) -> str:
    return f"Result: {param}"

@oaas.method(name="custom_name", serve_with_agent=True, timeout=5.0, retry_count=2)
async def background_task(self) -> bool:
    return True
```

### @oaas.getter and @oaas.setter (Accessor Methods)

Accessors provide typed read/write methods bound to persisted fields. They are async, validated at registration, and behave like normal methods for callers. Accessors are not exported as standalone RPC functions; they remain methods on the service class and do not appear in the package "functions" list.

Why: avoid redundant RPC for pure data access. A method incurs an RPC call that then reads/writes state and returns; an accessor performs the data operation directly.

Signatures:
- `@oaas.getter(field: str | None = None, *, projection: list[str] | None = None)`
- `@oaas.setter(field: str | None = None)`

Contracts:
- Getter: async; only `self`; must have a return annotation matching the field type (or projected sub-type). No side effects.
- Setter: async; `self` plus a single `value` parameter; parameter type must match the field type. Returns updated value or `None` if annotated as `None`.

Field inference:
- Getter: `get_<field>` → `<field>`; else method name equals field name.
- Setter: `set_<field>` → `<field>`; else method name equals field name.
Field must be type-annotated on the class (MRO-aware). Ambiguity or failure raises `TypeError`.

Projection (getter only):
- `projection=["a", "b"]` traverses attribute or dict keys after deserialization. Invalid paths raise `ValueError`.

Usage:
```python
from oaas_sdk2_py import oaas, OaasObject

@oaas.service("Counter", package="example")
class Counter(OaasObject):
    count: int = 0

    @oaas.getter()  # inferred from method name: get_count -> count
    async def get_count(self) -> int:
        # Body is not used by the runtime; recommended to reflect semantics.
        return self.count

    @oaas.setter()  # inferred from method name: set_count -> count
    async def set_count(self, value: int) -> int:
        self.count = value
        return self.count

    @oaas.getter("profile", projection=["address", "city"])
    async def get_city(self) -> str:
        # Returns projected sub-value from a structured field
        ...
```

Notes:
- Accessors are metadata-driven; they do not get exported as RPC functions.
- They work alongside normal `@oaas.method` methods.
- In local/mock mode, state semantics follow in-memory behavior.
- Accessors are callable through ObjectRef proxies; getters read directly from storage, setters write through to storage.

When to choose accessors vs methods

Prefer accessors for simple persisted reads/writes:
- Minimize public RPC surface: accessors stay as class methods and won’t appear in the exported function list.
- Strong coupling to state: validated against field annotations, with optional name-based inference.
- Predictable behavior: getters should be side-effect free; setters only write; easy to reason about.
- Projections: return just a path of interest from structured fields without extra plumbing.
- Cleaner docs/UX: keep the “real” RPC methods list focused on domain operations.

Use `@oaas.method` when the operation:
- Combines multiple fields, interacts with external systems, or has complex logic.
- Needs custom validation, retries, timeouts, or agent execution.

Example (before → after):

```python
# Before: exported RPC function
@oaas.method()
async def get_count(self) -> int:
    return self.count

# After: accessor (not exported as RPC function)
@oaas.getter("count")
async def get_count(self) -> int:
    ...
```

### @oaas.function

Decorator: `@oaas.function(name: str = "", serve_with_agent: bool = False, timeout: float | None = None, retry_count: int = 0, retry_delay: float = 1.0)`

Registers a stateless callable on the class that does not require instance state.

```python
@oaas.function()
def ping() -> str:
    return "pong"
```

### @oaas.constructor

Decorator: `@oaas.constructor(validate: bool = True, timeout: float | None = None, error_handling: str = "strict")`

Provides custom initialization logic integrated with `create()`.

```python
@oaas.constructor()
def initialize(self, value: int):
    self.value = value
```

Behavior and usage:
- Constructors are regular methods decorated for clarity and metrics; they are not auto-invoked by `create()`.
- Call them explicitly after `create()` on the instance, e.g., `obj = MyService.create(); await obj.initialize(42)`.
- They can be invoked at any time to re-initialize or adjust state; typical usage is immediately after creation.
- They are exported like normal methods during registration.

---

## Base Classes

### OaasObject

Module: `oaas_sdk2_py.simplified.objects`

Base class for all OaaS service objects with automatic state management.

Class Methods:
- `create(obj_id: int | None = None, local: bool | None = None) -> Self`
- `load(obj_id: int) -> Self`
- `start_agent(obj_id: int | None = None, partition_id: int | None = None, loop=None) -> Awaitable[str]` (classmethod)
- `stop_agent(obj_id: int | None = None) -> Awaitable[None]` (classmethod)

Instance Methods:
- `delete() -> None`
- `commit() -> None`
- `commit_async() -> Awaitable[None]`
- `start_instance_agent(loop=None) -> Awaitable[str]`
- `stop_instance_agent() -> Awaitable[None]`
- `as_ref() -> ObjectRef` — return an identity-based proxy to this object for remote calls and direct accessor IO.

State Management:

Type-annotated attributes become persistent fields automatically.

```python
@oaas.service("Counter", package="example")
class Counter(OaasObject):
    count: int = 0
    history: list[str] = []

    @oaas.method()
    async def increment(self, amount: int = 1) -> int:
        self.count += amount
        self.history.append(f"Added {amount}")
        return self.count
```

---

## Configuration

### OaasConfig

Module: `oaas_sdk2_py.simplified.config` (re-exports `oaas_sdk2_py.config.OaasConfig`).

Attributes (current implementation):

| Attribute | Type | Default | Description |
| --- | --- | --- | --- |
| `oprc_zenoh_peers` | `str | None` | `None` | Comma-separated Zenoh peers |
| `oprc_partition_default` | `int` | `0` | Default partition ID |
| `mock_mode` | `bool` | `False` | Use mock mode for testing |
| `async_mode` | `bool` | `True` | Enable async operations |
| `auto_commit` | `bool` | `True` | Auto-commit session changes |
| `batch_size` | `int` | `100` | Deprecated; retained for compatibility |

Usage:
```python
config = OaasConfig(
    async_mode=True,
    mock_mode=False,
    oprc_partition_default=0,
    oprc_zenoh_peers="tcp/localhost:7447",
    auto_commit=True,
)
oaas.configure(config)
```

---

## Type System

### Unified Serialization System

Unified serializer for both RPC and state management with validation and performance metrics.

Supported types include:
- Primitive: `int`, `float`, `bool`, `str`, `bytes`
- Collections: `List[T]`, `Dict[K, V]`, `Tuple[...]`, `Set[T]`
- Advanced: `Optional[T]`, `Union[...]`, `datetime`, `UUID`
- Structured: Pydantic `BaseModel`, and custom classes with serializable attributes

Method parameter rules:
- Current framework supports a single parameter (in addition to `self`). If you need multiple inputs today, wrap them in a Pydantic model or a dict. A second parameter may be used for `InvocationRequest`/`ObjectInvocationRequest` to access metadata.
- A proposal to support true multi-argument methods/constructors is drafted under `docs/proposals/multi_argument_rpc_and_constructor_proposal.md`.

Examples:
```python
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from uuid import uuid4, UUID
from pydantic import BaseModel

class UserData(BaseModel):
    name: str
    age: int
    email: Optional[str] = None

@oaas.service("DataProcessor", package="example")
class DataProcessor(OaasObject):
    @oaas.method()
    async def process_numbers(self, numbers: List[int]) -> float:
        return sum(numbers) / len(numbers) if numbers else 0.0

    @oaas.method()
    async def process_user_data(self, user: UserData) -> Dict[str, Any]:
        return {
            "processed_at": datetime.now(),
            "user_id": str(uuid4()),
            "name": user.name,
            "age_category": "adult" if user.age >= 18 else "minor",
        }

    @oaas.method()
    async def flexible_input(self, data: Union[int, str]) -> str:
        return f"Number: {data}" if isinstance(data, int) else f"Text: {data}"

    @oaas.method()
    async def optional_parameter(self, value: Optional[str]) -> bool:
        return value is not None
```

Serialization helpers:
```python
from oaas_sdk2_py.simplified.serialization import UnifiedSerializer
serializer = UnifiedSerializer()

# Serialize/deserialize
b = serializer.serialize({"a": 1}, dict)
obj = serializer.deserialize(b, dict)

# Type conversion
n = serializer.convert_value("123", int)  # 123
```

### Service references (identity-based)

Fields annotated with a service type (e.g., `Profile`) or `Optional[Profile]` are serialized by identity, not by value. This enables persistent object references across services.

Accepted assignment forms for a service-typed field:
- a live instance of the service (auto-converted to identity)
- a proxy from `as_ref()`
- an identity via `ref(cls_id, object_id, partition_id=0)`
- a tuple `(cls_id, partition_id, object_id)`
- a dict `{ "cls_id": str, "object_id": int, "partition_id": int }`

Creating and using refs:
```python
from typing import Optional
from oaas_sdk2_py import oaas, OaasObject, ref

@oaas.service("Profile", package="ref")
class Profile(OaasObject):
    email: str
    @oaas.getter("email")
    async def get_email(self) -> str: ...

@oaas.service("User", package="ref")
class User(OaasObject):
    profile: Optional[Profile] = None  # identity-based reference

    @oaas.method()
    async def read_profile_email(self) -> Optional[str]:
        return None if self.profile is None else await self.profile.get_email()

prof = Profile.create(); prof.email = "a@example.com"
user = User.create()
user.profile = prof           # instance → identity
user.profile = prof.as_ref()  # explicit proxy
user.profile = ref(prof.meta.cls_id, prof.object_id, prof.meta.partition_id)  # identity helper
```

Proxy behavior (ObjectRef):
- For normal `@oaas.method` methods, calls are forwarded via RPC.
- For accessors (`@oaas.getter/@oaas.setter`), calls perform direct persisted reads/writes through the data manager.
- Proxies compare equal and hash by identity `(cls_id, partition_id, object_id)`.
- Optional/Union annotations (e.g., `Optional[Profile]` or `Profile | None`) are fully supported for state and params.

---

## Server and Agent Management

### Server Management

The server hosts gRPC endpoints for external clients. It is independent from agents.

Functions (methods on the global `oaas` object):
- `oaas.start_server(port: int = 8080, loop=None, async_mode: bool | None = None) -> None`
- `oaas.stop_server() -> None`
- `oaas.is_server_running() -> bool`
- `oaas.get_server_info() -> Dict[str, Any]`
- `oaas.restart_server(port: int | None = None, loop=None, async_mode: bool | None = None) -> None`

### Agent Management

Agents execute methods marked with `serve_with_agent=True` for a specific object instance. They operate without the server if desired.

Functions:
- `await oaas.start_agent(service_class, obj_id: int | None = None, partition_id: int | None = None, loop=None) -> str`
- `await oaas.stop_agent(agent_id: str | None = None, service_class=None, obj_id: int | None = None) -> None`
- `oaas.list_agents() -> Dict[str, Dict[str, Any]]` (map of agent_id to info)
- `await oaas.stop_all_agents() -> None`

Example:
```python
import asyncio

async def run_service():
    oaas.start_server(port=8080)

    agent_id = await oaas.start_agent(DataProcessor, obj_id=1)
    print("Agents:", oaas.list_agents())  # dict of agent info

    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await oaas.stop_all_agents()
        oaas.stop_server()
```

---

## Error Handling

Module: `oaas_sdk2_py.simplified.errors`

- Base: `OaasError`
- Serialization: `SerializationError`, `ValidationError`
- Decorators: `DecoratorError`
- Session: `SessionError`
- Server/Agent: `ServerError`, `AgentError`

```python
from oaas_sdk2_py.simplified.errors import OaasError

@oaas.method()
async def divide(self, a: float) -> float:
    if a == 0:
        raise OaasError("Zero not allowed")
    return 10.0 / a
```

---

## Performance Monitoring

Performance hooks exist across decorators, state descriptors, and the unified serializer.

Unified serializer metrics:
```python
from oaas_sdk2_py.simplified.serialization import UnifiedSerializer
s = UnifiedSerializer()

# After some serialize/deserialize operations
metrics = s.get_performance_metrics()
ser = metrics.serialization_metrics
deser = metrics.deserialization_metrics
print(ser.call_count, ser.success_rate, ser.average_duration)
print(deser.call_count, deser.success_rate, deser.average_duration)
```

Decorator/state metrics expose `PerformanceMetrics` with:
- `call_count`, `error_count`
- `average_duration`, `min_duration`, `max_duration`
- `success_rate`

---

## Legacy API

Backwards-compatible classes remain available:

- `Oparaca`, `Session`, `BaseObject` (alias of `OaasObject`), `ClsMeta`, `FuncMeta`

Example:
```python
from oaas_sdk2_py import Oparaca, BaseObject

oaas_engine = Oparaca()
cls_meta = oaas_engine.new_cls("Counter", pkg="example")

@cls_meta
class Counter(BaseObject):
    @cls_meta.func()
    async def increment(self, amount: int) -> int:
        data = await self.get_data_async(0)
        count = int(data.decode()) if data else 0
        count += amount
        await self.set_data_async(0, str(count).encode())
        return count
```

---

## Environment Variables

`OaasConfig` is a Pydantic `BaseSettings`; fields map to env vars automatically.

| Env Var | Maps to | Example |
| --- | --- | --- |
| `OPRC_ZENOH_PEERS` | `oprc_zenoh_peers` | `tcp/localhost:7447` |
| `OPRC_PARTITION_DEFAULT` | `oprc_partition_default` | `0` |
| `MOCK_MODE` | `mock_mode` | `true` |
| `ASYNC_MODE` | `async_mode` | `true` |
| `AUTO_COMMIT` | `auto_commit` | `true` |
| `BATCH_SIZE` | `batch_size` (deprecated) | `100` |

---

## Complete Example

```python
import asyncio
from pydantic import BaseModel
from typing import Dict, Any, List
from oaas_sdk2_py import oaas, OaasObject, OaasConfig

# Configure OaaS
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)

class TaskRequest(BaseModel):
    title: str
    description: str
    priority: int = 1

class TaskResponse(BaseModel):
    id: int
    title: str
    completed: bool

@oaas.service("TaskManager", package="productivity")
class TaskManager(OaasObject):
    tasks: Dict[int, Dict[str, Any]] = {}
    next_id: int = 1

    @oaas.method()
    async def create_task(self, request: TaskRequest) -> TaskResponse:
        task_id = self.next_id
        self.next_id += 1
        self.tasks[task_id] = {
            "title": request.title,
            "description": request.description,
            "priority": request.priority,
            "completed": False,
        }
        return TaskResponse(id=task_id, title=request.title, completed=False)

    @oaas.method()
    async def complete_task(self, task_id: int) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id]["completed"] = True
            return True
        return False

    @oaas.method()
    async def list_tasks(self) -> List[Dict[str, Any]]:
        return [{"id": task_id, **task} for task_id, task in self.tasks.items()]

async def main():
    oaas.start_server(port=8080)
    agent_id = await oaas.start_agent(TaskManager, obj_id=1)
    try:
        manager = TaskManager.create(obj_id=1)
        t1 = await manager.create_task(TaskRequest(title="Learn OaaS", description="Finish tutorial"))
        await manager.complete_task(t1.id)
        print(await manager.list_tasks())
    finally:
        await oaas.stop_agent(agent_id)
        oaas.stop_server()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Notes and Corrections vs Previous Reference

- Config fields now accurately reflect `oaas_sdk2_py.config.OaasConfig` (removed `server_url`, `timeout`, `log_level`).
- `@oaas.method` documents `stateless`, `strict`, `timeout`, and retry options.
- `@oaas.function` and `@oaas.constructor` included.
- `list_agents()` returns a dict of details, not a list.
- Optional second RPC parameter of type `InvocationRequest`/`ObjectInvocationRequest` is supported.
- Performance metrics are accessed via `UnifiedSerializer().get_performance_metrics()` returning separate serialization/deserialization metrics.
- Fixed UUID usage in examples (`uuid4()` instead of `UUID.uuid4()`).
