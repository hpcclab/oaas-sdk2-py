# *OaaS-SDK2-PY Reference*
Table of Contents: 
- [Class]
    - [Core Classes](#core-classes)
        - [Oparaca Class](#oparaca-class)
        - [BaseObject Class](#baseobject-class)
        - [InvocationContext Class](#invocationcontext-class)
    - [Data Management Classes](#data-managment-classes)
        - [DataManager Class](#datamanager-class)
        - [ZenohDataManager Class](#zenohdatamanager-class)
    - [RPC Communication Classes](#rpc-communication-classes)
        - [RpcManager Class](#rpcmanager-class)
        - [ZenohRpcManager Class](#zenohrpcmanager-class)
    - [Metadata and Model Classes](#metadata-and-model-classes)

# *Core Classes*
These are the primary classes that define the OaaS framework and its execution flow. 

## *Oparaca Class*
The `Oparaca` class is a core class of OaaS-SDK2-PY, responsible for managing the application's class registration, invocation context, and execution. 

### *Import Path*
```python
from oaas_sdk2_py.engine import Oparaca
```

### *Constructor*
```python
Oparaca(default_pkg: str = "default", config: [OprcConfig] = None)
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `default_pkg` | `str` | `default` | Default package name for new classes |
| `config` | `OprcConfig` | `None` | Configuration settings for OaaS | 

Example:
```python
from oaas_sdk2_py import Oparaca
from oaas_sdk2_py.config import OprcConfig

oaas = Oparaca(config=OprcConfig())
```


### *Attributes*

| Attribute | Type | Description |
| ----------|------|-------------|
| `config` | `OprcConfig` | Configuration settings for OaaS |
| `meta_repo` | `MetadataRepo` | Stores metadata about registered classes |
| `default_pkg` | `str` | The default package for class registration |
| `rpc` | `RpcManager` | Manages function calls over gRPC |
| `data` | `DataManager` | Handles data storage and retrieval | 

### *Methods*
1. `new_cls()`

Description:
Creates a new class in Oparaca

```python
def new_cls(self, name: Optional[str] = None, pkg: Optional[str] = None) -> ClsMeta
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `name` | `str` | `None` | Name of the class being registered |
| `pkg` | `str` | `None` | Package namespace for the class |

Returns: 
`ClsMeta` (Metadata object containing function details)

Example:
```python
example_class = oaas.new_cls(pkg="example", name="example_service")
```

2. `new_context()`

Description:
Creates a new invocation context for execution

```python
def new_context(self, partition_id: Optional[int] = None) -> InvocationContext
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `partition_id` | `int` | `None` | Partition ID for execution |

Returns:
`InvocationContext` (New context for function execution)

Example:
```python
ctx = oaas.new_context(partition_id=1)
```

3. `handle_obj_invoke()`

Description:
Handles function invocation for objects

```python
async def handle_obj_invoke(self, req: ObjectInvocationRequest) -> InvocationResponse
```

Parameters:
Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `req` | `ObjectInvocationRequest` | - | The request object containing invocation details |

Returns:
`InvocationResponse` (Result of function execution)

Example:
```python
response = await oaas.handle_obj_invoke(invocation_request)
```

4. `serve_local_function`

Description:
Serves a local function, making it available for invocation

```python
async def serve_local_function(self, cls_id: str, fn_name: str, obj_id: int, partition_id: int = 0)
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `cls_id` | `str` | - | ID of the class |
| `fn_name` | `str` | - | Function name to serve |
| `obj_id` | `int` | - | Object ID associated with the function |
| `partition_id` | `int` | `0` | Partition where the function should run |

Example:
```python
await oaas.serve_local_function(cls_id="example.hello", fn_name="greet", obj_id=1)
```

## *BaseObject Class*
The `BaseObject` class is a core class that all user-defined objects inherit from, enabling function invocation and state. 

### *Import Path*
```python
from oaas_sdk2_py.engine import BaseObject
```

### *Constructor*
```python
BaseObject(meta: ObjectMeta = None, ctx: InvocationContext = None)
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `meta` | `ObjectMeta` | `None` | The metadata for the object instance |
| `ctx` | `InvocationContext` | `None` | The invocation context that manages the object |


### *Attributes*
| Attribute | Type | Description |
| ----------|------|-------------|
| `meta` | `ObjectMeta` | Object metadata |
| `ctx` | `InvocationContext` | The execution context managing the object |
| `_state` | `dict[int, bytes]` | Stores object state |
| `_dirty` | `bool` | Indicates whether the object has been modified |

### *Methods*

1. `set_data()`

Description: 
Stores data in the object's internal state

```python
def set_data(self, index: int, data: bytes)
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `index` | `int` | - | The index key for storing the data |
| `data` | `bytes` | - | The data to store |

Example:
```python
obj.set_data(0, b"Hello, world!")
```

2. `get_data()`

Description:
Retrieves data from the object's internal state

```python
async def get_data(self, index: int) -> bytes
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `index` | `int` | - | The index key to retrieve data from |

Returns:
`bytes` (The retrieved data)

Example:
```python
data = await obj.get_data(0)
```

3. `dirty` (Property)

Description:
Indicates if the object's state has changed

```python
@property
def dirty(self) -> bool
```

Returns:
`bool` (`True` if the object has unsaved changes)

Example:
```python
if obj.dirty:
    print("Object state has changed!")
```

4. `state` (Property)

Description:
Retrieves the current state of the object

```python
@property
def state(self) -> Dict[int, bytes]
```

Returns:
`dict[int, bytes]` (The object's data)

Example:
```python
current_state = obj.state
```

5. `remote` (Property)

Description:
Checks if the object is a remote reference

```python
@property
def remote(self) -> bool
```

Returns:
`bool` (`True` if the object is remote)

Example:
```python
if obj.remote:
    print("This is a remote object!")
```

6. `create_request()`

Description:
Creates an InvocationRequest for a stateless function call

```python
def create_request(self, fn_name: str, payload: bytes | None = None, options: dict[str, str] | None = None)
```

| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `fn_name` | `str` | - | Name of the function to invoke |
| `payload` | `bytes` | `None` | Optional function parameters |
| `options` | `dict[str, str]` | `None` | Extra options for invocation |

Returns:
`InvocationRequest` (The formatted request)

Example:
```python
request = obj.create_request("echo", b"Hello!")
```

7. `create_obj_request()`

Description:
Creates an ObjectInvocationRequest for a stateful function call

```python
def create_obj_request(self, fn_name: str, payload: bytes | None = None, options: dict[str, str] | None = None) -> ObjectInvocationRequest
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `fn_name` | `str` | - | Name of the function to invoke |
| `payload` | `bytes` | `None` | Optional function parameters |
| `options` | `dict[str, str]` | `None` | Extra options for invocation |

Returns:
`ObjectInvocationRequest` (The formatted request)

Example:
```python
request = obj.create_obj_request("greet", b"Alice")
```

## *InvocationContext Class*
The `InvocationContext` class is a core class that manages obejct lifecycle and function exeuction within an invocation.

### *Import Path*
```python
from oaas_sdk2_py.engine import InvocationContext
```

### *Constructor*
```python
InvocationContext(self, partition_id: int, rpc: RpcManager, data: DataManager)
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `partition_id` | `int` | - | The parition ID assigned to this execution context |
| `rpc` | `RpcManager` | - | The RPC manager for remote function invocation |
| `data` | `DataManager` | - | The data manager for handling object state |


### *Attributes*
| Attribute | Type | Description |
| ----------|------|-------------|
| `partition_id` | `int` | The partition assigned to the execution context |
| `rpc` | `RpcManager` | Manages function calls over gRPC |
| `data_manager` | `DataManager` | Handles data retrieval and persistence |
| `local_obj_dict` | `dict` | Stores local objects in the current invocation |
| `remote_obj_dict` | `dict` | Stores remote object references |


### *Methods*
1. `create_emtpy_object()`

Description:
Creates an empty object with a new unique ID

```python
def create_empty_object(self, cls_meta: ClsMeta) -> BaseObject
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `cls_meta` | `ClsMeta` | - | The metadata of the class to instantiate |

Returns: 
`BaseObject` (A new empty object of the given class)

Example:
```python
obj = ctx.create_empty_object(example_class)
```

2. `create_object()`

Description: 
Creates an object with a specific ID

```python
def create_object(self, cls_meta: ClsMeta, obj_id: int)
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `cls_meta` | `ClsMeta` | - | Metadata of the object's class |
| `obj_id` | `int` | - | The specific object ID to use |

Returns:
`BaseObject` (The instantiated object)

Example:
```python
obj = ctx.create_object(example_class, obj_id=1)
```

3. `create_object_from_ref()`

Description:
Creates a reference to a remote object

```python
def create_object_from_ref(self, cls_meta: ClsMeta, obj_id: int) -> BaseObject
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `cls_meta` | `ClsMeta` | - | Metadata of the referenced object's class |
| `obj_id` | `int` | - | The object ID to reference |

Returns:
`BaseObject` (A remote object reference)

Example:
```python
remote_obj = ctx.create_object_from_ref(example_class, obj_id=1)
```

4. `obj_rpc()`

Description:
Executes a remote object function call using RPC

```python
async def obj_rpc(self, req: ObjectInvocationRequest) -> InvocationResponse
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `req` | `ObjectInvocationRequest` | - | The RPC request for the function invocation |

Returns:
`InvocationResponse` (The result of the function call)

Example:
```python
response = await ctx.obj_rpc(invocation_request)
```

5. `fn_rpc()`

Description:
Executes a remote stateless function using RPC 

```python
async def fn_rpc(self, req: InvocationRequest) -> InvocationResponse
```

Parameters:
| Parameter | Type | Default | Description |
| ----------|------|---------|-------------|
| `req` | `ObjectInvocationRequest` | - | The RPC request for the function invocation |

Returns:
`InvocationResponse` (The result of the function call)

6. `commit()`

Description: 
Commits all changes made in the invocation context

```python
async def commit(self)
```

Example:
```python
await ctx.commit()
```
