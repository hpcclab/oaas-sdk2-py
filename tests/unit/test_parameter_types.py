#!/usr/bin/env python3
import pytest
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig


@pytest.fixture
def setup_oaas():
    oaas.configure(OaasConfig(async_mode=True, mock_mode=True))


@oaas.service("TypeTestService", package="test")
class TypeTestService(OaasObject):
    @oaas.method()
    async def test_str_param(self, text: str) -> str:
        return f"Got string: {text}"

    @oaas.method()
    async def test_bytes_param(self, data: bytes) -> bytes:
        return b"Got bytes: " + data

    @oaas.method()
    async def test_dict_param(self, data: dict) -> dict:
        return {"got_dict": True, "keys": list(data.keys())}

    @oaas.method()
    async def test_no_param(self) -> str:
        return "No parameters needed"


@pytest.mark.asyncio
async def test_all_types(setup_oaas):
    service = TypeTestService.create(local=True)
    assert await service.test_str_param("hello world") == "Got string: hello world"
    assert await service.test_bytes_param(b"binary data") == b"Got bytes: binary data"
    assert await service.test_dict_param({"key1": "value1", "key2": "value2"}) == {"got_dict": True, "keys": ["key1", "key2"]}
    assert await service.test_no_param() == "No parameters needed"
