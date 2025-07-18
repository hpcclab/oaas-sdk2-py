"""
Comprehensive RPC System Tests

Tests the enhanced RPC system with the unified serialization system,
focusing on the single parameter constraint and comprehensive type support.
"""

import pytest
import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, field_validator

from oaas_sdk2_py import oaas, OaasObject, OaasConfig
from oaas_sdk2_py.simplified.serialization import SerializationError, ValidationError


# Test Models for RPC
class MyRequest(BaseModel):
    value: int
    
class MyResponse(BaseModel):
    result: int


class ComplexRequest(BaseModel):
    user_id: int
    operation: str
    parameters: Dict[str, Any]
    metadata: Optional[Dict[str, str]] = None
    

class ComplexResponse(BaseModel):
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float


class NestedData(BaseModel):
    values: List[int]
    metadata: Dict[str, str]
    

class NestedRequest(BaseModel):
    data: NestedData
    operation: str
    

class NestedResponse(BaseModel):
    processed_data: NestedData
    summary: Dict[str, Any]


class ValidationRequest(BaseModel):
    required_field: str
    optional_field: Optional[int] = None
    
    @field_validator('required_field')
    @classmethod
    def validate_required(cls, v):
        if not v.strip():
            raise ValueError("required_field cannot be empty")
        return v


class TypeTestRequest(BaseModel):
    int_val: int
    float_val: float
    bool_val: bool
    str_val: str
    list_val: List[int]
    dict_val: Dict[str, Any]
    optional_val: Optional[str] = None
    union_val: Union[int, str]
    datetime_val: datetime
    uuid_val: UUID


class TypeTestResponse(BaseModel):
    processed: bool
    type_summary: Dict[str, str]
    timestamp: datetime


# Test Services
@oaas.service("SingleParamService", package="test")
class SingleParamService(OaasObject):
    """Service testing single parameter patterns."""
    
    @oaas.method()
    async def valid_int(self, value: int) -> int:
        return value * 2
    
    @oaas.method()
    async def valid_str(self, text: str) -> str:
        return f"Hello {text}"
    
    @oaas.method()
    async def valid_dict(self, data: dict) -> dict:
        return {"received": data, "timestamp": datetime.now().isoformat()}
    
    @oaas.method()
    async def valid_model(self, request: MyRequest) -> MyResponse:
        return MyResponse(result=request.value * 3)
    
    @oaas.method()
    async def no_params(self) -> str:
        return "no parameters needed"


