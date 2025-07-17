#!/usr/bin/env python3
"""
Comprehensive test suite for the OaaS SDK simplified interface Phase 1 Week 1 components.

This test suite provides comprehensive coverage for:
1. StateDescriptor - Automatic state persistence and serialization
2. OaasObject - Auto-serialization, state management, object lifecycle
3. OaasConfig - Configuration consolidation and backward compatibility
4. OaasService - Decorator system, service registration, method wrapping
5. Integration tests and performance benchmarks
"""

import asyncio
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


# Test imports
try:
    from oaas_sdk2_py import (
        # New simplified API
        OaasObject, OaasService, OaasConfig, oaas,
    )
    
    # Import specific components for unit testing
    from oaas_sdk2_py.simplified import StateDescriptor
    
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

# Test models
class GreetRequest(BaseModel):
    name: str

class GreetResponse(BaseModel):
    message: str

class CounterResponse(BaseModel):
    count: int

class IncrementRequest(BaseModel):
    amount: int = 1

class ComplexModel(BaseModel):
    id: int
    name: str
    tags: List[str]
    metadata: Dict[str, Any]
    timestamp: datetime
    uuid: UUID

# =============================================================================
# COMPREHENSIVE UNIT TESTS FOR FOUNDATION COMPONENTS
# =============================================================================

class TestStateDescriptor:
    """Comprehensive tests for StateDescriptor component."""
    
    def test_basic_state_descriptor_creation(self):
        """Test basic StateDescriptor creation and initialization."""
        descriptor = StateDescriptor(
            name="test_field",
            type_hint=int,
            default_value=42,
            index=0
        )
        
        assert descriptor.name == "test_field"
        assert descriptor.type_hint is int
        assert descriptor.default_value == 42
        assert descriptor.index == 0
        assert descriptor.private_name == "_state_test_field"
        print("✅ StateDescriptor basic creation test passed")
    
    def test_state_descriptor_basic_types(self):
        """Test StateDescriptor with basic Python types."""
        # Create a mock OaasObject for testing
        class MockObject:
            def __init__(self):
                self._data = {}
                
            def get_data(self, index):
                return self._data.get(index)
                
            def set_data(self, index, value):
                self._data[index] = value
        
        obj = MockObject()
        
        # Test integer descriptor
        int_desc = StateDescriptor("count", int, 0, 0)
        assert int_desc.__get__(obj) == 0
        int_desc.__set__(obj, 42)
        assert int_desc.__get__(obj) == 42
        
        # Test string descriptor
        str_desc = StateDescriptor("name", str, "", 1)
        assert str_desc.__get__(obj) == ""
        str_desc.__set__(obj, "test")
        assert str_desc.__get__(obj) == "test"
        
        # Test boolean descriptor
        bool_desc = StateDescriptor("active", bool, False, 2)
        assert not bool_desc.__get__(obj)
        bool_desc.__set__(obj, True)
        assert bool_desc.__get__(obj)
        
        print("✅ StateDescriptor basic types test passed")
    
    def test_state_descriptor_serialization(self):
        """Test StateDescriptor serialization and deserialization."""
        # Test basic type serialization
        int_desc = StateDescriptor("count", int, 0, 0)
        
        # Test serialization
        serialized = int_desc._serialize(42)
        assert serialized == b'42'
        
        # Test deserialization
        deserialized = int_desc._deserialize(b'42')
        assert deserialized == 42
        
        print("✅ StateDescriptor serialization test passed")
    
    def test_state_descriptor_type_conversion(self):
        """Test StateDescriptor type conversion capabilities."""
        int_desc = StateDescriptor("count", int, 0, 0)
        
        # Test string to int conversion
        assert int_desc._convert_value("42") == 42
        
        # Test float to int conversion
        assert int_desc._convert_value(42.5) == 42
        
        # Test bool to int conversion
        assert int_desc._convert_value(True) == 1
        
        print("✅ StateDescriptor type conversion test passed")


