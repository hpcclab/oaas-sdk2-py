#!/usr/bin/env python3
# Copied from tests/test_enhanced_serialization.py (unit, mock-only)
import pytest
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Optional, Union, Tuple, Set
from pydantic import BaseModel

from oaas_sdk2_py.simplified.serialization import (
    UnifiedSerializer,
)


class SampleModel(BaseModel):
    __test__ = False
    id: int
    name: str
    value: float
    active: bool


class NestedTestModel(BaseModel):
    __test__ = False
    model: SampleModel
    tags: List[str]
    metadata: Dict[str, str]


class TestUnifiedSerializer:
    def setup_method(self):
        self.serializer = UnifiedSerializer()

    @pytest.mark.parametrize("value,expected_type", [
        (42, int),
        (3.14, float),
        ("hello", str),
        (True, bool),
        (b"binary", bytes),
        ([1, 2, 3], list),
        ({"key": "value"}, dict),
    ])
    def test_basic_types(self, value, expected_type):
        serialized = self.serializer.serialize(value, expected_type)
        assert isinstance(serialized, bytes)
        deserialized = self.serializer.deserialize(serialized, expected_type)
        assert deserialized == value
        assert isinstance(deserialized, expected_type)

    def test_none_value(self):
        serialized = self.serializer.serialize(None)
        assert serialized == b""
        deserialized = self.serializer.deserialize(b"", Optional[str])
        assert deserialized is None

    def test_datetime(self):
        dt = datetime(2023, 12, 25, 15, 30, 45)
        serialized = self.serializer.serialize(dt, datetime)
        deserialized = self.serializer.deserialize(serialized, datetime)
        assert deserialized == dt

    def test_uuid(self):
        uuid_val = UUID("12345678-1234-5678-1234-567812345678")
        serialized = self.serializer.serialize(uuid_val, UUID)
        deserialized = self.serializer.deserialize(serialized, UUID)
        assert deserialized == uuid_val

    def test_list_type(self):
        data = [1, 2, 3, 4, 5]
        serialized = self.serializer.serialize(data, List[int])
        deserialized = self.serializer.deserialize(serialized, List[int])
        assert deserialized == data

    def test_dict_type(self):
        data = {"key1": "value1", "key2": "value2"}
        serialized = self.serializer.serialize(data, Dict[str, str])
        deserialized = self.serializer.deserialize(serialized, Dict[str, str])
        assert deserialized == data

    def test_tuple_type(self):
        data = (1, "hello", 3.14)
        serialized = self.serializer.serialize(data, Tuple[int, str, float])
        deserialized = self.serializer.deserialize(serialized, Tuple[int, str, float])
        assert deserialized == data

    def test_set_type(self):
        data = {1, 2, 3, 4, 5}
        serialized = self.serializer.serialize(data, Set[int])
        deserialized = self.serializer.deserialize(serialized, Set[int])
        assert deserialized == data

    def test_optional_type(self):
        serialized = self.serializer.serialize("hello", Optional[str])
        assert self.serializer.deserialize(serialized, Optional[str]) == "hello"
        serialized = self.serializer.serialize(None, Optional[str])
        assert self.serializer.deserialize(serialized, Optional[str]) is None

    def test_union_type(self):
        serialized = self.serializer.serialize(42, Union[int, str])
        assert self.serializer.deserialize(serialized, Union[int, str]) == 42
        serialized = self.serializer.serialize("hello", Union[int, str])
        assert self.serializer.deserialize(serialized, Union[int, str]) == "hello"

    def test_pydantic_model(self):
        model = SampleModel(id=1, name="test", value=3.14, active=True)
        serialized = self.serializer.serialize(model, SampleModel)
        deserialized = self.serializer.deserialize(serialized, SampleModel)
        assert isinstance(deserialized, SampleModel)
        assert deserialized == model

    def test_nested_pydantic_model(self):
        inner = SampleModel(id=1, name="inner", value=2.71, active=True)
        nested = NestedTestModel(model=inner, tags=["a", "b"], metadata={"k": "v"})
        serialized = self.serializer.serialize(nested, NestedTestModel)
        deserialized = self.serializer.deserialize(serialized, NestedTestModel)
        assert isinstance(deserialized, NestedTestModel)
        assert deserialized.model == inner
        assert deserialized.tags == ["a", "b"]
        assert deserialized.metadata == {"k": "v"}
