from __future__ import annotations

import asyncio
from typing import Optional
import pytest

from oaas_sdk2_py.simplified import oaas, OaasObject, ref


@oaas.service("Profile", package="ref")
class Profile(OaasObject):
    email: str

    @oaas.getter("email")
    async def get_email(self) -> str:
        return self.email

    @oaas.method()
    async def uppercase_email(self) -> str:
        return (self.email or "").upper()

@oaas.service("User", package="ref")
class User(OaasObject):
    profile: Optional[Profile] = None

    @oaas.method()
    async def link_profile(self, p: Profile) -> bool:
        # Accepts instance, proxy, or identity dict/tuple
        self.profile = p
        return True

    @oaas.method()
    async def read_profile_email(self) -> Optional[str]:
        if self.profile is None:
            return None
        return await self.profile.get_email()


@pytest.mark.asyncio
async def test_reference_fields_and_rpc(setup_oaas):
    # Create profile and user
    prof = Profile.create()
    prof.email = "a@example.com"

    user = User.create()
    # Edge case: no profile linked yet
    assert await user.read_profile_email() is None
    await user.link_profile(prof)

    # Ensure reading works through proxy
    assert await user.read_profile_email() == "a@example.com"

    # Assign via identity
    user.profile = ref(cls_id=prof.meta.cls_id, object_id=prof.object_id, partition_id=prof.meta.partition_id)
    assert await user.read_profile_email() == "a@example.com"

    # Assign via as_ref()
    user.profile = prof.as_ref()
    assert await user.read_profile_email() == "a@example.com"

    # Assign via identity tuple (cls_id, partition_id, object_id)
    user.profile = (prof.meta.cls_id, prof.meta.partition_id, prof.object_id)
    assert await user.read_profile_email() == "a@example.com"

    # Direct accessor call via ObjectRef
    assert await prof.as_ref().get_email() == "a@example.com"

    # Non-accessor method call via ObjectRef
    assert await prof.as_ref().uppercase_email() == "A@EXAMPLE.COM"

    # Set profile to None and verify Optional handling
    user.profile = None
    assert await user.read_profile_email() is None
