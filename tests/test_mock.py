import unittest

import oprc_py
from .sample_cls import AsyncSampleObj, SampleObj, oaas, async_sample_cls_meta, sample_cls_meta

oprc_py.init_logger("debug")

class TestAsyncMock(unittest.IsolatedAsyncioTestCase):
    
    async def test_data_fail_without_mock(self):
        obj: AsyncSampleObj = oaas.create_object(async_sample_cls_meta, 1)
        await obj.set_intro("Hi from Testing")
        with self.assertRaises(Exception):
            await obj.commit_async()  # should fail because it connot connect to the ODGM
    
    async def test_rpc_fail_without_mock(self):
        obj: AsyncSampleObj = oaas.create_object(async_sample_cls_meta, 1)
        with self.assertRaises(Exception):
            await obj.greet() # should fail because it connot connect to Zenoh
        
    async def test_rpc_with_mock(self):
        mock_oaas = oaas.mock()
        obj: AsyncSampleObj = mock_oaas.create_object(async_sample_cls_meta, 1)
        await obj.set_intro("Object 1")
        await obj.commit_async()
        result = await obj.greet()
        assert result == "Hello, Object 1"
    
    async def test_multiple_objects(self):
        mock_oaas = oaas.mock()
        obj1 = mock_oaas.create_object(async_sample_cls_meta, 1)
        obj2 = mock_oaas.create_object(async_sample_cls_meta, 2)
        
        await obj1.set_intro("Object 1")
        await obj2.set_intro("Object 2")
        await obj1.commit_async()
        await obj2.commit_async()
        
        obj1_reload = mock_oaas.load_object(async_sample_cls_meta, 1)
        obj2_reload = mock_oaas.load_object(async_sample_cls_meta, 2)
        
        assert await obj1_reload.get_intro() == "Object 1"
        assert await obj2_reload.get_intro() == "Object 2"

    async def test_object_update(self):
        mock_oaas = oaas.mock()
        obj = mock_oaas.create_object(async_sample_cls_meta, 1)
        
        await obj.set_intro("Initial value")
        await obj.commit_async()
        
        await obj.set_intro("Updated value")
        await obj.commit_async()
        
        obj_reload = mock_oaas.load_object(async_sample_cls_meta, 1)
        assert await obj_reload.get_intro() == "Updated value"

    async def test_object_delete(self):
        mock_oaas = oaas.mock()
        obj = mock_oaas.create_object(async_sample_cls_meta, 1)
        
        await obj.set_intro("Test value")
        await obj.commit_async()
        
        # Assuming there's a delete method in your mock implementation
        mock_oaas.delete_object(async_sample_cls_meta, 1)
        await mock_oaas.commit_async()
        
        # Now loading the object should create a fresh one without the intro
        obj_new = mock_oaas.load_object(async_sample_cls_meta, 1)
        with self.assertRaises(Exception):
            await obj_new.get_intro()  # Should fail as object was deleted

    async def test_mock_isolation(self):
        # Test that different mock instances are isolated
        mock_oaas1 = oaas.mock()
        mock_oaas2 = oaas.mock()
        
        obj1 = mock_oaas1.create_object(async_sample_cls_meta, 1)
        await obj1.set_intro("From mock 1")
        await obj1.commit_async()
        
        # This should be a fresh object in a different mock environment
        obj2 = mock_oaas2.create_object(async_sample_cls_meta, 1)
        with self.assertRaises(Exception):
            await obj2.get_intro()  # Should fail as it's a different mock


class TestMock(unittest.TestCase):
    
    def test_data_fail_without_mock(self):
        obj: SampleObj = oaas.create_object(sample_cls_meta, 1)
        obj.set_intro("Hi from Testing")
        with self.assertRaises(Exception):
            obj.commit()  # should fail because it connot connect to the ODGM
    
    def test_rpc_fail_without_mock(self):
        obj: SampleObj = oaas.create_object(sample_cls_meta, 1)
        print(obj.greet)
        print(SampleObj.greet)
        with self.assertRaises(Exception):
            out = obj.greet() # should fail because it connot connect to Zenoh
            print(out)
        
    def test_rpc_with_mock(self):
        mock_oaas = oaas.mock()
        obj: SampleObj = mock_oaas.create_object(sample_cls_meta, 1)
        obj.set_intro("Object 1")
        obj.commit()
        result = obj.greet()
        assert result == "Hello, Object 1"
    
    def test_multiple_objects(self):
        mock_oaas = oaas.mock()
        obj1: SampleObj = mock_oaas.create_object(sample_cls_meta, 1)
        obj2: SampleObj = mock_oaas.create_object(sample_cls_meta, 2)
        
        obj1.set_intro("Object 1")
        obj2.set_intro("Object 2")
        obj1.commit()
        obj2.commit()
        
        obj1_reload: SampleObj = mock_oaas.load_object(sample_cls_meta, 1)
        obj2_reload: SampleObj = mock_oaas.load_object(sample_cls_meta, 2)
        
        assert obj1_reload.get_intro() == "Object 1"
        assert obj2_reload.get_intro() == "Object 2"

    def test_object_update(self):
        mock_oaas = oaas.mock()
        obj = mock_oaas.create_object(sample_cls_meta, 1)
        
        obj.set_intro("Initial value")
        obj.commit()
        
        obj.set_intro("Updated value")
        obj.commit()
        
        obj_reload = mock_oaas.load_object(sample_cls_meta, 1)
        assert obj_reload.get_intro() == "Updated value"

    def test_object_delete(self):
        mock_oaas = oaas.mock()
        obj = mock_oaas.create_object(sample_cls_meta, 1)
        
        obj.set_intro("Test value")
        obj.commit()
        
        # Assuming there's a delete method in your mock implementation
        mock_oaas.delete_object(sample_cls_meta, 1)
        mock_oaas.commit()
        
        # Now loading the object should create a fresh one without the intro
        obj_new = mock_oaas.load_object(sample_cls_meta, 1)
        with self.assertRaises(Exception):
            obj_new.get_intro()  # Should fail as object was deleted

    def test_mock_isolation(self):
        # Test that different mock instances are isolated
        mock_oaas1 = oaas.mock()
        mock_oaas2 = oaas.mock()
        
        obj1 = mock_oaas1.create_object(sample_cls_meta, 1)
        obj1.set_intro("From mock 1")
        obj1.commit()
        
        # This should be a fresh object in a different mock environment
        obj2 = mock_oaas2.create_object(sample_cls_meta, 1)
        with self.assertRaises(Exception):
            obj2.get_intro()  # Should fail as it's a different mock

