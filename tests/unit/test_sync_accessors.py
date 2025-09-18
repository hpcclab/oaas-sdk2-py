from __future__ import annotations

import pytest

from oaas_sdk2_py.simplified import oaas, OaasObject


@oaas.service("Counter", package="sync")
class Counter(OaasObject):
    count: int = 0

    @oaas.getter("count")
    def get_count(self) -> int:
        return -1

    @oaas.setter("count")
    def set_count(self, value: int) -> None:
        pass


@pytest.mark.asyncio
async def test_sync_getter_setter_work(setup_oaas):
    c = Counter.create()
    c.set_count(5)
    assert c.get_count() == 5
