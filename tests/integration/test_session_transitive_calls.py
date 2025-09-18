#!/usr/bin/env python3
import pytest
from oaas_sdk2_py.simplified import oaas, OaasConfig, OaasObject


@pytest.mark.integration
async def test_transitive_calls(setup_oaas):
    oaas.configure(OaasConfig(async_mode=True, mock_mode=True))

    @oaas.service("SessionCounter", package="examples")
    class SessionCounter(OaasObject):
        sessions: int = 0

        @oaas.method()
        def increment_sessions(self) -> int:
            self.sessions += 1
            return self.sessions

    @oaas.service("UserManager", package="examples")
    class UserManager(OaasObject):
        session_counter: SessionCounter = None

        @oaas.method()
        async def new_session(self) -> int:
            if self.session_counter is not None:
                return await self.session_counter.increment_sessions()
            return 0

    counter = SessionCounter.create(obj_id=1)
    mgr = UserManager.create(obj_id=2)
    mgr.session_counter = counter
    assert await mgr.new_session() == 1