@oaas.service("ComplexRPCService", package="test")  
class ComplexRPCService(OaasObject):
    """Service testing complex Pydantic model RPC."""
    
    @oaas.method()
    async def complex_operation(self, request: ComplexRequest) -> ComplexResponse:
        start_time = time.time()
        try:
            # Simulate complex processing
            result = self._process_operation(request.operation, request.parameters)
            execution_time = time.time() - start_time
            
            return ComplexResponse(
                success=True,
                result=result,
                execution_time=execution_time
            )
        except Exception as e:
            return ComplexResponse(
                success=False,
                result=None,  # Provide required result field
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def _process_operation(self, operation: str, parameters: Dict[str, Any]) -> Any:
        """Simulate operation processing."""
        if operation == "math":
            return parameters.get("x", 0) + parameters.get("y", 0)
        elif operation == "string":
            return f"Processed: {parameters.get('text', '')}"
        elif operation == "list":
            return [x * 2 for x in parameters.get("values", [])]
        else:
            raise ValueError(f"Unknown operation: {operation}")


@oaas.service("NestedRPCService", package="test")
class NestedRPCService(OaasObject):
    """Service testing nested Pydantic models."""
    
    @oaas.method()
    async def process_nested(self, request: NestedRequest) -> NestedResponse:
        # Process nested data structure
        processed = NestedData(
            values=[v * 2 for v in request.data.values],
            metadata={**request.data.metadata, "processed": "true"}
        )
        
        return NestedResponse(
            processed_data=processed,
            summary={
                "operation": request.operation,
                "original_count": len(request.data.values),
                "processed_count": len(processed.values)
            }
        )


@oaas.service("DictRPCService", package="test")
class DictRPCService(OaasObject):
    """Service testing dictionary-based parameters."""
    
    @oaas.method()
    async def dict_math(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle math operations via dictionary."""
        operation = params.get("operation")
        x = params.get("x", 0)
        y = params.get("y", 0)
        
        if operation == "add":
            result = x + y
        elif operation == "multiply":
            result = x * y
        elif operation == "subtract":
            result = x - y
        else:
            result = None
            
        return {
            "operation": operation,
            "x": x,
            "y": y,
            "result": result,
            "success": result is not None
        }
    
    @oaas.method()
    async def dict_batch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch operations via dictionary."""
        operations = params.get("operations", [])
        results = []
        
        for op in operations:
            # Each operation is a dictionary
            result = await self.dict_math(op)
            results.append(result)
            
        return {
            "batch_size": len(operations),
            "results": results,
            "all_successful": all(r.get("success") for r in results)
        }


@oaas.service("SerializationRPCService", package="test")
class SerializationRPCService(OaasObject):
    """Service testing serialization through RPC."""
    
    @oaas.method()
    async def test_primitives(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test primitive type serialization."""
        return {
            "int_value": data.get("int_val", 0),
            "float_value": data.get("float_val", 0.0),
            "bool_value": data.get("bool_val", False),
            "str_value": data.get("str_val", ""),
            "received_types": {k: type(v).__name__ for k, v in data.items()}
        }
    
    @oaas.method()
    async def test_collections(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test collection type serialization."""
        return {
            "list_length": len(data.get("list_val", [])),
            "dict_keys": list(data.get("dict_val", {}).keys()),
            "nested_access": data.get("nested", {}).get("deep", "not_found"),
            "collection_types": {
                "list_type": type(data.get("list_val", [])).__name__,
                "dict_type": type(data.get("dict_val", {})).__name__
            }
        }
    
    @oaas.method()
    async def test_bytes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test bytes serialization."""
        bytes_data = data.get("bytes_val", b"")
        if isinstance(bytes_data, bytes):
            decoded = bytes_data.decode('utf-8')
        else:
            decoded = str(bytes_data)
            
        return {
            "original_type": type(bytes_data).__name__,
            "decoded_value": decoded,
            "length": len(bytes_data)
        }
    
    @oaas.method()
    async def test_complex_types(self, request: TypeTestRequest) -> TypeTestResponse:
        """Test comprehensive type serialization."""
        type_summary = {
            "int_type": type(request.int_val).__name__,
            "float_type": type(request.float_val).__name__,
            "bool_type": type(request.bool_val).__name__,
            "str_type": type(request.str_val).__name__,
            "list_type": type(request.list_val).__name__,
            "dict_type": type(request.dict_val).__name__,
            "datetime_type": type(request.datetime_val).__name__,
            "uuid_type": type(request.uuid_val).__name__
        }
        
        return TypeTestResponse(
            processed=True,
            type_summary=type_summary,
            timestamp=datetime.now()
        )


@oaas.service("ValidationRPCService", package="test")
class ValidationRPCService(OaasObject):
    """Service testing validation through RPC."""
    
    @oaas.method()
    async def validate_request(self, request: ValidationRequest) -> Dict[str, Any]:
        """Test Pydantic validation in RPC."""
        return {
            "valid": True,
            "required_field": request.required_field,
            "optional_field": request.optional_field
        }
    
    @oaas.method()
    async def validate_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test manual validation with dictionary."""
        errors = []
        
        if "required_field" not in data:
            errors.append("required_field is missing")
        elif not data["required_field"].strip():
            errors.append("required_field cannot be empty")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "data": data
        }


# Test Classes
class TestBasicRPC:
    """Test basic RPC functionality with single parameters."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_single_parameter_int(self):
        """Test RPC with single integer parameter."""
        service = SingleParamService.create(obj_id=1)
        
        result = await service.valid_int(42)
        assert result == 84
    
    @pytest.mark.asyncio
    async def test_single_parameter_string(self):
        """Test RPC with single string parameter."""
        service = SingleParamService.create(obj_id=1)
        
        result = await service.valid_str("World")
        assert result == "Hello World"
    
    @pytest.mark.asyncio
    async def test_single_parameter_dict(self):
        """Test RPC with single dictionary parameter."""
        service = SingleParamService.create(obj_id=1)
        
        test_data = {"key": "value", "number": 42}
        result = await service.valid_dict(test_data)
        
        assert result["received"] == test_data
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_single_parameter_pydantic_model(self):
        """Test RPC with single Pydantic model parameter."""
        service = SingleParamService.create(obj_id=1)
        
        request = MyRequest(value=100)
        result = await service.valid_model(request)
        
        assert isinstance(result, MyResponse)
        assert result.result == 300
    
    @pytest.mark.asyncio
    async def test_no_parameters(self):
        """Test RPC with no parameters."""
        service = SingleParamService.create(obj_id=1)
        
        result = await service.no_params()
        assert result == "no parameters needed"


class TestComplexRPC:
    """Test complex RPC scenarios with Pydantic models."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_complex_operation_math(self):
        """Test complex operation with math."""
        service = ComplexRPCService.create(obj_id=1)
        
        request = ComplexRequest(
            user_id=123,
            operation="math",
            parameters={"x": 10, "y": 20},
            metadata={"client": "test"}
        )
        
        result = await service.complex_operation(request)
        
        assert isinstance(result, ComplexResponse)
        assert result.success is True
        assert result.result == 30
        assert result.error is None
        assert result.execution_time >= 0
    
    @pytest.mark.asyncio
    async def test_complex_operation_string(self):
        """Test complex operation with string processing."""
        service = ComplexRPCService.create(obj_id=1)
        
        request = ComplexRequest(
            user_id=456,
            operation="string",
            parameters={"text": "Hello World"}
        )
        
        result = await service.complex_operation(request)
        
        assert result.success is True
        assert result.result == "Processed: Hello World"
    
    @pytest.mark.asyncio
    async def test_complex_operation_list(self):
        """Test complex operation with list processing."""
        service = ComplexRPCService.create(obj_id=1)
        
        request = ComplexRequest(
            user_id=789,
            operation="list",
            parameters={"values": [1, 2, 3, 4, 5]}
        )
        
        result = await service.complex_operation(request)
        
        assert result.success is True
        assert result.result == [2, 4, 6, 8, 10]
    
    @pytest.mark.asyncio
    async def test_complex_operation_error(self):
        """Test complex operation error handling."""
        service = ComplexRPCService.create(obj_id=1)
        
        request = ComplexRequest(
            user_id=999,
            operation="unknown",
            parameters={}
        )
        
        result = await service.complex_operation(request)
        
        assert result.success is False
        assert "Unknown operation" in result.error
        assert result.execution_time >= 0


class TestNestedRPC:
    """Test nested Pydantic model RPC."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_nested_processing(self):
        """Test nested data structure processing."""
        service = NestedRPCService.create(obj_id=1)
        
        nested_data = NestedData(
            values=[1, 2, 3, 4],
            metadata={"source": "test", "version": "1.0"}
        )
        
        request = NestedRequest(
            data=nested_data,
            operation="double"
        )
        
        result = await service.process_nested(request)
        
        assert isinstance(result, NestedResponse)
        assert result.processed_data.values == [2, 4, 6, 8]
        assert result.processed_data.metadata["source"] == "test"
        assert result.processed_data.metadata["processed"] == "true"
        assert result.summary["operation"] == "double"
        assert result.summary["original_count"] == 4
        assert result.summary["processed_count"] == 4


class TestDictionaryRPC:
    """Test dictionary-based RPC parameters."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_dict_math_add(self):
        """Test dictionary math operation - addition."""
        service = DictRPCService.create(obj_id=1)
        
        result = await service.dict_math({
            "operation": "add",
            "x": 10,
            "y": 15
        })
        
        assert result["operation"] == "add"
        assert result["x"] == 10
        assert result["y"] == 15
        assert result["result"] == 25
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_dict_math_multiply(self):
        """Test dictionary math operation - multiplication."""
        service = DictRPCService.create(obj_id=1)
        
        result = await service.dict_math({
            "operation": "multiply",
            "x": 7,
            "y": 8
        })
        
        assert result["result"] == 56
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_dict_math_unknown(self):
        """Test dictionary math operation - unknown operation."""
        service = DictRPCService.create(obj_id=1)
        
        result = await service.dict_math({
            "operation": "divide",
            "x": 10,
            "y": 2
        })
        
        assert result["result"] is None
        assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_dict_batch_operations(self):
        """Test batch operations via dictionary."""
        service = DictRPCService.create(obj_id=1)
        
        result = await service.dict_batch({
            "operations": [
                {"operation": "add", "x": 5, "y": 3},
                {"operation": "multiply", "x": 4, "y": 6},
                {"operation": "subtract", "x": 10, "y": 4}
            ]
        })
        
        assert result["batch_size"] == 3
        assert len(result["results"]) == 3
        assert result["results"][0]["result"] == 8
        assert result["results"][1]["result"] == 24
        assert result["results"][2]["result"] == 6
        assert result["all_successful"] is True


class TestSerializationRPC:
    """Test serialization through RPC calls."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_primitive_serialization(self):
        """Test primitive type serialization through RPC."""
        service = SerializationRPCService.create(obj_id=1)
        
        result = await service.test_primitives({
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "str_val": "test string"
        })
        
        assert result["int_value"] == 42
        assert result["float_value"] == 3.14
        assert result["bool_value"] is True
        assert result["str_value"] == "test string"
        assert result["received_types"]["int_val"] == "int"
        assert result["received_types"]["float_val"] == "float"
        assert result["received_types"]["bool_val"] == "bool"
        assert result["received_types"]["str_val"] == "str"
    
    @pytest.mark.asyncio
    async def test_collection_serialization(self):
        """Test collection type serialization through RPC."""
        service = SerializationRPCService.create(obj_id=1)
        
        result = await service.test_collections({
            "list_val": [1, 2, 3, 4],
            "dict_val": {"key1": "value1", "key2": "value2"},
            "nested": {"deep": "found"}
        })
        
        assert result["list_length"] == 4
        assert set(result["dict_keys"]) == {"key1", "key2"}
        assert result["nested_access"] == "found"
        assert result["collection_types"]["list_type"] == "list"
        assert result["collection_types"]["dict_type"] == "dict"
    
    @pytest.mark.asyncio
    async def test_bytes_serialization(self):
        """Test bytes serialization through RPC."""
        service = SerializationRPCService.create(obj_id=1)
        
        test_bytes = "Hello World".encode('utf-8')
        result = await service.test_bytes({
            "bytes_val": test_bytes
        })
        
        assert result["decoded_value"] == "Hello World"
        assert result["length"] == len(test_bytes)
        # Note: bytes might be serialized differently in mock mode
    
    @pytest.mark.asyncio
    async def test_comprehensive_type_serialization(self):
        """Test comprehensive type serialization through Pydantic model."""
        service = SerializationRPCService.create(obj_id=1)
        
        request = TypeTestRequest(
            int_val=42,
            float_val=3.14,
            bool_val=True,
            str_val="test",
            list_val=[1, 2, 3],
            dict_val={"key": "value"},
            optional_val="optional",
            union_val=100,
            datetime_val=datetime.now(),
            uuid_val=uuid4()
        )
        
        result = await service.test_complex_types(request)
        
        assert isinstance(result, TypeTestResponse)
        assert result.processed is True
        assert result.type_summary["int_type"] == "int"
        assert result.type_summary["float_type"] == "float"
        assert result.type_summary["bool_type"] == "bool"
        assert result.type_summary["str_type"] == "str"
        assert result.type_summary["list_type"] == "list"
        assert result.type_summary["dict_type"] == "dict"
        assert result.type_summary["datetime_type"] == "datetime"
        assert result.type_summary["uuid_type"] == "UUID"
        assert isinstance(result.timestamp, datetime)


class TestValidationRPC:
    """Test validation through RPC calls."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_valid_pydantic_request(self):
        """Test valid Pydantic request validation."""
        service = ValidationRPCService.create(obj_id=1)
        
        request = ValidationRequest(
            required_field="valid value",
            optional_field=42
        )
        
        result = await service.validate_request(request)
        
        assert result["valid"] is True
        assert result["required_field"] == "valid value"
        assert result["optional_field"] == 42
    
    @pytest.mark.asyncio
    async def test_invalid_pydantic_request(self):
        """Test invalid Pydantic request validation."""
        service = ValidationRPCService.create(obj_id=1)
        
        # This should raise a validation error
        with pytest.raises((ValueError, ValidationError)):
            ValidationRequest(required_field="")  # Empty string should fail validation
    
    @pytest.mark.asyncio
    async def test_valid_dict_validation(self):
        """Test valid dictionary validation."""
        service = ValidationRPCService.create(obj_id=1)
        
        result = await service.validate_dict({
            "required_field": "valid value",
            "optional_field": 42
        })
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_invalid_dict_validation(self):
        """Test invalid dictionary validation."""
        service = ValidationRPCService.create(obj_id=1)
        
        # Missing required field
        result = await service.validate_dict({
            "optional_field": 42
        })
        
        assert result["valid"] is False
        assert "required_field is missing" in result["errors"]
        
        # Empty required field
        result = await service.validate_dict({
            "required_field": "   ",
            "optional_field": 42
        })
        
        assert result["valid"] is False
        assert "required_field cannot be empty" in result["errors"]


class TestPerformanceRPC:
    """Test RPC performance with single parameters."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_primitive_performance(self):
        """Test primitive type RPC performance."""
        service = SerializationRPCService.create(obj_id=1)
        
        start_time = time.time()
        for i in range(50):  # Reduced for faster tests
            await service.test_primitives({
                "int_val": i,
                "float_val": i * 1.5,
                "bool_val": i % 2 == 0,
                "str_val": f"test_{i}"
            })
        primitive_time = time.time() - start_time
        
        # Performance should be reasonable (under 2 seconds for 50 calls in mock mode)
        assert primitive_time < 2.0
    
    @pytest.mark.asyncio
    async def test_complex_model_performance(self):
        """Test complex Pydantic model RPC performance."""
        service = ComplexRPCService.create(obj_id=1)
        
        start_time = time.time()
        for i in range(50):  # Reduced for faster tests
            request = ComplexRequest(
                user_id=i,
                operation="math",
                parameters={"x": i, "y": i * 2}
            )
            await service.complex_operation(request)
        model_time = time.time() - start_time
        
        # Performance should be reasonable (under 3 seconds for 50 calls in mock mode)
        assert model_time < 3.0
    
    @pytest.mark.asyncio
    async def test_batch_operation_performance(self):
        """Test batch operation performance."""
        service = DictRPCService.create(obj_id=1)
        
        # Create a large batch operation
        operations = [
            {"operation": "add", "x": i, "y": i * 2}
            for i in range(100)
        ]
        
        start_time = time.time()
        result = await service.dict_batch({"operations": operations})
        batch_time = time.time() - start_time
        
        assert result["batch_size"] == 100
        assert result["all_successful"] is True
        # Should handle 100 operations in reasonable time
        assert batch_time < 5.0


class TestCrossServiceRPC:
    """Test RPC communication between services."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
    
    @pytest.mark.asyncio
    async def test_cross_service_communication(self):
        """Test RPC between different services."""
        math_service = DictRPCService.create(obj_id=1)
        validation_service = ValidationRPCService.create(obj_id=2)
        
        # Get result from math service
        math_result = await math_service.dict_math({
            "operation": "multiply",
            "x": 6,
            "y": 7
        })
        assert math_result["result"] == 42
        
        # Use math result in validation service
        validation_result = await validation_service.validate_dict({
            "required_field": f"Result: {math_result['result']}",
            "optional_field": math_result["result"]
        })
        
        assert validation_result["valid"] is True
        assert validation_result["data"]["required_field"] == "Result: 42"
        assert validation_result["data"]["optional_field"] == 42
    
    @pytest.mark.asyncio
    async def test_complex_service_chain(self):
        """Test complex chain of service calls."""
        dict_service = DictRPCService.create(obj_id=1)
        complex_service = ComplexRPCService.create(obj_id=2)
        nested_service = NestedRPCService.create(obj_id=3)
        
        # Step 1: Batch math operations
        batch_result = await dict_service.dict_batch({
            "operations": [
                {"operation": "add", "x": 10, "y": 5},
                {"operation": "multiply", "x": 3, "y": 4}
            ]
        })
        
        # Step 2: Use results in complex operation
        values = [r["result"] for r in batch_result["results"]]
        complex_result = await complex_service.complex_operation(
            ComplexRequest(
                user_id=1,
                operation="list",
                parameters={"values": values}
            )
        )
        
        # Step 3: Process in nested service
        nested_data = NestedData(
            values=complex_result.result,
            metadata={"source": "batch", "operation_count": str(batch_result["batch_size"])}
        )
        
        nested_result = await nested_service.process_nested(
            NestedRequest(data=nested_data, operation="final")
        )
        
        # Verify the entire chain
        assert len(nested_result.processed_data.values) == 2
        assert nested_result.processed_data.values == [60, 48]  # [(15*2)*2, (12*2)*2]
        assert nested_result.summary["operation"] == "final"


# Integration test to run all RPC tests
@pytest.mark.asyncio
async def test_comprehensive_rpc_integration():
    """Comprehensive integration test for the entire RPC system."""
    config = OaasConfig(mock_mode=True)
    oaas.configure(config)
    
    # Test all service types
    services = {
        'single': SingleParamService.create(obj_id=1),
        'complex': ComplexRPCService.create(obj_id=2),
        'nested': NestedRPCService.create(obj_id=3),
        'dict': DictRPCService.create(obj_id=4),
        'serialization': SerializationRPCService.create(obj_id=5),
        'validation': ValidationRPCService.create(obj_id=6)
    }
    
    # Test basic functionality of each service
    results = {}
    
    # Single param service
    results['single_int'] = await services['single'].valid_int(10)
    results['single_str'] = await services['single'].valid_str("test")
    
    # Complex service
    results['complex'] = await services['complex'].complex_operation(
        ComplexRequest(user_id=1, operation="math", parameters={"x": 5, "y": 10})
    )
    
    # Dictionary service
    results['dict'] = await services['dict'].dict_math({
        "operation": "add", "x": 3, "y": 7
    })
    
    # Serialization service
    results['serialization'] = await services['serialization'].test_primitives({
        "int_val": 42, "str_val": "hello"
    })
    
    # Validation service  
    results['validation'] = await services['validation'].validate_dict({
        "required_field": "valid"
    })
    
    # Verify all results
    assert results['single_int'] == 20
    assert results['single_str'] == "Hello test"
    assert results['complex'].success is True
    assert results['complex'].result == 15
    assert results['dict']['result'] == 10
    assert results['serialization']['int_value'] == 42
    assert results['validation']['valid'] is True
    
    print("✅ All RPC integration tests passed!")


if __name__ == "__main__":
    # Run a quick integration test
    asyncio.run(test_comprehensive_rpc_integration())