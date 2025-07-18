# Enhanced Request Serialization Design

## Problem Analysis

The current RPC parameter handling in [`model.py`](oaas_sdk2_py/model.py) has limited type support compared to the comprehensive state management system in [`state_descriptor.py`](oaas_sdk2_py/simplified/state_descriptor.py). This creates inconsistency and limits the types that can be used in RPC calls.

## Current Limitations

### 1. RPC Parameter Types (model.py lines 411-564)
**Currently Supported:**
- BaseModel (Pydantic)
- InvocationRequest/ObjectInvocationRequest
- bytes, str, dict, int, float, bool, list

**Missing:**
- datetime, UUID
- Union/Optional types
- Complex nested structures
- Type validation and conversion
- Comprehensive error handling

### 2. State Management Types (state_descriptor.py lines 1-496)
**Already Supported:**
- All basic types with conversion
- Generic types (List[T], Dict[K,V], Union, Optional)
- Pydantic models with validation
- datetime, UUID
- Complex nested structures
- Comprehensive error handling
- Performance monitoring

## Enhanced Serialization Architecture

### 1. Unified Type System

Create a shared serialization system that both RPC and state management can use:

```python
# New file: oaas_sdk2_py/simplified/serialization.py
class UnifiedSerializer:
    """Unified serialization system for both RPC and state management."""
    
    @staticmethod
    def serialize(value: Any, type_hint: Type = None) -> bytes:
        """Serialize any value with optional type hint."""
        
    @staticmethod
    def deserialize(data: bytes, type_hint: Type) -> Any:
        """Deserialize bytes to typed value."""
        
    @staticmethod
    def convert_value(value: Any, target_type: Type) -> Any:
        """Convert value to target type with validation."""
```

### 2. Enhanced RPC Parameter Processing

Extend the `_create_single_param_caller` method to support all types:

```python
# Enhanced model.py
def _create_enhanced_single_param_caller(self, function, sig: inspect.Signature, strict):
    """Create caller with comprehensive type support."""
    second_param = list(sig.parameters.values())[1]
    param_type = second_param.annotation
    
    # Use unified serialization system
    serializer = UnifiedSerializer()
    
    if inspect.iscoroutinefunction(function):
        @functools.wraps(function)
        async def caller(obj_self, req):
            try:
                # Deserialize with type validation
                value = serializer.deserialize(req.payload, param_type)
                result = await function(obj_self, value)
                return parse_resp(result)
            except Exception as e:
                return self._create_error_response(e, param_type)
        return caller
    else:
        @functools.wraps(function)
        def caller(obj_self, req):
            try:
                value = serializer.deserialize(req.payload, param_type)
                result = function(obj_self, value)
                return parse_resp(result)
            except Exception as e:
                return self._create_error_response(e, param_type)
        return caller
```

### 3. Comprehensive Type Support

Support all the types that state management supports:

#### 3.1 Basic Types
- `int`, `float`, `str`, `bool`
- `bytes`
- `None`

#### 3.2 Collection Types
- `List[T]` with element type conversion
- `Dict[K, V]` with key/value type conversion
- `Tuple[T, ...]`
- `Set[T]`

#### 3.3 Optional/Union Types
- `Optional[T]` (Union[T, None])
- `Union[T1, T2, ...]`

#### 3.4 DateTime/UUID Types
- `datetime` with ISO format
- `UUID` with string conversion

#### 3.5 Pydantic Models
- Full Pydantic model support
- Nested model validation
- Custom validators

#### 3.6 Complex Types
- Nested data structures
- Custom classes with `__dict__`
- Enum types

### 4. Error Handling Enhancement

Implement comprehensive error handling:

```python
class RpcSerializationError(Exception):
    """Enhanced RPC serialization error."""
    def __init__(self, message: str, error_code: str, details: Dict[str, Any]):
        self.error_code = error_code
        self.details = details
        super().__init__(message)

def _create_error_response(self, error: Exception, param_type: Type) -> InvocationResponse:
    """Create detailed error response."""
    error_details = {
        'error_type': type(error).__name__,
        'parameter_type': param_type.__name__ if param_type else 'unknown',
        'error_message': str(error)
    }
    
    return InvocationResponse(
        status=int(InvocationResponseCode.AppError),
        payload=json.dumps(error_details).encode()
    )
```

