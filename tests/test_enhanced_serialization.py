"""
Comprehensive tests for the enhanced serialization system.

This test suite covers all aspects of the unified serialization system
including basic types, complex types, error handling, and performance.
"""

import pytest
import json
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Optional, Union, Tuple, Set
from pydantic import BaseModel

from oaas_sdk2_py.simplified.serialization import (
    UnifiedSerializer, 
    RpcSerializationError, 
    RpcPerformanceMetrics
)
from oaas_sdk2_py.simplified.errors import SerializationError, ValidationError


class SampleModel(BaseModel):
    """Test Pydantic model for serialization testing."""
    id: int
    name: str
    value: float
    active: bool


class NestedTestModel(BaseModel):
    """Test nested Pydantic model."""
    model: SampleModel
    tags: List[str]
    metadata: Dict[str, str]


class TestUnifiedSerializer:
    """Test suite for the UnifiedSerializer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = UnifiedSerializer()
    
    @pytest.mark.parametrize("value,expected_type", [
        (42, int),
        (3.14, float),
        ("hello", str),
        (True, bool),
        (b"binary", bytes),
        ([1, 2, 3], list),
        ({"key": "value"}, dict),
    ])
    def test_basic_types_serialization(self, value, expected_type):
        """Test serialization of all basic parameter types."""
        # Test serialization
        serialized = self.serializer.serialize(value, expected_type)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, expected_type)
        assert deserialized == value
        assert isinstance(deserialized, expected_type)
    
    def test_none_value_handling(self):
        """Test handling of None values."""
        # Test serialization of None
        serialized = self.serializer.serialize(None)
        assert serialized == b""
        
        # Test deserialization to None
        deserialized = self.serializer.deserialize(b"", Optional[str])
        assert deserialized is None
    
    def test_datetime_serialization(self):
        """Test datetime serialization and deserialization."""
        dt = datetime(2023, 12, 25, 15, 30, 45)
        
        # Test serialization
        serialized = self.serializer.serialize(dt, datetime)
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, datetime)
        assert isinstance(deserialized, datetime)
        assert deserialized == dt
    
    def test_uuid_serialization(self):
        """Test UUID serialization and deserialization."""
        uuid_val = UUID("12345678-1234-5678-1234-567812345678")
        
        # Test serialization
        serialized = self.serializer.serialize(uuid_val, UUID)
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, UUID)
        assert isinstance(deserialized, UUID)
        assert deserialized == uuid_val
    
    def test_list_type_serialization(self):
        """Test List[T] serialization with element type conversion."""
        test_data = [1, 2, 3, 4, 5]
        
        # Test serialization
        serialized = self.serializer.serialize(test_data, List[int])
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, List[int])
        assert isinstance(deserialized, list)
        assert deserialized == test_data
        assert all(isinstance(x, int) for x in deserialized)
    
    def test_dict_type_serialization(self):
        """Test Dict[K, V] serialization with key/value type conversion."""
        test_data = {"key1": "value1", "key2": "value2"}
        
        # Test serialization
        serialized = self.serializer.serialize(test_data, Dict[str, str])
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, Dict[str, str])
        assert isinstance(deserialized, dict)
        assert deserialized == test_data
    
    def test_tuple_type_serialization(self):
        """Test Tuple serialization."""
        test_data = (1, "hello", 3.14)
        
        # Test serialization
        serialized = self.serializer.serialize(test_data, Tuple[int, str, float])
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, Tuple[int, str, float])
        assert isinstance(deserialized, tuple)
        assert deserialized == test_data
    
    def test_set_type_serialization(self):
        """Test Set serialization."""
        test_data = {1, 2, 3, 4, 5}
        
        # Test serialization
        serialized = self.serializer.serialize(test_data, Set[int])
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, Set[int])
        assert isinstance(deserialized, set)
        assert deserialized == test_data
    
    def test_optional_type_serialization(self):
        """Test Optional[T] type serialization."""
        # Test with value
        test_value = "hello"
        serialized = self.serializer.serialize(test_value, Optional[str])
        deserialized = self.serializer.deserialize(serialized, Optional[str])
        assert deserialized == test_value
        
        # Test with None
        serialized = self.serializer.serialize(None, Optional[str])
        deserialized = self.serializer.deserialize(serialized, Optional[str])
        assert deserialized is None
    
    def test_union_type_serialization(self):
        """Test Union type serialization."""
        # Test with int
        test_value = 42
        serialized = self.serializer.serialize(test_value, Union[int, str])
        deserialized = self.serializer.deserialize(serialized, Union[int, str])
        assert deserialized == test_value
        
        # Test with str
        test_value = "hello"
        serialized = self.serializer.serialize(test_value, Union[int, str])
        deserialized = self.serializer.deserialize(serialized, Union[int, str])
        assert deserialized == test_value
    
    def test_pydantic_model_serialization(self):
        """Test Pydantic model serialization."""
        model = SampleModel(id=1, name="test", value=3.14, active=True)
        
        # Test serialization
        serialized = self.serializer.serialize(model, SampleModel)
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, SampleModel)
        assert isinstance(deserialized, SampleModel)
        assert deserialized.id == model.id
        assert deserialized.name == model.name
        assert deserialized.value == model.value
        assert deserialized.active == model.active
    
    def test_nested_pydantic_model_serialization(self):
        """Test nested Pydantic model serialization."""
        inner_model = SampleModel(id=1, name="inner", value=2.71, active=True)
        nested_model = NestedTestModel(
            model=inner_model,
            tags=["tag1", "tag2"],
            metadata={"key": "value"}
        )
        
        # Test serialization
        serialized = self.serializer.serialize(nested_model, NestedTestModel)
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, NestedTestModel)
        assert isinstance(deserialized, NestedTestModel)
        assert deserialized.model.id == inner_model.id
        assert deserialized.tags == ["tag1", "tag2"]
        assert deserialized.metadata == {"key": "value"}
    
    def test_complex_nested_structure(self):
        """Test complex nested data structures."""
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice", "roles": ["admin", "user"]},
                {"id": 2, "name": "Bob", "roles": ["user"]},
            ],
            "metadata": {
                "version": "1.0",
                "created": "2023-12-25T15:30:45",
                "active": True
            }
        }
        
        # Test serialization
        serialized = self.serializer.serialize(complex_data, Dict)
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, Dict)
        assert isinstance(deserialized, dict)
        assert deserialized == complex_data
    
    def test_type_conversion(self):
        """Test convert_value method with various conversions."""
        # Test int to str conversion
        result = self.serializer.convert_value(42, str)
        assert result == "42"
        assert isinstance(result, str)
        
        # Test str to int conversion
        result = self.serializer.convert_value("123", int)
        assert result == 123
        assert isinstance(result, int)
        
        # Test list to tuple conversion
        result = self.serializer.convert_value([1, 2, 3], tuple)
        assert result == (1, 2, 3)
        assert isinstance(result, tuple)
    
    def test_serialization_error_handling(self):
        """Test error handling in serialization."""
        # Test invalid serialization
        with pytest.raises(SerializationError):
            # Try to serialize an object that can't be serialized
            class UnserializableClass:
                def __init__(self):
                    self.circular_ref = self
            
            obj = UnserializableClass()
            self.serializer.serialize(obj, UnserializableClass)
    
    def test_deserialization_error_handling(self):
        """Test error handling in deserialization."""
        # Test invalid JSON data
        with pytest.raises(SerializationError):
            self.serializer.deserialize(b"invalid json", dict)
        
        # Test type mismatch
        with pytest.raises(SerializationError):
            self.serializer.deserialize(b'"string"', int)
    
    def test_type_validation_errors(self):
        """Test parameter type validation errors."""
        # Test invalid datetime format
        with pytest.raises(ValidationError):
            self.serializer.convert_value("invalid-date", datetime)
        
        # Test invalid UUID format
        with pytest.raises(ValidationError):
            self.serializer.convert_value("invalid-uuid", UUID)
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        from oaas_sdk2_py.simplified.errors import get_debug_context
        
        # Enable performance monitoring
        debug_ctx = get_debug_context()
        debug_ctx.performance_monitoring = True
        
        # Ensure metrics are being collected
        metrics = self.serializer.get_performance_metrics()
        assert isinstance(metrics, RpcPerformanceMetrics)
        
        # Test some operations to generate metrics
        test_data = {"key": "value", "number": 42}
        serialized = self.serializer.serialize(test_data, Dict)
        deserialized = self.serializer.deserialize(serialized, Dict)
        
        # Verify metrics were recorded
        assert metrics.serialization_metrics.call_count > 0
        assert metrics.deserialization_metrics.call_count > 0
    
    def test_large_data_performance(self):
        """Test RPC performance with large data structures."""
        # Create large data structure
        large_data = {
            "items": [{"id": i, "data": f"data_{i}" * 100} for i in range(1000)],
            "metadata": {"count": 1000, "size": "large"}
        }
        
        # Test serialization performance
        serialized = self.serializer.serialize(large_data, Dict)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 10000  # Should be substantial
        
        # Test deserialization performance
        deserialized = self.serializer.deserialize(serialized, Dict)
        assert isinstance(deserialized, dict)
        assert len(deserialized["items"]) == 1000
    
    def test_concurrent_serialization(self):
        """Test concurrent RPC calls with complex data."""
        import threading
        import time
        
        results = []
        errors = []
        
        def serialize_task(data, target_type):
            try:
                serialized = self.serializer.serialize(data, target_type)
                deserialized = self.serializer.deserialize(serialized, target_type)
                results.append(deserialized)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads with different data
        threads = []
        test_cases = [
            ({"id": 1, "name": "test1"}, Dict),
            ([1, 2, 3, 4, 5], List[int]),
            (SampleModel(id=2, name="test2", value=1.5, active=False), SampleModel),
            (datetime.now(), datetime),
            (UUID("12345678-1234-5678-1234-567812345678"), UUID),
        ]
        
        for data, target_type in test_cases:
            thread = threading.Thread(target=serialize_task, args=(data, target_type))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Concurrent serialization errors: {errors}"
        assert len(results) == len(test_cases)
    
    def test_rpc_serialization_error_details(self):
        """Test detailed error information in RPC serialization errors."""
        try:
            # This should raise a validation error
            self.serializer.convert_value("invalid", int)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert hasattr(e, 'error_code')
            assert hasattr(e, 'details')
            assert e.error_code == 'TYPE_CONVERSION_ERROR'
    
    def test_backwards_compatibility(self):
        """Test that enhanced serialization maintains backward compatibility."""
        # Test that basic serialization still works as before
        basic_data = {"message": "hello", "number": 42}
        
        # Should work without type hints
        serialized = self.serializer.serialize(basic_data)
        assert isinstance(serialized, bytes)
        
        # Should work with type hints
        serialized_with_hint = self.serializer.serialize(basic_data, Dict[str, Union[str, int]])
        assert isinstance(serialized_with_hint, bytes)
        
        # Both should deserialize to the same result
        deserialized = self.serializer.deserialize(serialized, Dict)
        deserialized_with_hint = self.serializer.deserialize(serialized_with_hint, Dict)
        assert deserialized == deserialized_with_hint == basic_data
    
    def test_serialization_with_custom_types(self):
        """Test serialization with custom classes."""
        class CustomClass:
            def __init__(self, value):
                self.value = value
            
            def __eq__(self, other):
                return isinstance(other, CustomClass) and self.value == other.value
        
        custom_obj = CustomClass("test_value")
        
        # Test serialization (should use pickle fallback)
        serialized = self.serializer.serialize(custom_obj, CustomClass)
        assert isinstance(serialized, bytes)
        
        # Test deserialization
        deserialized = self.serializer.deserialize(serialized, CustomClass)
        assert isinstance(deserialized, CustomClass)
        assert deserialized.value == custom_obj.value
    
    def test_reset_performance_metrics(self):
        """Test resetting performance metrics."""
        # Generate some metrics
        self.serializer.serialize({"test": "data"}, Dict)
        
        # Get initial metrics
        metrics = self.serializer.get_performance_metrics()
        initial_count = metrics.serialization_metrics.call_count
        
        # Reset metrics
        self.serializer.reset_performance_metrics()
        
        # Verify metrics were reset
        reset_metrics = self.serializer.get_performance_metrics()
        assert reset_metrics.serialization_metrics.call_count == 0
        assert reset_metrics.deserialization_metrics.call_count == 0


class TestRpcPerformanceMetrics:
    """Test suite for RPC performance metrics."""
    
    def test_performance_metrics_recording(self):
        """Test that performance metrics are recorded correctly."""
        metrics = RpcPerformanceMetrics()
        
        # Record some operations
        metrics.record_serialization(0.001, True, 100)
        metrics.record_serialization(0.002, True, 200)
        metrics.record_deserialization(0.0015, True, 150)
        
        # Verify metrics
        assert metrics.serialization_metrics.call_count == 2
        assert metrics.deserialization_metrics.call_count == 1
        assert metrics.serialization_metrics.total_duration == 0.003
        assert metrics.deserialization_metrics.total_duration == 0.0015
    
    def test_performance_metrics_error_tracking(self):
        """Test error tracking in performance metrics."""
        metrics = RpcPerformanceMetrics()
        
        # Record successful and failed operations
        metrics.record_serialization(0.001, True, 100)
        metrics.record_serialization(0.002, False, 0)
        
        # Verify error tracking
        assert metrics.serialization_metrics.call_count == 2
        assert metrics.serialization_metrics.error_count == 1
        assert metrics.serialization_metrics.success_rate == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])