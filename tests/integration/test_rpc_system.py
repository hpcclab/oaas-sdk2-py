#!/usr/bin/env python3
import pytest
from oaas_sdk2_py.simplified import oaas, OaasConfig, OaasObject


@pytest.mark.integration
def test_rpc_system_basic(setup_oaas):
    oaas.configure(OaasConfig(async_mode=True, mock_mode=True))

    @oaas.service("RpcEcho", package="tests")
    class RpcEcho(OaasObject):
        value: int = 0

        @oaas.method()
        def echo(self, x: int) -> int:
            return x

    obj = RpcEcho.create(obj_id=1)
    assert obj.echo(7) == 7
