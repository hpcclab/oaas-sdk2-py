#!/usr/bin/env python3
import pytest
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig


@pytest.fixture
def setup_oaas():
    oaas.configure(OaasConfig(async_mode=True, mock_mode=True))


@oaas.service("PrimitiveTestService", package="test")
class PrimitiveTestService(OaasObject):
    @oaas.method()
    async def test_int(self, number: int) -> int:
        return number * 2

    @oaas.method()
    async def test_float(self, number: float) -> float:
        return number * 3.14

    @oaas.method()
    async def test_bool(self, flag: bool) -> bool:
        return not flag

    @oaas.method()
    async def test_list(self, items: list) -> list:
        return items + ["added_item"]

    @oaas.method()
    async def test_mixed_return(self, multiplier: int) -> dict:
        return {
            "multiplier": multiplier,
            "result": multiplier * 42,
            "is_even": multiplier % 2 == 0,
            "factors": [i for i in range(1, multiplier + 1) if multiplier % i == 0],
        }


@pytest.mark.asyncio
async def test_primitive_types(setup_oaas):
    service = PrimitiveTestService.create(local=True)
    assert await service.test_int(5) == 10
    assert abs(await service.test_float(2.5) - 7.85) < 0.01
    assert await service.test_bool(True) is False
    assert await service.test_bool(False) is True
    assert await service.test_list([1, 2, 3]) == [1, 2, 3, "added_item"]
    result = await service.test_mixed_return(6)
    assert result == {"multiplier": 6, "result": 252, "is_even": True, "factors": [1, 2, 3, 6]}
