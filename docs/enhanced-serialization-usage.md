# Enhanced Serialization System Usage Guide

## Overview

The enhanced serialization system provides comprehensive type support for both RPC parameter handling and state management in the OaaS SDK. This unified approach ensures consistent behavior across all serialization operations.

## Key Features

### 1. Unified Type Support

The enhanced serialization system supports all the types that were previously only available in state management:

- **Basic Types**: `int`, `float`, `str`, `bool`, `bytes`, `None`
- **Collection Types**: `List[T]`, `Dict[K,V]`, `Tuple[T, ...]`, `Set[T]`
- **Optional/Union Types**: `Optional[T]`, `Union[T1, T2, ...]`
- **DateTime/UUID Types**: `datetime`, `UUID`
- **Pydantic Models**: Full support with validation
- **Complex Types**: Nested structures, custom classes, Enums

### 2. Enhanced Error Handling

Comprehensive error handling with detailed error context:

```python
from oaas_sdk2_py.simplified.serialization import RpcSerializationError

try:
    # Serialization operation
    serializer.serialize(value, target_type)
except RpcSerializationError as e:
    print(f"Error Code: {e.error_code}")
    print(f"Details: {e.details}")
```

### 3. Performance Monitoring

Built-in performance metrics collection:

```python
from oaas_sdk2_py.simplified.serialization import UnifiedSerializer

serializer = UnifiedSerializer()

# Perform operations
serializer.serialize(data, data_type)
serializer.deserialize(bytes_data, target_type)

# Get performance metrics
metrics = serializer.get_performance_metrics()
print(f"Serialization calls: {metrics.serialization_metrics.call_count}")
print(f"Average duration: {metrics.serialization_metrics.average_duration}")
```

## Usage Examples

### Basic RPC Method Parameters

```python
from oaas_sdk2_py.model import ClsMeta
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Optional

cls_meta = ClsMeta("MyService")

@cls_meta.func()
async def process_data(self, data: Dict[str, Union[str, int]]) -> List[str]:
    """Process complex data structure."""
    return [f"processed_{key}" for key in data.keys()]

@cls_meta.func()
async def handle_datetime(self, timestamp: datetime) -> str:
    """Handle datetime parameter."""
    return f"Received: {timestamp.isoformat()}"

@cls_meta.func()
async def process_uuid(self, identifier: UUID) -> str:
    """Handle UUID parameter."""
    return f"Processing ID: {identifier}"

@cls_meta.func()
async def optional_parameter(self, value: Optional[str] = None) -> str:
    """Handle optional parameter."""
    return f"Value: {value or 'None provided'}"
```

### State Management with Enhanced Types

```python
from oaas_sdk2_py.simplified.objects import OaasObject
from oaas_sdk2_py.simplified.state_descriptor import StateDescriptor
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Optional

class MyObject(OaasObject):
    # Enhanced type support in state management
    user_data: Dict[str, Union[str, int]] = StateDescriptor(
        "user_data", Dict[str, Union[str, int]], {}, 0
    )
    
    created_at: datetime = StateDescriptor(
        "created_at", datetime, datetime.now(), 1
    )
    
    session_id: Optional[UUID] = StateDescriptor(
        "session_id", Optional[UUID], None, 2
    )
    
    tags: List[str] = StateDescriptor(
        "tags", List[str], [], 3
    )
```

### Complex Data Structures

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class UserProfile(BaseModel):
    user_id: int
    username: str
    email: Optional[str] = None
    preferences: Dict[str, str] = {}

class UserGroup(BaseModel):
    group_id: int
    name: str
    members: List[UserProfile]
    metadata: Dict[str, Union[str, int, bool]]

@cls_meta.func()
async def create_user_group(self, group_data: UserGroup) -> str:
    """Create a new user group with complex nested data."""
    return f"Created group '{group_data.name}' with {len(group_data.members)} members"

@cls_meta.func()
async def update_user_preferences(
    self, 
    user_id: int, 
    preferences: Dict[str, Union[str, int, bool]]
) -> UserProfile:
    """Update user preferences with various data types."""
    # Implementation here
    pass
```

## Error Handling

### Comprehensive Error Information

The enhanced serialization system provides detailed error information:

```python
from oaas_sdk2_py.simplified.errors import SerializationError, ValidationError

try:
    # RPC call with invalid parameter
    await my_service.process_data("invalid_data_type")
except SerializationError as e:
    print(f"Serialization failed: {e}")
    print(f"Error code: {e.error_code}")
    print(f"Details: {e.details}")

try:
    # Type conversion error
    serializer.convert_value("invalid_number", int)
except ValidationError as e:
    print(f"Validation failed: {e}")
    print(f"Error code: {e.error_code}")
    print(f"Details: {e.details}")
```

### Error Codes

Common error codes you might encounter:

- `SERIALIZATION_ERROR`: General serialization failure
- `DESERIALIZATION_ERROR`: General deserialization failure  
- `TYPE_CONVERSION_ERROR`: Type conversion failure
- `PYDANTIC_VALIDATION_ERROR`: Pydantic model validation failure
- `DATETIME_FORMAT_ERROR`: Invalid datetime format
- `UUID_FORMAT_ERROR`: Invalid UUID format
- `RPC_PARAM_ERROR`: Generic RPC parameter error

## Performance Monitoring

### Metrics Collection

Performance metrics are automatically collected:

```python
from oaas_sdk2_py.simplified.serialization import UnifiedSerializer

serializer = UnifiedSerializer()