class TestOaasObject:
    """Comprehensive tests for OaasObject component."""
    
    def test_oaas_object_state_management(self):
        """Test OaasObject automatic state management."""
        # Configure for testing
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
        
        @oaas.service("StateTestObj", package="test")
        class StateTestObj(OaasObject):
            count: int = 0
            name: str = "default"

            @oaas.method
            async def increment(self) -> int:
                self.count += 1
                return self.count

            @oaas.method
            async def set_name(self, req: dict) -> str:
                new_name = req.get("name", "default")
                self.name = new_name
                return self.name
        
        async def test_state():
            obj = StateTestObj.create(obj_id=1)
            
            # Test initial state
            assert obj.count == 0
            assert obj.name == "default"
            
            # Test state modification
            result = await obj.increment()
            assert result == 1
            assert obj.count == 1
            
            # Test string state
            result = await obj.set_name({"name": "test"})
            assert result == "test"
            assert obj.name == "test"
            
            return True
        
        result = asyncio.run(test_state())
        assert result
        print("✅ OaasObject state management test passed")
    
    def test_oaas_object_lifecycle(self):
        """Test OaasObject lifecycle management."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
        
        @oaas.service("LifecycleTestObj", package="test")
        class LifecycleTestObj(OaasObject):
            value: int = 0
            
            @oaas.method
            async def set_value(self, req: dict) -> int:
                val = req.get("value", 0)
                self.value = val
                return self.value
        
        async def test_lifecycle():
            # Test creation
            obj1 = LifecycleTestObj.create(obj_id=1)
            await obj1.set_value({"value": 42})
            assert obj1.value == 42
            
            # Test loading (should work in mock mode)
            obj2 = LifecycleTestObj.load(obj_id=1)
            # In mock mode, this creates a new instance
            assert obj2 is not None
            
            return True
        
        result = asyncio.run(test_lifecycle())
        assert result
        print("✅ OaasObject lifecycle test passed")


class TestOaasConfig:
    """Comprehensive tests for OaasConfig component."""
    
    def test_oaas_config_creation(self):
        """Test OaasConfig creation with defaults."""
        config = OaasConfig()
        
        assert config.oprc_zenoh_peers is None
        assert config.oprc_partition_default == 0
        assert not config.mock_mode
        assert config.async_mode
        assert config.auto_commit
        assert config.batch_size == 100
        print("✅ OaasConfig creation test passed")
    
    def test_oaas_config_custom_values(self):
        """Test OaasConfig with custom values."""
        config = OaasConfig(
        
            oprc_zenoh_peers="peer1:7447,peer2:7447",
            oprc_partition_default=1,
            mock_mode=True,
            async_mode=False,
            auto_commit=False,
            batch_size=50
        )
        
        assert config.oprc_zenoh_peers == "peer1:7447,peer2:7447"
        assert config.oprc_partition_default == 1
        assert config.mock_mode
        assert not config.async_mode
        assert not config.auto_commit
        assert config.batch_size == 50
        print("✅ OaasConfig custom values test passed")
    
    def test_oaas_config_to_oprc_config(self):
        """Test OaasConfig to OprcConfig conversion."""
        config = OaasConfig(
            oprc_zenoh_peers="peer1:7447,peer2:7447",
            oprc_partition_default=1
        )
        
        oprc_config = config  # OprcConfig is now an alias for OaasConfig
    
        assert oprc_config.oprc_zenoh_peers == "peer1:7447,peer2:7447"
        assert oprc_config.oprc_partition_default == 1
        print("✅ OaasConfig to OprcConfig conversion test passed")
    
    def test_oaas_config_peer_parsing(self):
        """Test OaasConfig peer parsing."""
        config = OaasConfig(oprc_zenoh_peers="peer1:7447,peer2:7447,peer3:7447")
        
        peers = config.get_zenoh_peers()
        assert peers == ["peer1:7447", "peer2:7447", "peer3:7447"]
        
        # Test None peers
        config_none = OaasConfig(oprc_zenoh_peers=None)
        assert config_none.get_zenoh_peers() is None
        print("✅ OaasConfig peer parsing test passed")


class TestOaasService:
    """Comprehensive tests for OaasService component."""
    
    def test_oaas_service_registration(self):
        """Test service registration and retrieval."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
        
        @oaas.service("TestServiceReg", package="test")
        class TestServiceReg(OaasObject):
            @oaas.method
            async def test_method(self) -> str:
                return "test"
        
        # Test service is registered
        service = oaas.get_service("TestServiceReg", "test")
        assert service is not None
        assert service == TestServiceReg
        
        # Test service listing
        services = oaas.list_services()
        assert "test.TestServiceReg" in services
        print("✅ OaasService registration test passed")
    
    def test_oaas_service_global_configuration(self):
        """Test global service configuration."""
        config = OaasConfig(
            mock_mode=True,
            auto_commit=False
        )
        oaas.configure(config)
        
        # Test that global config is set
        assert OaasService._global_config == config
        
        # Test that global oaas is reset
        global_oaas = OaasService._get_global_oaas()
        assert global_oaas.mock_mode
        print("✅ OaasService global configuration test passed")


