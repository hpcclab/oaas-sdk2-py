#!/usr/bin/env python3
"""
Test script to verify primitive data type support.
"""
import pytest
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig


@pytest.fixture
def setup_oaas():
    """Setup OaaS for testing."""
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

@pytest.mark.asyncio
async def test_primitive_types(setup_oaas):
    """Test all primitive parameter types"""
    print("🧪 Testing Primitive Data Type Support")
    print("=" * 45)
    
    service = PrimitiveTestService.create(local=True)
    
    # Test int
    result = await service.test_int(5)
    print(f"✓ int parameter: 5 * 2 = {result} (type: {type(result)})")
    assert result == 10
    assert isinstance(result, int)
    
    # Test float
    result = await service.test_float(2.5)
    print(f"✓ float parameter: 2.5 * 3.14 = {result:.2f} (type: {type(result)})")
    assert abs(result - 7.85) < 0.01  # Allow for floating point precision
    assert isinstance(result, float)
    
    # Test bool
    result = await service.test_bool(True)
    print(f"✓ bool parameter: not True = {result} (type: {type(result)})")
    assert result == False
    assert isinstance(result, bool)
    
    result = await service.test_bool(False)
    print(f"✓ bool parameter: not False = {result} (type: {type(result)})")
    assert result == True
    assert isinstance(result, bool)
    
    # Test list
    result = await service.test_list([1, 2, 3])
    print(f"✓ list parameter: [1, 2, 3] + ['added_item'] = {result} (type: {type(result)})")
    expected = [1, 2, 3, "added_item"]
    assert result == expected
    assert isinstance(result, list)
    
    # Test mixed return types
    result = await service.test_mixed_return(6)
    print(f"✓ mixed return: {result}")
    assert isinstance(result, dict)
    assert result['multiplier'] == 6
    assert result['result'] == 252  # 6 * 42
    assert result['is_even'] == True
    assert result['factors'] == [1, 2, 3, 6]
    
    print(f"  - multiplier: {result['multiplier']} (type: {type(result['multiplier'])})")
    print(f"  - result: {result['result']} (type: {type(result['result'])})")
    print(f"  - is_even: {result['is_even']} (type: {type(result['is_even'])})")
    print(f"  - factors: {result['factors']} (type: {type(result['factors'])})")
    
    print("\n✅ All primitive data types work correctly!")
