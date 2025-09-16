#!/usr/bin/env python3
"""
Test: Transitive RPC call and persisted state across services.

Mirrors examples.session: `UserManager` calls `SessionCounter.increment_sessions`
through an identity-based reference. Verifies final count equals the number of
login calls, under remote-by-default semantics (mock mode allowed).
"""

from oaas_sdk2_py.simplified import (
    oaas, OaasObject, OaasConfig,
)

def test_transitive_calls_increment_persisted_state():
    # Configure mock mode; remote-by-default behavior is preserved
    config = OaasConfig(mock_mode=True, async_mode=False)
    oaas.configure(config)

    @oaas.service("SessionCounter", package="examples")
    class SessionCounter(OaasObject):
        count: int = 0

        @oaas.method()
        def increment_sessions(self) -> int:
            self.count += 1
            return self.count

        @oaas.getter()
        def get_count(self) -> int:
            return self.count

    @oaas.service("UserManager", package="examples")
    class UserManager(OaasObject):
        session_counter: SessionCounter = None

        @oaas.method()
        def login_user(self, user_id: str) -> str:
            if self.session_counter is not None:
                self.session_counter.increment_sessions()
            return f"User {user_id} logged in successfully."

    # Create objects and wire the reference
    global_counter = SessionCounter.create(obj_id=100)
    user_mgr = UserManager.create(obj_id=200)
    user_mgr.session_counter = global_counter

    # Perform two transitive calls
    assert "Alice" in user_mgr.login_user("Alice")
    assert "Bob" in user_mgr.login_user("Bob")

    # Verify persisted state reached 2
    assert global_counter.get_count() == 2
