from __future__ import annotations

import pytest

from oaas_sdk2_py.simplified import oaas, OaasObject


@oaas.service("Counter", package="sync")
class Counter(OaasObject):
    count: int = 0

    # Intentionally non-async accessor declarations
    @oaas.getter("count")
    def get_count(self) -> int:
        # Body is ignored by wrapper; kept to ensure sync definition accepted
        return -1

    @oaas.setter("count")
    def set_count(self, value: int) -> None:
        # Body is ignored by wrapper; kept to ensure sync definition accepted
        pass


@pytest.mark.asyncio
async def test_sync_getter_setter_work(setup_oaas):
    c = Counter.create()
    # Setter should work even though defined sync
    c.set_count(5)
    # Getter should read persisted state
    assert c.get_count() == 5