# Perform some operations
for i in range(100):
    data = {"iteration": i, "data": f"test_{i}"}
    serialized = serializer.serialize(data, Dict[str, Union[str, int]])
    deserialized = serializer.deserialize(serialized, Dict[str, Union[str, int]])

# Get comprehensive metrics
metrics = serializer.get_performance_metrics()

print("Serialization Metrics:")
print(f"  Total calls: {metrics.serialization_metrics.call_count}")
print(f"  Total duration: {metrics.serialization_metrics.total_duration:.4f}s")
print(f"  Average duration: {metrics.serialization_metrics.average_duration:.4f}s")
print(f"  Min duration: {metrics.serialization_metrics.min_duration:.4f}s")
print(f"  Max duration: {metrics.serialization_metrics.max_duration:.4f}s")
print(f"  Success rate: {metrics.serialization_metrics.success_rate:.2%}")

print("\nDeserialization Metrics:")
print(f"  Total calls: {metrics.deserialization_metrics.call_count}")
print(f"  Total duration: {metrics.deserialization_metrics.total_duration:.4f}s")
print(f"  Average duration: {metrics.deserialization_metrics.average_duration:.4f}s")
print(f"  Success rate: {metrics.deserialization_metrics.success_rate:.2%}")
```

### Performance Optimization

For optimal performance:

1. **Use Type Hints**: Always provide type hints for better serialization performance
2. **Avoid Deep Nesting**: Minimize deeply nested structures when possible
3. **Use Appropriate Types**: Choose the most specific type possible
4. **Monitor Metrics**: Regularly check performance metrics to identify bottlenecks

```python
# Good: Specific type hints
@cls_meta.func()
async def process_users(self, users: List[UserProfile]) -> Dict[str, int]:
    return {"processed": len(users)}

# Less optimal: Generic types
@cls_meta.func()
async def process_data(self, data: Dict) -> Dict:
    return {"processed": len(data)}
```

## Migration Guide

### From Legacy RPC Parameter Handling

If you're migrating from the old RPC parameter handling:

**Before (Limited Type Support):**
```python
@cls_meta.func()
async def old_method(self, data: dict) -> str:
    # Had to manually handle complex types
    if 'timestamp' in data:
        timestamp = datetime.fromisoformat(data['timestamp'])
    return "processed"
```

**After (Enhanced Type Support):**
```python
@cls_meta.func()
async def new_method(self, data: ProcessingRequest) -> ProcessingResponse:
    # Automatic type conversion and validation
    return ProcessingResponse(
        result="processed",
        timestamp=datetime.now()
    )
```

### Backward Compatibility

The enhanced serialization system is fully backward compatible:

```python
# Existing code continues to work
@cls_meta.func()
async def legacy_method(self, data: dict) -> str:
    return "still works"

# New enhanced features are available
@cls_meta.func()
async def enhanced_method(self, data: Dict[str, Union[str, int]]) -> List[str]:
    return ["enhanced", "features"]
```

## Best Practices

### 1. Use Specific Type Hints

```python
# Good: Specific types
async def process_user_data(self, user_data: Dict[str, Union[str, int]]) -> UserProfile:
    pass

# Less optimal: Generic types
async def process_data(self, data: Dict) -> Dict:
    pass
```

### 2. Handle Optional Parameters Properly

```python
# Good: Explicit optional handling
async def update_user(self, user_id: int, email: Optional[str] = None) -> bool:
    if email is not None:
        # Update email
        pass
    return True
```

### 3. Use Pydantic Models for Complex Data

```python
class UserRequest(BaseModel):
    user_id: int
    email: str
    preferences: Dict[str, str] = {}
    tags: List[str] = []

# Good: Structured data with validation
async def create_user(self, request: UserRequest) -> UserProfile:
    pass
```

### 4. Monitor Performance

```python
# Regularly check performance metrics
def check_serialization_performance():
    metrics = serializer.get_performance_metrics()
    if metrics.serialization_metrics.average_duration > 0.01:  # 10ms threshold
        print("Warning: Serialization is slow")
```

### 5. Handle Errors Gracefully

```python
async def robust_method(self, data: ComplexData) -> Result:
    try:
        # Process data
        return Result(success=True, data=processed_data)
    except ValidationError as e:
        return Result(success=False, error=f"Validation failed: {e}")
    except SerializationError as e:
        return Result(success=False, error=f"Serialization failed: {e}")
```

## Troubleshooting

### Common Issues

1. **Type Conversion Errors**
   - Ensure your data matches the expected type
   - Use appropriate type hints
   - Check for None values in non-optional types

2. **Pydantic Validation Errors**
   - Verify your model definitions
   - Check required fields are provided
   - Ensure field types match the data

3. **Performance Issues**
   - Monitor serialization metrics
   - Avoid deeply nested structures
   - Use specific type hints

### Debug Mode

Enable debug logging to get detailed serialization information:

```python
from oaas_sdk2_py.simplified.errors import get_debug_context, DebugLevel

# Enable debug mode
debug_ctx = get_debug_context()
debug_ctx.set_level(DebugLevel.DEBUG)
debug_ctx.enable_performance_monitoring()

# Your serialization operations will now log detailed information
```

## Conclusion

The enhanced serialization system provides:

- **Comprehensive Type Support**: All Python types are supported
- **Consistent Behavior**: Same serialization logic for RPC and state management
- **Enhanced Error Handling**: Detailed error information for debugging
- **Performance Monitoring**: Built-in metrics for optimization
- **Backward Compatibility**: Existing code continues to work
- **Developer Experience**: Better type safety and validation

This unified approach ensures that your OaaS applications can handle any data type that Python developers need to use, with robust error handling and performance monitoring.