#!/usr/bin/env python3
import pytest

from oaas_sdk2_py import Oparaca, BaseObject
from oaas_sdk2_py.simplified import OaasObject, OaasConfig, oaas
from pydantic import BaseModel


class GreetRequest(BaseModel):
    name: str


class GreetResponse(BaseModel):
    message: str


@pytest.mark.integration
async def test_legacy_api_compat(setup_oaas):
    oparaca = Oparaca(mock_mode=True)
    greeter_cls = oparaca.new_cls("LegacyGreeter", pkg="test")

    @greeter_cls
    class LegacyGreeter(BaseObject):
        @greeter_cls.func()
        async def greet(self, req: GreetRequest) -> GreetResponse:
            return GreetResponse(message=f"Hello, {req.name}!")

    session = oparaca.new_session()
    greeter = session.create_object(greeter_cls, obj_id=1)
    result = await greeter.greet(GreetRequest(name="Legacy"))
    await session.commit_async()
    assert result.message == "Hello, Legacy!"


@pytest.mark.integration
async def test_simplified_api_compat(setup_oaas):
    oaas.configure(OaasConfig(mock_mode=True, auto_commit=True))

    @oaas.service("SimpleGreeter", package="test")
    class SimpleGreeter(OaasObject):
        @oaas.method
        async def greet(self, req: GreetRequest) -> GreetResponse:
            return GreetResponse(message=f"Hello, {req.name}!")

    greeter = SimpleGreeter.create(obj_id=1)
    result = await greeter.greet(GreetRequest(name="Simple"))
    assert result.message == "Hello, Simple!"


@pytest.mark.integration
async def test_mixed_usage_compat(setup_oaas):
    # Configure simplified path
    oaas.configure(OaasConfig(mock_mode=True))

    # Legacy service
    oparaca = Oparaca(mock_mode=True)
    legacy_cls = oparaca.new_cls("LegacyMixed", pkg="mixed")

    @legacy_cls
    class LegacyMixed(BaseObject):
        @legacy_cls.func()
        async def legacy_method(self, req: GreetRequest) -> GreetResponse:
            return GreetResponse(message=f"Legacy: {req.name}")

    # Simplified service
    @oaas.service("NewMixed", package="newmixed")
    class NewMixed(OaasObject):
        greeting: str = "Hello"

        @oaas.method
        async def new_method(self, req: GreetRequest) -> GreetResponse:
            return GreetResponse(message=f"{self.greeting}, {req.name}")

    # Exercise both
    session = oparaca.new_session()
    legacy_obj = session.create_object(legacy_cls, obj_id=1)
    legacy_result = await legacy_obj.legacy_method(GreetRequest(name="Legacy"))
    await session.commit_async()

    new_obj = NewMixed.create(obj_id=2)
    new_result = await new_obj.new_method(GreetRequest(name="New"))

    assert legacy_result.message == "Legacy: Legacy"
    assert new_result.message == "Hello, New"
