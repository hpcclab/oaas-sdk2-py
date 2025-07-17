#!/usr/bin/env python3
"""
Test script to verify type support after fixing isinstance bug.
"""
import pytest
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig


@pytest.fixture
def setup_oaas():
    """Setup OaaS for testing."""
    config = OaasConfig(async_mode=True, mock_mode=True)
    oaas.configure(config)


@oaas.service("TypeTestService", package="test")
class TypeTestService(OaasObject):
    
    @oaas.method()
    async def test_str_param(self, text: str) -> str:
        """Test str parameter support"""
        return f"Got string: {text}"
    
    @oaas.method()
    async def test_bytes_param(self, data: bytes) -> bytes:
        """Test bytes parameter support"""
        return b"Got bytes: " + data
    
    @oaas.method()
    async def test_dict_param(self, data: dict) -> dict:
        """Test dict parameter support"""
        return {"got_dict": True, "keys": list(data.keys())}
    
    @oaas.method()
    async def test_no_param(self) -> str:
        """Test no parameter support"""
        return "No parameters needed"

@pytest.mark.asyncio
async def test_all_types(setup_oaas):
    """Test all supported parameter types"""
    print("🧪 Testing Parameter Type Support")
    print("=" * 40)
    
    service = TypeTestService.create(local=True)
    
    # Test str
    result = await service.test_str_param("hello world")
    print(f"✓ str parameter: {result}")
    assert result == "Got string: hello world"
    assert isinstance(result, str)
    
    # Test bytes
    result = await service.test_bytes_param(b"binary data")
    print(f"✓ bytes parameter: {result}")
    assert result == b"Got bytes: binary data"
    assert isinstance(result, bytes)
    
    # Test dict
    result = await service.test_dict_param({"key1": "value1", "key2": "value2"})
    print(f"✓ dict parameter: {result}")
    assert result == {"got_dict": True, "keys": ["key1", "key2"]}
    assert isinstance(result, dict)
    
    # Test no param
    result = await service.test_no_param()
    print(f"✓ no parameter: {result}")
    assert result == "No parameters needed"
    assert isinstance(result, str)
    
    print("\n✅ All parameter types work correctly!")
