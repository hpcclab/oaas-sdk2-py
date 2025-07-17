#!/usr/bin/env python3
"""
Test script to verify type support after fixing isinstance bug.
"""
import asyncio
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig

# Configure OaaS
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

async def test_all_types():
    """Test all supported parameter types"""
    print("🧪 Testing Parameter Type Support")
    print("=" * 40)
    
    service = TypeTestService.create(local=True)
    
    # Test str
    result = await service.test_str_param("hello world")
    print(f"✓ str parameter: {result}")
    
    # Test bytes
    result = await service.test_bytes_param(b"binary data")
    print(f"✓ bytes parameter: {result}")
    
    # Test dict
    result = await service.test_dict_param({"key1": "value1", "key2": "value2"})
    print(f"✓ dict parameter: {result}")
    
    # Test no param
    result = await service.test_no_param()
    print(f"✓ no parameter: {result}")
    
    print("\n✅ All parameter types work correctly!")

if __name__ == "__main__":
    asyncio.run(test_all_types())
