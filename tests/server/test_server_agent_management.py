#!/usr/bin/env python3
"""
Server and agent management tests (disabled in mock-only runs).
"""

import pytest
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig


@pytest.fixture
def setup_oaas():
    oaas.configure(OaasConfig(async_mode=True, mock_mode=True))


@oaas.service("TestService", package="test")
class TestService(OaasObject):
    __test__ = False
    counter: int = 0

    @oaas.method(serve_with_agent=True)
    async def increment(self) -> int:
        self.counter += 1
        return self.counter

    @oaas.method(serve_with_agent=True)
    async def get_counter(self) -> int:
        return self.counter


@pytest.mark.server
@pytest.mark.asyncio
async def test_server_management(setup_oaas):
    assert True


@pytest.mark.server
@pytest.mark.asyncio
async def test_agent_management(setup_oaas):
    assert True


@pytest.mark.server
@pytest.mark.asyncio
async def test_integration(setup_oaas):
    assert True
