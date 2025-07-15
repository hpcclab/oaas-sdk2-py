# OaaS SDK API Reference

## Table of Contents
1. [Core Classes](#core-classes)
2. [Configuration](#configuration)
3. [Models and Metadata](#models-and-metadata)
4. [Sessions](#sessions)
5. [Objects](#objects)
6. [Handlers](#handlers)
7. [Mock Implementation](#mock-implementation)
8. [Repository](#repository)
9. [Request/Response Types](#requestresponse-types)
10. [Exceptions](#exceptions)

## Core Classes

### Oparaca

The main engine class that manages the OaaS system.

**Module:** [`oaas_sdk2_py.engine`](oaas_sdk2_py/engine.py)

#### Constructor

```python
def __init__(
    self,
    default_pkg: str = "default",
    config: OprcConfig = None,
    mock_mode: bool = False,
    meta_repo: MetadataRepo = None,
    engine: oprc_py.OaasEngine = None,
    async_mode: bool = False,
)
```

| Parameter | Type | Description |
| --- | --- | --- |
| `default_pkg` | `str` | Default package name for classes. |
| `config` | `OprcConfig` | Configuration object (uses default if None). |
| `mock_mode` | `bool` | Enable mock mode for testing. |
| `meta_repo` | `MetadataRepo` | Metadata repository instance. |
| `engine` | `oprc_py.OaasEngine` | OaaS engine instance. |
| `async_mode` | `bool` | Enable async server mode. |

#### Methods

| Method | Description |
| --- | --- |
| `new_cls(name: str = None, pkg: str = None) -> ClsMeta` | Creates a new class metadata object. |
| `new_session(partition_id: int = None) -> Session` | Creates a new session for object management. |
| `mock() -> Oparaca` | Returns a mock version of the OaaS instance for testing. |
| `create_object(cls_meta: ClsMeta, obj_id: int = None, local: bool = False)` | Creates an object using the default session. |
| `load_object(cls_meta: ClsMeta, obj_id: int)` | Loads an existing object using the default session. |
| `delete_object(cls_meta: ClsMeta, obj_id: int, partition_id: int = None)` | Deletes an object using the default session. |
| `start_grpc_server(loop=None, port=8080)` | Starts the gRPC server. |
| `stop_server()` | Stops the running server. |
| `run_agent(loop, cls_meta: ClsMeta, obj_id: int, partition_id: int = None)` | Runs an agent for a specific object and class. |
| `stop_agent(cls_meta: ClsMeta, obj_id: int, partition_id: int = None)` | Stops an agent for a specific object and class. |
| `commit() / commit_async()` | Commits changes using the default session. |

## Configuration

### OprcConfig

Configuration class for OaaS settings.

**Module:** [`oaas_sdk2_py.config`](oaas_sdk2_py/config.py)

#### Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `oprc_odgm_url` | `HttpUrl` | ODGM server URL (default: "http://localhost:10000"). |
| `oprc_zenoh_peers` | `str`|`None` | Zenoh peers (default: None). |
| `oprc_partition_default` | `int` | Default partition ID (default: 0). |

#### Methods

| Method | Description |
| --- | --- |
| `get_zenoh_peers() -> list[str]`|`None` | Returns the list of Zenoh peers. |

## Models and Metadata

### ClsMeta

Class metadata for OaaS classes.

**Module:** [`oaas_sdk2_py.model`](oaas_sdk2_py/model.py)

#### Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `name` | `str` | Class name. |
| `pkg` | `str` | Package name. |
| `cls_id` | `str` | Full class ID (pkg.name). |
| `func_dict` | `dict[str, FuncMeta]` | Function metadata dictionary. |
| `state_dict` | `dict[int, StateMeta]` | State metadata dictionary. |

#### Methods

| Method | Description |
| --- | --- |
| `func(name="", stateless=False, strict=False, serve_with_agent=False)` | Decorator for registering class methods as OaaS functions. |
| `export_pkg(pkg: dict) -> dict` | Exports class metadata to package dictionary. |

### FuncMeta

Function metadata for OaaS methods.

**Module:** [`oaas_sdk2_py.model`](oaas_sdk2_py/model.py)

#### Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `func` | `function` | Original function. |
| `invoke_handler` | `Callable` | Invocation handler. |
| `signature` | `inspect.Signature` | Function signature. |
| `name` | `str` | Function name. |
| `stateless` | `bool` | Whether function is stateless. |
| `serve_with_agent` | `bool` | Can be served by agent. |
| `is_async` | `bool` | Whether function is async. |

### StateMeta

State metadata for object data indices.

**Module:** [`oaas_sdk2_py.model`](oaas_sdk2_py/model.py)

#### Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `index` | `int` | Data index. |
| `name` | `str` | State name (optional). |

## Sessions

### Session

Session class for managing object lifecycle and transactions.

**Module:** [`oaas_sdk2_py.session`](oaas_sdk2_py/session.py)

#### Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `partition_id` | `int` | Session partition ID. |
| `local_obj_dict` | `Dict[ObjectMetadata, BaseObject]` | Local objects. |
| `remote_obj_dict` | `Dict[ObjectMetadata, BaseObject]` | Remote objects. |
| `delete_obj_set` | `set[ObjectMetadata]` | Objects marked for deletion. |

#### Methods

| Method | Description |
| --- | --- |
| `create_object(cls_meta: ClsMeta, obj_id: int = None, local: bool = False)` | Creates a new object instance. |
| `load_object(cls_meta: ClsMeta, obj_id: int)` | Loads an existing remote object. |
| `delete_object(cls_meta: ClsMeta, obj_id: int, partition_id: int = None)` | Marks an object for deletion. |
| `obj_rpc(req: ObjectInvocationRequest) -> InvocationResponse` | Performs synchronous object RPC. |
| `obj_rpc_async(req: ObjectInvocationRequest) -> InvocationResponse` | Performs asynchronous object RPC. |
| `fn_rpc(req: InvocationRequest) -> InvocationResponse` | Performs synchronous function RPC. |
| `fn_rpc_async(req: InvocationRequest) -> InvocationResponse` | Performs asynchronous function RPC. |
| `invoke_local(req: InvocationRequest \| ObjectInvocationRequest) -> InvocationResponse` | Invokes a function locally without RPC. |
| `invoke_local_async(req: InvocationRequest \| ObjectInvocationRequest) -> InvocationResponse` | Invokes a function locally without RPC (async). |
| `commit() / commit_async()` | Commits all changes in the session. |

## Objects

### BaseObject

Base class for all OaaS objects.

**Module:** [`oaas_sdk2_py.obj`](oaas_sdk2_py/obj.py)

#### Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `meta` | `ObjectMetadata` | Object metadata. |
| `session` | `Session` | Session instance. |
| `object_id` | `int` | Object ID (property). |
| `dirty` | `bool` | Whether object has uncommitted changes (property). |
| `remote` | `bool` | Whether object is remote (property). |
| `state` | `dict[int, bytes]` | Object state dictionary (property). |

#### Methods

| Method | Description |
| --- | --- |
| `get_data(index: int) -> bytes` | Gets data from the specified index synchronously. |
| `get_data_async(index: int) -> bytes` | Gets data from the specified index asynchronously. |
| `set_data(index: int, data: bytes)` | Sets data at the specified index synchronously. |
| `set_data_async(index: int, data: bytes)` | Sets data at the specified index asynchronously. |
| `fetch(force: bool = False)` | Fetches object data from storage. |
| `delete()` | Marks object for deletion. |
| `commit() / commit_async()` | Commits object changes. |
| `create_request(fn_name: str, payload: bytes = None, options: dict = None) -> InvocationRequest` | Creates a function invocation request. |
| `create_obj_request(fn_name: str, payload: bytes = None, options: dict = None) -> ObjectInvocationRequest` | Creates an object invocation request. |
| `trigger(source, target_fn, event_type)` | Adds a trigger to the object. |
| `suppress(source, target_fn, event_type)` | Removes a trigger from the object. |
| `manage_trigger(source, target_fn, event_type, add=True, req_options=None)` | Manages (adds or removes) a trigger. |

## Handlers

### AsyncInvocationHandler

Handles asynchronous function invocations.

**Module:** [`oaas_sdk2_py.handler`](oaas_sdk2_py/handler.py)

#### Methods

| Method | Description |
| --- | --- |
| `invoke_fn(invocation_request: InvocationRequest) -> InvocationResponse` | Invokes a function asynchronously. |
| `invoke_obj(invocation_request: ObjectInvocationRequest) -> InvocationResponse` | Invokes an object method asynchronously. |

### SyncInvocationHandler

Handles synchronous function invocations.

**Module:** [`oaas_sdk2_py.handler`](oaas_sdk2_py/handler.py)

#### Methods

| Method | Description |
| --- | --- |
| `invoke_fn(invocation_request: InvocationRequest) -> InvocationResponse` | Invokes a function synchronously. |
| `invoke_obj(invocation_request: ObjectInvocationRequest) -> InvocationResponse` | Invokes an object method synchronously. |

## Mock Implementation

### LocalDataManager

Mock data manager for testing.

**Module:** [`oaas_sdk2_py.mock`](oaas_sdk2_py/mock.py)

#### Methods

| Method | Description |
| --- | --- |
| `get_obj(cls_id: str, partition_id: int, obj_id: int) -> ObjectData` | Gets object data synchronously. |
| `get_obj_async(cls_id: str, partition_id: int, obj_id: int) -> ObjectData` | Gets object data asynchronously. |
| `set_obj(obj: ObjectData)` | Sets object data synchronously. |
| `set_obj_async(obj: ObjectData)` | Sets object data asynchronously. |
| `del_obj(cls_id: str, partition_id: int, obj_id: int)` | Deletes object data synchronously. |
| `del_obj_async(cls_id: str, partition_id: int, obj_id: int)` | Deletes object data asynchronously. |

### LocalRpcManager

Mock RPC manager for testing.

**Module:** [`oaas_sdk2_py.mock`](oaas_sdk2_py/mock.py)

#### Methods

| Method | Description |
| --- | --- |
| `invoke_fn(req: InvocationRequest) -> InvocationResponse` | Invokes function synchronously. |
| `invoke_fn_async(req: InvocationRequest) -> InvocationResponse` | Invokes function asynchronously. |
| `invoke_obj(req: ObjectInvocationRequest) -> InvocationResponse` | Invokes object method synchronously. |
| `invoke_obj_async(req: ObjectInvocationRequest) -> InvocationResponse` | Invokes object method asynchronously. |

## Repository

### MetadataRepo

Repository for storing and managing class metadata.

**Module:** [`oaas_sdk2_py.repo`](oaas_sdk2_py/repo.py)

#### Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `cls_dict` | `dict[str, ClsMeta]` | Dictionary of class metadata. |

#### Methods

| Method | Description |
| --- | --- |
| `add_cls(cls_meta: ClsMeta)` | Adds class metadata to the repository. |
| `get_cls_meta(cls_id: str) -> ClsMeta` | Gets class metadata by class ID. |
| `export_pkg() -> dict[str, Any]` | Exports all packages as dictionary. |
| `print_pkg()` | Prints package metadata in YAML format. |

## Request/Response Types

### InvocationRequest

**Module:** `oprc_py.oprc_py`

| Attribute | Type | Description |
| --- | --- | --- |
| `cls_id` | `str` | Class ID. |
| `fn_id` | `str` | Function ID. |
| `payload` | `bytes` | Request payload. |
| `options` | `dict[str, str]` | Request options. |

### ObjectInvocationRequest

**Module:** `oprc_py.oprc_py`

| Attribute | Type | Description |
| --- | --- | --- |
| `cls_id` | `str` | Class ID. |
| `partition_id` | `int` | Partition ID. |
| `object_id` | `int` | Object ID. |
| `fn_id` | `str` | Function ID. |
| `payload` | `bytes` | Request payload. |
| `options` | `dict[str, str]` | Request options. |

### InvocationResponse

**Module:** `oprc_py.oprc_py`

| Attribute | Type | Description |
| --- | --- | --- |
| `payload` | `bytes` | Response payload. |
| `status` | `int` | Response status code. |

### InvocationResponseCode

**Module:** `oprc_py.oprc_py`

| Value | Description |
| --- | --- |
| `Okay` | Success. |
| `InvalidRequest` | Invalid request. |
| `AppError` | Application error. |

### ObjectData

**Module:** `oprc_py.oprc_py`

| Attribute | Type | Description |
| --- | --- | --- |
| `meta` | `ObjectMetadata` | Object metadata. |
| `entries` | `dict[int, bytes]` | Data entries. |
| `event` | `PyObjectEvent` | Event configuration. |

### ObjectMetadata

**Module:** `oprc_py.oprc_py`

| Attribute | Type | Description |
| --- | --- | --- |
| `cls_id` | `str` | Class ID. |
| `partition_id` | `int` | Partition ID. |
| `object_id` | `int` | Object ID. |

## Exceptions

### Common Exceptions

| Exception | Description |
| --- | --- |
| `ValueError` | Invalid parameter values. |
| `TypeError` | Invalid parameter types. |
| `KeyError` | Missing keys or objects. |
| `AttributeError` | Missing attributes or methods. |

## Utility Functions

### parse_resp(resp) -> InvocationResponse

**Module:** [`oaas_sdk2_py.model`](oaas_sdk2_py/model.py)

| Parameter | Type | Description |
| --- | --- | --- |
| `resp` | `Any` | Response object (None, InvocationResponse, BaseModel, bytes, or str). |

## Environment Variables

| Variable | Description |
| --- | --- |
| `OPRC_ODGM_URL` | ODGM server URL. |
| `OPRC_ZENOH_PEERS` | Zenoh peer addresses. |
| `OPRC_PARTITION_DEFAULT` | Default partition ID. |
| `LOG_LEVEL` | Logging level. |
| `HTTP_PORT` | HTTP server port. |