class TestIntegration:
    """Integration tests for component interactions."""
    
    def test_full_workflow_integration(self):
        """Test complete workflow integration."""
        config = OaasConfig(mock_mode=True, auto_commit=True)
        oaas.configure(config)
        
        @oaas.service("WorkflowTestInt", package="integration")
        class WorkflowTestInt(OaasObject):
            counter: int = 0
            messages: List[str] = []
            
            @oaas.method
            async def process_message(self, req: dict) -> Dict[str, Any]:
                message = req.get("message", "")
                self.counter += 1
                self.messages.append(message)
                
                return {
                    "counter": self.counter,
                    "message_count": len(self.messages),
                    "latest_message": message
                }
        
        async def test_workflow():
            obj = WorkflowTestInt.create(obj_id=1)
            
            # Process multiple messages
            result1 = await obj.process_message({"message": "Hello"})
            assert result1["counter"] == 1
            assert result1["message_count"] == 1
            assert result1["latest_message"] == "Hello"
            
            result2 = await obj.process_message({"message": "World"})
            assert result2["counter"] == 2
            assert result2["message_count"] == 2
            assert result2["latest_message"] == "World"
            
            # Verify state persistence
            assert obj.counter == 2
            assert obj.messages == ["Hello", "World"]
            
            return True
        
        result = asyncio.run(test_workflow())
        assert result
        print("✅ Integration workflow test passed")


class TestPerformance:
    """Performance and concurrent access tests."""
    
    def test_state_access_performance(self):
        """Test performance of state access operations."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
        
        @oaas.service("PerformanceTestObj", package="performance")
        class PerformanceTestObj(OaasObject):
            counter: int = 0
            
            @oaas.method
            async def bulk_increment(self, req: dict) -> dict:
                count = req.get("count", 0)
                for _ in range(count):
                    self.counter += 1
                return {"counter": self.counter}
        
        async def test_performance():
            obj = PerformanceTestObj.create(obj_id=1)
            
            # Measure performance
            start_time = time.time()
            result = await obj.bulk_increment({"count": 100})  # Reduced from 1000 for faster testing
            end_time = time.time()
            
            execution_time = end_time - start_time
            assert result["counter"] == 100
            assert obj.counter == 100
            
            # Should complete within reasonable time
            assert execution_time < 5.0  # 5 seconds threshold
            
            return True
        
        result = asyncio.run(test_performance())
        assert result
        print("✅ Performance test passed")
    
    def test_concurrent_access(self):
        """Test concurrent access to state fields."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
        
        @oaas.service("ConcurrencyTestObj", package="performance")
        class ConcurrencyTestObj(OaasObject):
            shared_counter: int = 0
            
            @oaas.method
            async def increment_shared(self) -> int:
                # Simulate some work
                await asyncio.sleep(0.001)  # Reduced sleep time
                self.shared_counter += 1
                return self.shared_counter
        
        async def test_concurrent():
            obj = ConcurrencyTestObj.create(obj_id=1)
            
            # Run multiple concurrent operations
            tasks = []
            for _ in range(5):  # Reduced from 10 for faster testing
                task = asyncio.create_task(obj.increment_shared())
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # Check that all operations completed
            assert len(results) == 5
            assert obj.shared_counter == 5
            
            return True
        
        result = asyncio.run(test_concurrent())
        assert result
        print("✅ Concurrent access test passed")


