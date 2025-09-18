import pytest

from oaas_sdk2_py.simplified import (
	oaas, OaasObject, OaasConfig,
	getter, setter,
)


@pytest.fixture(autouse=True)
def _configure_oaas():
	# Ensure simplified stack runs in mock/async mode for tests
	cfg = OaasConfig(mock_mode=True, async_mode=True, auto_commit=True)
	oaas.configure(cfg)
	yield


def test_accessor_registration_and_metadata():
	@oaas.service("AccessMeta", package="test")
	class AccessMeta(OaasObject):
		count: int = 0

		@getter("count")
		async def get_value(self) -> int:
			# Original body should be ignored by wrapper
			return -1

		@setter("count")
		async def set_value(self, value: int) -> int:
			# Original body should be ignored by wrapper
			return -1

	# Accessor specs should be attached on class
	specs = getattr(AccessMeta, "_oaas_accessors", {})
	assert "get_value" in specs and "set_value" in specs
	assert specs["get_value"].field_name == "count"
	assert specs["set_value"].field_name == "count"


@pytest.mark.asyncio
async def test_getter_setter_persisted_io_and_inference():
	@oaas.service("CounterSvc", package="test")
	class CounterSvc(OaasObject):
		count: int = 0

		# Inference via name get_<field>
		@getter()
		async def get_count(self) -> int:
			return -1

		# Inference via name set_<field>
		@setter()
		async def set_count(self, value: int) -> int:
			return -1

	obj = CounterSvc.create(local=True)
	# Write through setter wrapper
	val = await obj.set_count(7)
	assert val == 7
	# Read through getter wrapper
	got = await obj.get_count()
	assert got == 7


@pytest.mark.asyncio
async def test_projection_getter_over_structured_state():
	@oaas.service("ProfileSvc", package="test")
	class ProfileSvc(OaasObject):
		profile: dict = {"address": {"city": "", "zip": ""}}

		@setter("profile")
		async def set_profile(self, value: dict) -> dict:
			return value

		@getter("profile", projection=["address", "city"])
		async def get_city(self) -> str:
			return "override"

	obj = ProfileSvc.create(local=True)
	await obj.set_profile({"address": {"city": "Tokyo", "zip": "100-0001"}})
	city = await obj.get_city()
	assert city == "Tokyo"
