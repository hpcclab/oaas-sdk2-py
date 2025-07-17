# Session Management and Backward Compatibility - Phase 1 Week 2

## Overview

This document describes the enhanced session management capabilities and backward compatibility features introduced in Phase 1 Week 2 of the OaaS SDK simplification project.

## Key Features

### 1. AutoSessionManager

The `AutoSessionManager` class provides automatic session lifecycle management with the following features:

- **Automatic session creation and cleanup**
- **Thread-safe session handling**
- **Background auto-commit for state changes**
- **Integration with existing Oparaca engine**
- **Backward compatibility with manual session management**

### 2. Enhanced Backward Compatibility

The `LegacySessionAdapter` class provides full compatibility with the existing Session API while benefiting from the new automatic management features.

### 3. Auto-commit Functionality

Automatic commit functionality that can be enabled/disabled and configured for different intervals.

## Usage Examples

### Basic Auto Session Management

```python
from oaas_sdk2_py import oaas, OaasObject, OaasConfig, configure_oaas

# Configure for auto session management
config = OaasConfig(mock_mode=True, auto_commit=True)
configure_oaas(config)

# Define a service
@oaas.service("MyService")
class MyService(OaasObject):
    counter: int = 0
    
    @oaas.method
    def increment(self):
        self.counter += 1
        return self.counter

# Create and use objects - sessions are managed automatically
obj = MyService.create()
obj.increment()  # Auto-commits in background
print(f"Counter: {obj.counter}")
```

### Thread-Safe Session Management

```python
import threading
from oaas_sdk2_py import oaas, OaasObject, configure_oaas, OaasConfig

# Configure for thread-safe operations
config = OaasConfig(mock_mode=True, auto_commit=True)
configure_oaas(config)

@oaas.service("ThreadSafeService")
class ThreadSafeService(OaasObject):
    thread_data: str = ""
    
    @oaas.method
    def set_thread_data(self):
        self.thread_data = f"Thread-{threading.get_ident()}"

def worker():
    # Each thread gets its own session automatically
    obj = ThreadSafeService.create()
    obj.set_thread_data()
    print(f"Thread {threading.get_ident()}: {obj.thread_data}")

# Create multiple threads
threads = []
for i in range(5):
    t = threading.Thread(target=worker)
    threads.append(t)
    t.start()

for t in threads:
    t.join()
```

### Manual Session Control

```python
from oaas_sdk2_py import OaasService, oaas, OaasObject

# Get manual control when needed
with OaasService.session_scope() as session:
    # Operations within this scope use the same session
    obj1 = MyService.create()
    obj2 = MyService.create()
    
    obj1.increment()
    obj2.increment()
    
    # Session automatically commits when exiting scope
```

### Auto-commit Configuration

```python
from oaas_sdk2_py import (
    enable_auto_commit, 
    disable_auto_commit, 
    set_auto_commit_interval,
    OaasService
)

# Enable auto-commit
enable_auto_commit()

# Set auto-commit interval to 0.5 seconds
set_auto_commit_interval(0.5)

# Disable auto-commit when needed
disable_auto_commit()

# Manual commit all sessions
OaasService.commit_all()

# Async commit all sessions
await OaasService.commit_all_async()
```

### Backward Compatibility

```python
from oaas_sdk2_py import (
    # Legacy API - still works exactly the same
    Oparaca, Session, BaseObject, ClsMeta,
    
    # New compatibility functions
    new_session, get_global_oaas
)

# Traditional usage still works
config = OaasConfig()
oparaca = Oparaca(config=config, mock_mode=True)
cls_meta = oparaca.new_cls("LegacyService")

@cls_meta
class LegacyService(BaseObject):
    @cls_meta.func()
    def legacy_method(self):
        return "Still works!"

# Traditional session usage
session = oparaca.new_session()
obj = session.create_object(cls_meta, local=True)
session.commit()

# New session adapter with auto-management
new_style_session = new_session()
obj2 = new_style_session.create_object(cls_meta, local=True)
new_style_session.commit()  # Still works, but auto-managed underneath
```

## API Reference

### AutoSessionManager

```python
class AutoSessionManager:
    def __init__(self, oparaca: Oparaca)
    def get_session(self, partition_id: Optional[int] = None) -> Session
    def create_object(self, cls_meta: ClsMeta, obj_id: Optional[int] = None, 
                     local: bool = None, partition_id: Optional[int] = None) -> OaasObject
    def load_object(self, cls_meta: ClsMeta, obj_id: int, 
                   partition_id: Optional[int] = None) -> OaasObject
    def schedule_commit(self, obj: OaasObject) -> None
    def commit_all(self) -> None
    async def commit_all_async(self) -> None
    def cleanup_session(self, thread_id: Optional[int] = None) -> None
    def shutdown(self) -> None
    
    @contextmanager
    def session_scope(self, partition_id: Optional[int] = None)
```

