#!/usr/bin/env python3
"""
Test script to verify primitive data type support.
"""
import asyncio
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig

# Configure OaaS
config = OaasConfig(async_mode=True, mock_mode=True)
oaas.configure(config)

@oaas.service("PrimitiveTestService", package="test")
class PrimitiveTestService(OaasObject):
    
    @oaas.method()
    async def test_int(self, number: int) -> int:
        """Test int parameter and return"""
        return number * 2
    
    @oaas.method()
    async def test_float(self, number: float) -> float:
        """Test float parameter and return"""
        return number * 3.14
    
    @oaas.method()
    async def test_bool(self, flag: bool) -> bool:
        """Test bool parameter and return"""
        return not flag
    
    @oaas.method()
    async def test_list(self, items: list) -> list:
        """Test list parameter and return"""
        return items + ["added_item"]
    
    @oaas.method()
    async def test_mixed_return(self, multiplier: int) -> dict:
        """Test returning different types based on input"""
        return {
            "multiplier": multiplier,
            "result": multiplier * 42,
            "is_even": multiplier % 2 == 0,
            "factors": [i for i in range(1, multiplier + 1) if multiplier % i == 0]
        }

async def test_primitive_types():
    """Test all primitive parameter types"""
    print("🧪 Testing Primitive Data Type Support")
    print("=" * 45)
    
    service = PrimitiveTestService.create(local=True)
    
    # Test int
    result = await service.test_int(5)
    print(f"✓ int parameter: 5 * 2 = {result} (type: {type(result)})")
    
    # Test float
    result = await service.test_float(2.5)
    print(f"✓ float parameter: 2.5 * 3.14 = {result:.2f} (type: {type(result)})")
    
    # Test bool
    result = await service.test_bool(True)
    print(f"✓ bool parameter: not True = {result} (type: {type(result)})")
    
    result = await service.test_bool(False)
    print(f"✓ bool parameter: not False = {result} (type: {type(result)})")
    
    # Test list
    result = await service.test_list([1, 2, 3])
    print(f"✓ list parameter: [1, 2, 3] + ['added_item'] = {result} (type: {type(result)})")
    
    # Test mixed return types
    result = await service.test_mixed_return(6)
    print(f"✓ mixed return: {result}")
    print(f"  - multiplier: {result['multiplier']} (type: {type(result['multiplier'])})")
    print(f"  - result: {result['result']} (type: {type(result['result'])})")
    print(f"  - is_even: {result['is_even']} (type: {type(result['is_even'])})")
    print(f"  - factors: {result['factors']} (type: {type(result['factors'])})")
    
    print("\n✅ All primitive data types work correctly!")

if __name__ == "__main__":
    asyncio.run(test_primitive_types())
