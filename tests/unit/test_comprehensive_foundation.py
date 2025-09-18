#!/usr/bin/env python3
import pytest
from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from oaas_sdk2_py.simplified import StateDescriptor, OaasObject, OaasConfig, oaas


class GreetRequest(BaseModel):
    name: str


class GreetResponse(BaseModel):
    message: str


class CounterResponse(BaseModel):
    count: int


class IncrementRequest(BaseModel):
    amount: int = 1


class ComplexModel(BaseModel):
    id: int
    name: str
    tags: List[str]
    metadata: Dict[str, Any]
    timestamp: datetime
    uuid: UUID


class TestStateDescriptor:
    def test_basic_state_descriptor_creation(self):
        d = StateDescriptor(name="test_field", type_hint=int, default_value=42, index=0)
        assert d.name == "test_field"
        assert d.type_hint is int
        assert d.default_value == 42
        assert d.index == 0
        assert d.private_name == "_state_test_field"

    def test_state_descriptor_basic_types(self):
        class MockObject:
            def __init__(self):
                self._data = {}
            def get_data(self, index):
                return self._data.get(index)
            def set_data(self, index, value):
                self._data[index] = value

        obj = MockObject()
        int_desc = StateDescriptor("count", int, 0, 0)
        assert int_desc.__get__(obj) == 0
        int_desc.__set__(obj, 42)
        assert int_desc.__get__(obj) == 42

        str_desc = StateDescriptor("name", str, "", 1)
        assert str_desc.__get__(obj) == ""
        str_desc.__set__(obj, "test")
        assert str_desc.__get__(obj) == "test"

        bool_desc = StateDescriptor("active", bool, False, 2)
        assert bool_desc.__get__(obj) is False
        bool_desc.__set__(obj, True)
        assert bool_desc.__get__(obj) is True

    def test_state_descriptor_serialization(self):
        d = StateDescriptor("count", int, 0, 0)
        assert d._deserialize(d._serialize(42)) == 42

    def test_state_descriptor_type_conversion(self):
        d = StateDescriptor("count", int, 0, 0)
        assert d._convert_value("42") == 42
        assert d._convert_value(42.5) == 42
        assert d._convert_value(True) == 1


class TestOaasObject:
    @pytest.mark.asyncio
    async def test_oaas_object_state_management(self, setup_oaas):
        oaas.configure(OaasConfig(mock_mode=True))

        @oaas.service("StateTestObj", package="test")
        class StateTestObj(OaasObject):
            count: int = 0
            name: str = "default"

            @oaas.method
            async def increment(self) -> int:
                self.count += 1
                return self.count

            @oaas.method
            async def set_name(self, req: dict) -> str:
                self.name = req.get("name", "default")
                return self.name

        obj = StateTestObj.create(obj_id=1)
        assert obj.count == 0 and obj.name == "default"
        assert await obj.increment() == 1
        assert await obj.set_name({"name": "test"}) == "test"
        assert obj.count == 1 and obj.name == "test"
