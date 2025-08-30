from __future__ import annotations

import pytest

from oaas_sdk2_py.simplified import oaas, OaasObject


@oaas.service("Account", package="ref")
class Account(OaasObject):
    balance: int = 0

    @oaas.getter("balance")
    async def get_balance(self) -> int:
        return self.balance

    @oaas.setter("balance")
    async def set_balance(self, value: int) -> None:
        # Body ignored by accessor wrapper; kept for clarity.
        self.balance = value

    @oaas.constructor()
    async def init(self, starting: int) -> None:
        # Initialize persisted state
        self.balance = starting


@pytest.mark.asyncio
async def test_constructor_and_setter_via_objectref(setup_oaas):
    # Create and initialize via constructor
    acct = Account.create()
    await acct.init(10)
    assert await acct.get_balance() == 10

    # Use ObjectRef to call setter accessor (write-through) and verify via getter
    ref = acct.as_ref()
    await ref.set_balance(25)
    assert await ref.get_balance() == 25

    # Call constructor on instance and verify state updated
    await acct.init(50)
    # Verify latest value via ref (reads storage directly)
    assert await ref.get_balance() == 50
