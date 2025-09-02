import unittest

from oaas_sdk2_py import oaas, OaasConfig
from .sample_cls import AsyncSampleObj, SampleObj


class TestAsyncMock(unittest.IsolatedAsyncioTestCase):
    async def test_data_fail_without_mock(self):
        # Configure real mode (no mock) so commits should fail without ODGM
        oaas.configure(OaasConfig(mock_mode=False, auto_commit=False))
        obj = AsyncSampleObj.create(obj_id=1)
        # Disable object-level auto-commit so failure occurs on explicit commit
        obj._auto_commit = False
        await obj.set_intro("Hi from Testing")
        with self.assertRaises(Exception):
            await obj.commit_async()  # Expected to fail without ODGM

    async def test_with_mock_greet(self):
        # Enable mock mode and verify method works
        oaas.configure(OaasConfig(mock_mode=True, auto_commit=True))
        obj = AsyncSampleObj.create(obj_id=1)
        await obj.set_intro("Object 1")
        await obj.commit_async()
        result = await obj.greet()
        self.assertEqual(result, "Hello, Object 1")

    async def test_multiple_objects(self):
        oaas.configure(OaasConfig(mock_mode=True, auto_commit=False))
        obj1 = AsyncSampleObj.create(obj_id=1)
        obj2 = AsyncSampleObj.create(obj_id=2)

        await obj1.set_intro("Object 1")
        await obj2.set_intro("Object 2")
        await obj1.commit_async()
        await obj2.commit_async()

        obj1_reload = AsyncSampleObj.load(1)
        obj2_reload = AsyncSampleObj.load(2)

        self.assertEqual(await obj1_reload.get_intro(), "Object 1")
        self.assertEqual(await obj2_reload.get_intro(), "Object 2")

    async def test_object_update(self):
        oaas.configure(OaasConfig(mock_mode=True, auto_commit=False))
        obj = AsyncSampleObj.create(obj_id=1)

        await obj.set_intro("Initial value")
        await obj.commit_async()

        await obj.set_intro("Updated value")
        await obj.commit_async()

        obj_reload = AsyncSampleObj.load(1)
        self.assertEqual(await obj_reload.get_intro(), "Updated value")

    async def test_object_delete(self):
        oaas.configure(OaasConfig(mock_mode=True, auto_commit=False))
        obj = AsyncSampleObj.create(obj_id=1)

        await obj.set_intro("Test value")
        await obj.commit_async()

        obj.delete()
        await obj.session.commit_async()

        # After deletion, a fresh load should have default state
        obj_new = AsyncSampleObj.load(1)
        self.assertEqual(await obj_new.get_intro(), "")


class TestMockWithSampleObj(unittest.IsolatedAsyncioTestCase):
    async def test_data_fail_without_mock(self):
        oaas.configure(OaasConfig(mock_mode=False, auto_commit=False))
        obj = SampleObj.create(obj_id=1)
        # Disable object-level auto-commit so failure occurs on explicit commit
        obj._auto_commit = False
        await obj.set_intro("Hi from Testing")
        with self.assertRaises(Exception):
            await obj.commit_async()  # Expected to fail without ODGM

    async def test_with_mock_greet(self):
        oaas.configure(OaasConfig(mock_mode=True, auto_commit=True))
        obj = SampleObj.create(obj_id=1)
        await obj.set_intro("Object 1")
        await obj.commit_async()
        result = await obj.greet()
        self.assertEqual(result, "Hello, Object 1")

    async def test_multiple_objects(self):
        oaas.configure(OaasConfig(mock_mode=True, auto_commit=False))
        obj1 = SampleObj.create(obj_id=1)
        obj2 = SampleObj.create(obj_id=2)

        await obj1.set_intro("Object 1")
        await obj2.set_intro("Object 2")
        await obj1.commit_async()
        await obj2.commit_async()

        obj1_reload = SampleObj.load(1)
        obj2_reload = SampleObj.load(2)

        self.assertEqual(await obj1_reload.get_intro(), "Object 1")
        self.assertEqual(await obj2_reload.get_intro(), "Object 2")

    async def test_object_update(self):
        oaas.configure(OaasConfig(mock_mode=True, auto_commit=False))
        obj = SampleObj.create(obj_id=1)

        await obj.set_intro("Initial value")
        await obj.commit_async()

        await obj.set_intro("Updated value")
        await obj.commit_async()

        obj_reload = SampleObj.load(1)
        self.assertEqual(await obj_reload.get_intro(), "Updated value")

    async def test_object_delete(self):
        oaas.configure(OaasConfig(mock_mode=True, auto_commit=False))
        obj = SampleObj.create(obj_id=1)

        await obj.set_intro("Test value")
        await obj.commit_async()

        obj.delete()
        await obj.session.commit_async()

        obj_new = SampleObj.load(1)
        self.assertEqual(await obj_new.get_intro(), "")