class TestErrorHandling:
    """Error handling and edge case tests."""
    
    def test_invalid_state_types(self):
        """Test handling of invalid state types."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
        
        @oaas.service("InvalidTypeTestObj", package="error")
        class InvalidTypeTestObj(OaasObject):
            flexible_field: int = 0
            
            @oaas.method
            async def set_flexible(self, req: dict) -> Any:
                # This should handle type conversion gracefully
                value = req.get("value", 0)
                self.flexible_field = value
                return self.flexible_field
        
        async def test_invalid_types():
            obj = InvalidTypeTestObj.create(obj_id=1)
            
            # Test string to int conversion
            result = await obj.set_flexible({"value": "42"})
            assert result == 42
            
            # Test float to int conversion
            result = await obj.set_flexible({"value": 42.7})
            assert result == 42
            
            # Test boolean to int conversion
            result = await obj.set_flexible({"value": True})
            assert result == 1
            
            return True
        
        result = asyncio.run(test_invalid_types())
        assert result
        print("✅ Error handling test passed")
    
    def test_serialization_edge_cases(self):
        """Test serialization edge cases."""
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
        
        @oaas.service("SerializationTestObj", package="error")
        class SerializationTestObj(OaasObject):
            none_field: Optional[str] = None
            empty_list: List[str] = []
            empty_dict: Dict[str, str] = {}
            
            @oaas.method
            async def test_none_handling(self) -> Dict[str, Any]:
                return {
                    "none_field": self.none_field,
                    "empty_list": self.empty_list,
                    "empty_dict": self.empty_dict
                }
        
        async def test_serialization():
            obj = SerializationTestObj.create(obj_id=1)
            
            result = await obj.test_none_handling()
            assert result["none_field"] is None
            assert result["empty_list"] == []
            assert result["empty_dict"] == {}
            
            return True
        
        result = asyncio.run(test_serialization())
        assert result
        print("✅ Serialization edge cases test passed")


def run_all_comprehensive_tests():
    """Run all comprehensive tests."""
    print("\n🧪 Running Comprehensive Foundation Component Tests")
    print("=" * 60)
    
    # Test classes and their methods
    test_classes = [
        ("StateDescriptor", TestStateDescriptor),
        ("OaasObject", TestOaasObject),
        ("OaasConfig", TestOaasConfig),
        ("OaasService", TestOaasService),
        ("Integration", TestIntegration),
        ("Performance", TestPerformance),
        ("Error Handling", TestErrorHandling),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_class in test_classes:
        print(f"\n📋 Running {test_name} Tests")
        print("-" * 40)
        try:
            instance = test_class()
            test_methods = [method for method in dir(instance) if method.startswith('test_')]
            
            for method_name in test_methods:
                method = getattr(instance, method_name)
                if callable(method):
                    method()
            
            passed += 1
            print(f"✅ {test_name} comprehensive tests passed")
            
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} comprehensive tests failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"📊 Comprehensive Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All comprehensive tests passed!")
        print("✅ Phase 1 Week 1 foundation components are fully tested and validated.")
        return True
    else:
        print("❌ Some comprehensive tests failed.")
        return False


if __name__ == "__main__":
    success = run_all_comprehensive_tests()
    exit(0 if success else 1)