### 5. Performance Optimization

Add performance monitoring to RPC serialization:

```python
class RpcPerformanceMetrics:
    """Performance metrics for RPC serialization."""
    
    def __init__(self):
        self.serialization_metrics = PerformanceMetrics()
        self.deserialization_metrics = PerformanceMetrics()
        
    def record_serialization(self, duration: float, success: bool, data_size: int):
        """Record serialization performance."""
        
    def record_deserialization(self, duration: float, success: bool, data_size: int):
        """Record deserialization performance."""
```

## Implementation Plan

### Phase 1: Core Serialization System

1. **Create `UnifiedSerializer` class**
   - Extract serialization logic from `StateDescriptor`
   - Make it reusable for both RPC and state management
   - Add comprehensive type support

2. **Enhance `parse_resp` function**
   - Support all return types
   - Add error handling
   - Add performance monitoring

### Phase 2: Enhanced RPC Parameter Processing

1. **Extend `_create_single_param_caller`**
   - Support all types from `StateDescriptor`
   - Add type validation
   - Add error handling

2. **Create specialized callers for complex types**
   - datetime/UUID support
   - Union/Optional support
   - Nested model support

### Phase 3: Error Handling and Validation

1. **Implement `RpcSerializationError`**
   - Detailed error context
   - Error codes for different scenarios
   - User-friendly error messages

2. **Add parameter validation**
   - Type checking before deserialization
   - Range/constraint validation
   - Custom validation support

### Phase 4: Performance and Monitoring

1. **Add `RpcPerformanceMetrics`**
   - Track serialization/deserialization performance
   - Monitor error rates
   - Memory usage tracking

2. **Integration with debug system**
   - Detailed logging
   - Performance tracing
   - Error tracking

## Test Requirements Enhancement

### 1. Comprehensive Type Tests

```python
# Test all basic types
@pytest.mark.parametrize("value,expected_type", [
    (42, int),
    (3.14, float),
    ("hello", str),
    (True, bool),
    (b"binary", bytes),
    ([1, 2, 3], list),
    ({"key": "value"}, dict),
])
async def test_basic_types(setup_oaas, value, expected_type):
    """Test all basic parameter types."""
```

### 2. Complex Type Tests

```python
# Test datetime/UUID
async def test_datetime_uuid_types(setup_oaas):
    """Test datetime and UUID parameter types."""
    
# Test Union/Optional
async def test_union_optional_types(setup_oaas):
    """Test Union and Optional parameter types."""
    
# Test nested models
async def test_nested_pydantic_models(setup_oaas):
    """Test nested Pydantic model parameters."""
```

### 3. Error Handling Tests

```python
# Test type validation errors
async def test_type_validation_errors(setup_oaas):
    """Test parameter type validation errors."""
    
# Test serialization errors
async def test_serialization_errors(setup_oaas):
    """Test various serialization error scenarios."""
```

### 4. Performance Tests

```python
# Test performance with large data
async def test_large_data_performance(setup_oaas):
    """Test RPC performance with large data structures."""
    
# Test concurrent serialization
async def test_concurrent_serialization(setup_oaas):
    """Test concurrent RPC calls with complex data."""
```

## Migration Strategy

### 1. Backward Compatibility
- Keep existing RPC parameter handling working
- Add new enhanced handling as opt-in
- Gradual migration path

### 2. Feature Flags
- Enable enhanced serialization per service
- Allow fallback to legacy behavior
- Performance comparison tools

### 3. Documentation
- Update reference documentation
- Add migration guide
- Performance optimization guide

## Expected Benefits

1. **Consistency**: Same type support across RPC and state management
2. **Robustness**: Comprehensive error handling and validation
3. **Performance**: Optimized serialization with monitoring
4. **Developer Experience**: Better error messages and debugging
5. **Flexibility**: Support for complex data structures and custom types

This enhanced serialization system will provide a solid foundation for comprehensive RPC testing and ensure the OaaS SDK can handle any data type that Python developers need to use.