### LegacySessionAdapter

```python
class LegacySessionAdapter:
    def __init__(self, auto_session_manager: AutoSessionManager, partition_id: Optional[int] = None)
    def create_object(self, cls_meta: ClsMeta, obj_id: Optional[int] = None, local: bool = False) -> OaasObject
    def load_object(self, cls_meta: ClsMeta, obj_id: int) -> OaasObject
    def delete_object(self, cls_meta: ClsMeta, obj_id: int, partition_id: Optional[int] = None)
    def commit(self)
    async def commit_async(self)
    def obj_rpc(self, req) -> Any
    async def obj_rpc_async(self, req) -> Any
    def fn_rpc(self, req) -> Any
    async def fn_rpc_async(self, req) -> Any
    def invoke_local(self, req) -> Any
    async def invoke_local_async(self, req) -> Any
    
    # Properties for full compatibility
    @property
    def local_obj_dict(self)
    @property
    def remote_obj_dict(self)
    @property
    def delete_obj_set(self)
    @property
    def partition_id(self)
    @property
    def rpc_manager(self)
    @property
    def data_manager(self)
    @property
    def meta_repo(self)
    @property
    def local_only(self)
```

### Global Functions

```python
# Session management
def new_session(partition_id: Optional[int] = None) -> LegacySessionAdapter
def get_global_oaas() -> Oparaca
def configure_oaas(config: OaasConfig) -> None

# Auto-commit control
def enable_auto_commit() -> None
def disable_auto_commit() -> None
def set_auto_commit_interval(seconds: float) -> None
```

### OaasService Extensions

```python
class OaasService:
    @staticmethod
    def commit_all() -> None
    
    @staticmethod
    async def commit_all_async() -> None
    
    @staticmethod
    def get_session(partition_id: Optional[int] = None) -> Session
    
    @staticmethod
    @contextmanager
    def session_scope(partition_id: Optional[int] = None)
    
    @staticmethod
    def cleanup_session(thread_id: Optional[int] = None) -> None
    
    @staticmethod
    def shutdown() -> None
```

## Migration Guide

### From Manual Session Management

**Before:**
```python
# Manual session management
global_oaas = Oparaca(config=config, mock_mode=True)
session = global_oaas.new_session()
obj = session.create_object(cls_meta, local=True)
session.commit()
```

**After:**
```python
# Automatic session management
configure_oaas(OaasConfig(mock_mode=True, auto_commit=True))
obj = MyService.create()  # Auto-managed session
# Auto-commits in background
```

### From Traditional Session API

**Before:**
```python
session = oparaca.new_session()
obj = session.create_object(cls_meta, local=True)
session.commit()
```

**After:**
```python
session = new_session()  # Returns LegacySessionAdapter
obj = session.create_object(cls_meta, local=True)
session.commit()  # Still works, but auto-managed underneath
```

## Best Practices

1. **Use auto-commit for simplicity**: Enable auto-commit for most applications to reduce boilerplate code.

2. **Use session scopes for transactions**: When you need explicit control over commit timing, use `session_scope()`.

3. **Thread safety**: The new session manager is thread-safe by default. Each thread gets its own session.

4. **Resource cleanup**: Call `OaasService.shutdown()` when your application exits to ensure proper cleanup.

5. **Backward compatibility**: Existing code using the legacy API continues to work without changes.

## Performance Considerations

- **Background commits**: Auto-commit runs in a background thread to minimize impact on application performance.
- **Thread-local sessions**: Each thread maintains its own session to avoid contention.
- **Weak references**: The session manager uses weak references to avoid memory leaks.
- **Configurable intervals**: Auto-commit intervals can be configured based on your application's needs.

## Error Handling

The session manager includes robust error handling:

- **Session commit errors**: Logged but don't affect other sessions
- **Background timer errors**: Automatically restart the timer
- **Thread cleanup errors**: Logged during session cleanup
- **Shutdown errors**: Handled gracefully during application shutdown

## Thread Safety

The AutoSessionManager is designed to be thread-safe:

- **Thread-local sessions**: Each thread gets its own session instance
- **Reentrant locks**: Used to protect shared data structures
- **Concurrent commits**: Multiple sessions can commit concurrently
- **Async support**: Full support for async/await operations

This implementation ensures that the OaaS SDK can be used safely in multi-threaded applications while maintaining backward compatibility with existing code.