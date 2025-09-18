#!/usr/bin/env python3
import pytest
from oaas_sdk2_py.simplified import oaas, OaasConfig, OaasObject


@pytest.mark.integration
def test_session_management_create_and_commit(setup_oaas):
    oaas.configure(OaasConfig(async_mode=True, mock_mode=True))

    @oaas.service("SessThing", package="tests")
    class SessThing(OaasObject):
        count: int = 0

        @oaas.method()
        def inc(self) -> int:
            self.count += 1
            return self.count

    obj = SessThing.create(obj_id=11)
    assert obj.inc() == 1
