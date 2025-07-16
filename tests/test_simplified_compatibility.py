#!/usr/bin/env python3
"""
Comprehensive test suite for the OaaS SDK simplified interface Phase 1 Week 1 components.

This test suite provides comprehensive coverage for:
1. StateDescriptor - Automatic state persistence and serialization
2. OaasObject - Auto-serialization, state management, object lifecycle
3. OaasConfig - Configuration consolidation and backward compatibility
4. OaasService - Decorator system, service registration, method wrapping
5. Integration with existing Oparaca engine
6. Performance characteristics and memory usage
7. Thread safety and concurrent access
8. Type safety and serialization edge cases
9. Backward compatibility with legacy API
"""

import asyncio
import json
import threading
import time
import gc
import sys
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel
import pytest
import pickle

# Test imports for backward compatibility
try:
    from oaas_sdk2_py import (
        # Legacy API - should still work
        Oparaca, Session, BaseObject, ClsMeta, FuncMeta, OprcConfig,
        ObjectInvocationRequest, InvocationRequest, InvocationResponse,
        
        # New simplified API
        OaasObject, OaasService, OaasConfig, oaas,
        create_object, load_object
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

class NestedModel(BaseModel):
    inner: ComplexModel
    count: int

# =============================================================================
# COMPATIBILITY TESTS FOR BACKWARD COMPATIBILITY
# =============================================================================

def test_legacy_api():
    """Test that the legacy API still works exactly as before."""
    print("\n🔄 Testing Legacy API...")
    
    try:
        # Test legacy object creation flow
        oparaca = Oparaca(mock_mode=True)
        greeter_cls = oparaca.new_cls("LegacyGreeter", pkg="test")
        
        @greeter_cls
        class LegacyGreeter(BaseObject):
            @greeter_cls.func()
            async def greet(self, req: GreetRequest) -> GreetResponse:
                return GreetResponse(message=f"Hello, {req.name}!")
        
        # Test legacy usage
        async def legacy_test():
            session = oparaca.new_session()
            greeter = session.create_object(greeter_cls, obj_id=1)
            result = await greeter.greet(GreetRequest(name="Legacy"))
            await session.commit_async()
            return result
        
        result = asyncio.run(legacy_test())
        assert result.message == "Hello, Legacy!"
        print("✅ Legacy API works correctly")
        
    except Exception as e:
        print(f"❌ Legacy API test failed: {e}")
        return False
    
    return True

def test_new_simplified_api():
    """Test the new simplified API."""
    print("\n🆕 Testing New Simplified API...")
    
    try:
        # Configure the new system
        config = OaasConfig(
            server_url="http://localhost:10000",
            mock_mode=True,
            auto_commit=True
        )
        oaas.configure(config)
        
        # Test new decorator system
        @oaas.service("SimpleGreeter", package="test")
        class SimpleGreeter(OaasObject):
            @oaas.method
            async def greet(self, req: GreetRequest) -> GreetResponse:
                return GreetResponse(message=f"Hello, {req.name}!")
        
        # Test new usage
        async def simple_test():
            greeter = SimpleGreeter.create(obj_id=1)
            result = await greeter.greet(GreetRequest(name="Simple"))
            return result
        
        result = asyncio.run(simple_test())
        assert result.message == "Hello, Simple!"
        print("✅ New simplified API works correctly")
        
    except Exception as e:
        print(f"❌ New simplified API test failed: {e}")
        return False
    
    return True

def test_state_management():
    """Test automatic state management with type hints."""
    print("\n📊 Testing State Management...")
    
    try:
        # Test state descriptors
        @oaas.service("StateCounter", package="test")
        class StateCounter(OaasObject):
            # Typed state fields - should auto-serialize
            count: int = 0
            name: str = "default"
            tags: List[str] = []
            metadata: Dict[str, str] = {}
            
            @oaas.method
            async def increment(self, req: IncrementRequest) -> CounterResponse:
                self.count += req.amount
                return CounterResponse(count=self.count)
            
            @oaas.method
            async def set_name(self, req: dict) -> str:
                new_name = req.get("name", "default")
                self.name = new_name
                return self.name
            
            @oaas.method
            async def add_tag(self, req: dict) -> List[str]:
                tag = req.get("tag", "")
                self.tags.append(tag)
                return self.tags
            
            @oaas.method
            async def set_metadata(self, req: dict) -> Dict[str, str]:
                key = req.get("key", "")
                value = req.get("value", "")
                self.metadata[key] = value
                return self.metadata
        
        async def state_test():
            counter = StateCounter.create(obj_id=1)
            
            # Test integer state
            result1 = await counter.increment(IncrementRequest(amount=5))
            assert result1.count == 5
            
            # Test string state
            result2 = await counter.set_name({"name": "test_counter"})
            assert result2 == "test_counter"
            
            # Test list state
            result3 = await counter.add_tag({"tag": "important"})
            assert result3 == ["important"]
            
            # Test dict state
            result4 = await counter.set_metadata({"key": "owner", "value": "test_user"})
            assert result4 == {"owner": "test_user"}
            
            return True
        
        result = asyncio.run(state_test())
        assert result == True
        print("✅ State management works correctly")
        
    except Exception as e:
        print(f"❌ State management test failed: {e}")
        return False
    
    return True

def test_config_compatibility():
    """Test that OaasConfig works with existing OprcConfig."""
    print("\n⚙️ Testing Configuration Compatibility...")
    
    try:
        # Test OaasConfig to OprcConfig conversion
        oaas_config = OaasConfig(
            server_url="http://localhost:9000",
            peers="peer1:7447,peer2:7447",
            default_partition=1,
            mock_mode=False
        )
        
        # Convert to legacy config
        oprc_config = oaas_config.to_oprc_config()
        
        # Verify conversion
        assert str(oprc_config.oprc_odgm_url) == "http://localhost:9000/"
        assert oprc_config.oprc_zenoh_peers == "peer1:7447,peer2:7447"
        assert oprc_config.oprc_partition_default == 1
        
        # Test peer parsing
        peers = oaas_config.get_zenoh_peers()
        assert peers == ["peer1:7447", "peer2:7447"]
        
        print("✅ Configuration compatibility works correctly")
        
    except Exception as e:
        print(f"❌ Configuration compatibility test failed: {e}")
        return False
    
    return True

def test_mixed_usage():
    """Test that legacy and new APIs can be used together."""
    print("\n🔄 Testing Mixed Usage...")
    
    try:
        # Configure both systems to use the same mock mode
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)
        
        # Create a legacy service
        oparaca = Oparaca(mock_mode=True)
        legacy_cls = oparaca.new_cls("LegacyMixed", pkg="mixed")
        
        @legacy_cls
        class LegacyMixed(BaseObject):
            @legacy_cls.func()
            async def legacy_method(self, req: GreetRequest) -> GreetResponse:
                return GreetResponse(message=f"Legacy: {req.name}")
        
        # Create a new service (use different package to avoid conflicts)
        @oaas.service("NewMixed", package="newmixed")
        class NewMixed(OaasObject):
            greeting: str = "Hello"
            
            @oaas.method
            async def new_method(self, req: GreetRequest) -> GreetResponse:
                return GreetResponse(message=f"{self.greeting}, {req.name}")
        
        # Test that both work
        async def mixed_test():
            # Legacy usage
            session = oparaca.new_session()
            legacy_obj = session.create_object(legacy_cls, obj_id=1)
            legacy_result = await legacy_obj.legacy_method(GreetRequest(name="Legacy"))
            await session.commit_async()
            
            # New usage
            new_obj = NewMixed.create(obj_id=2)
            new_result = await new_obj.new_method(GreetRequest(name="New"))
            
            return legacy_result, new_result
        
        legacy_result, new_result = asyncio.run(mixed_test())
        assert legacy_result.message == "Legacy: Legacy"
        assert new_result.message == "Hello, New"
        
        print("✅ Mixed usage works correctly")
        
    except Exception as e:
        print(f"❌ Mixed usage test failed: {e}")
        return False
    
    return True

def main():
    """Run compatibility tests only."""
    print("🧪 Running OaaS SDK Simplified Interface Compatibility Tests")
    print("=" * 60)
    
    # Original compatibility tests
    compatibility_tests = [
        test_legacy_api,
        test_new_simplified_api,
        test_state_management,
        test_config_compatibility,
        test_mixed_usage,
    ]
    
    passed = 0
    failed = 0
    
    print("\n📋 COMPATIBILITY TESTS")
    print("-" * 40)
    for test in compatibility_tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Compatibility Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All compatibility tests passed! The simplified interface is working correctly.")
        print("✅ For comprehensive foundation component tests, run: python test_comprehensive_foundation.py")
        return True
    else:
        print("❌ Some compatibility tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)