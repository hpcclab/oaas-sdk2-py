import unittest
import oprc_py
from oprc_py import FnTriggerType, DataTriggerType
from .sample_cls import oaas, sample_cls_meta, SampleObj

try:
    oprc_py.init_logger("info,oprc_py=debug")
except Exception as _:
    pass

class TestEvent(unittest.TestCase):
    def test_add_event(self):
        mock = oaas.mock()
        obj1: SampleObj = mock.create_object(sample_cls_meta, 1)
        obj2: SampleObj = mock.create_object(sample_cls_meta, 2)
        
        out = obj1.trigger(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)
        print(out)
        out = obj1.trigger(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)
        print(out)
        print(obj1._obj.event)
        
        # Add assertion to verify the event was added
        self.assertTrue(obj1._obj.event is not None)
        fn_triggers = obj1._obj.event.get_func_triggers()
        print(fn_triggers)
        self.assertEqual(len(fn_triggers), 1)
        self.assertTrue(obj1.greet._meta.name in fn_triggers)
        # Verify the OnComplete triggers
        on_complete_triggers = fn_triggers[obj1.greet._meta.name].on_complete
        self.assertEqual(len(on_complete_triggers), 1)
        # Verify target function details
        target = on_complete_triggers[0]
        self.assertEqual(target.cls_id, obj2.meta.cls_id)
        self.assertEqual(target.partition_id, obj2.meta.partition_id)
        self.assertEqual(target.object_id, obj2.meta.object_id)
        self.assertEqual(target.fn_id, obj2.sample_fn._meta.name)
        
    def test_add_data_trigger(self):
        mock = oaas.mock()
        obj1: SampleObj = mock.create_object(sample_cls_meta, 1)
        obj2: SampleObj = mock.create_object(sample_cls_meta, 2)
        
        # Add a data trigger - when data entry 5 is updated, call sample_fn
        data_key = 5
        obj1.trigger(data_key, obj2.sample_fn, DataTriggerType.OnUpdate)
        
        # Verify the data trigger was added
        self.assertTrue(obj1._obj.event is not None)
        data_triggers = obj1._obj.event.get_data_triggers()
        self.assertEqual(len(data_triggers), 1)
        self.assertTrue(data_key in data_triggers)
        # Verify the OnUpdate triggers
        on_update_triggers = data_triggers[data_key].on_update
        self.assertEqual(len(on_update_triggers), 1)
        # Verify target function details
        target = on_update_triggers[0]
        self.assertEqual(target.cls_id, obj2.meta.cls_id)
        self.assertEqual(target.partition_id, obj2.meta.partition_id)
        self.assertEqual(target.object_id, obj2.meta.object_id)
        self.assertEqual(target.fn_id, obj2.sample_fn._meta.name)
        
    def test_suppress_fn_trigger(self):
        mock = oaas.mock()
        obj1: SampleObj = mock.create_object(sample_cls_meta, 1)
        obj2: SampleObj = mock.create_object(sample_cls_meta, 2)
        
        # Add a function trigger
        obj1.trigger(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)
        
        # Verify it was added
        fn_triggers = obj1._obj.event.get_func_triggers()
        self.assertEqual(len(fn_triggers), 1)
        self.assertTrue(obj1.greet._meta.name in fn_triggers)
        self.assertEqual(len(fn_triggers[obj1.greet._meta.name].on_complete), 1)
        
        # Suppress the trigger
        obj1.suppress(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)
        
        # Verify it was removed
        fn_triggers = obj1._obj.event.get_func_triggers()
        if obj1.greet._meta.name in fn_triggers:
            self.assertEqual(len(fn_triggers[obj1.greet._meta.name].on_complete), 0)
        
    def test_suppress_data_trigger(self):
        mock = oaas.mock()
        obj1: SampleObj = mock.create_object(sample_cls_meta, 1)
        obj2: SampleObj = mock.create_object(sample_cls_meta, 2)
        
        # Add a data trigger
        data_key = 10
        obj1.trigger(data_key, obj2.sample_fn, DataTriggerType.OnUpdate)
        
        # Verify it was added
        data_triggers = obj1._obj.event.get_data_triggers()
        self.assertEqual(len(data_triggers), 1)
        self.assertTrue(data_key in data_triggers)
        self.assertEqual(len(data_triggers[data_key].on_update), 1)
        
        # Suppress the trigger
        obj1.suppress(data_key, obj2.sample_fn, DataTriggerType.OnUpdate)
        
        # Verify it was removed
        data_triggers = obj1._obj.event.get_data_triggers()
        if data_key in data_triggers:
            self.assertEqual(len(data_triggers[data_key].on_update), 0)
        
    def test_multiple_triggers(self):
        mock = oaas.mock()
        obj1: SampleObj = mock.create_object(sample_cls_meta, 1)
        obj2: SampleObj = mock.create_object(sample_cls_meta, 2)
        
        # Add multiple triggers of different types
        obj1.trigger(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)
        obj1.trigger(obj1.greet, obj2.sample_fn, FnTriggerType.OnError)
        obj1.trigger(5, obj2.sample_fn, DataTriggerType.OnUpdate)
        obj1.trigger(7, obj2.sample_fn, DataTriggerType.OnCreate)
        
        # Verify all triggers were added
        fn_triggers = obj1._obj.event.get_func_triggers()
        data_triggers = obj1._obj.event.get_data_triggers()
        
        # Check function triggers
        self.assertEqual(len(fn_triggers), 1)  # One function with triggers
        self.assertTrue(obj1.greet._meta.name in fn_triggers)
        self.assertEqual(len(fn_triggers[obj1.greet._meta.name].on_complete), 1)
        self.assertEqual(len(fn_triggers[obj1.greet._meta.name].on_error), 1)
        
        # Check data triggers
        self.assertEqual(len(data_triggers), 2)  # Two data keys with triggers
        self.assertTrue(5 in data_triggers)
        self.assertTrue(7 in data_triggers)
        self.assertEqual(len(data_triggers[5].on_update), 1)
        self.assertEqual(len(data_triggers[7].on_create), 1)
        
        # Suppress one of each type
        obj1.suppress(obj1.greet, obj2.sample_fn, FnTriggerType.OnError)
        obj1.suppress(7, obj2.sample_fn, DataTriggerType.OnCreate)
        
        # Verify selective removal
        fn_triggers = obj1._obj.event.get_func_triggers()
        data_triggers = obj1._obj.event.get_data_triggers()
        
        # Check function triggers after suppression
        self.assertTrue(obj1.greet._meta.name in fn_triggers)
        self.assertEqual(len(fn_triggers[obj1.greet._meta.name].on_complete), 1)
        self.assertEqual(len(fn_triggers[obj1.greet._meta.name].on_error), 0)
        
        # Check data triggers after suppression
        self.assertTrue(5 in data_triggers)
        if 7 in data_triggers:
            self.assertEqual(len(data_triggers[7].on_create), 0)
        self.assertEqual(len(data_triggers[5].on_update), 1)
        
    def test_different_trigger_types(self):
        mock = oaas.mock()
        obj1: SampleObj = mock.create_object(sample_cls_meta, 1)
        obj2: SampleObj = mock.create_object(sample_cls_meta, 2)
        obj3: SampleObj = mock.create_object(sample_cls_meta, 3)
        
        # Test all data trigger types
        data_key = 15
        obj1.trigger(data_key, obj2.sample_fn, DataTriggerType.OnCreate)
        obj1.trigger(data_key, obj2.greet, DataTriggerType.OnUpdate)
        obj1.trigger(data_key, obj3.sample_fn, DataTriggerType.OnDelete)
        
        # Verify data triggers
        data_triggers = obj1._obj.event.get_data_triggers()
        self.assertEqual(len(data_triggers), 1)
        self.assertTrue(data_key in data_triggers)
        self.assertEqual(len(data_triggers[data_key].on_create), 1)
        self.assertEqual(len(data_triggers[data_key].on_update), 1)
        self.assertEqual(len(data_triggers[data_key].on_delete), 1)
        
        # Test all function trigger types
        obj1.trigger(obj1.sample_fn, obj2.sample_fn, FnTriggerType.OnComplete)
        obj1.trigger(obj1.sample_fn, obj3.greet, FnTriggerType.OnError)
        
        # Verify function triggers
        fn_triggers = obj1._obj.event.get_func_triggers()
        self.assertEqual(len(fn_triggers), 1)
        fn_id = obj1.sample_fn._meta.name
        self.assertTrue(fn_id in fn_triggers)
        self.assertEqual(len(fn_triggers[fn_id].on_complete), 1)
        self.assertEqual(len(fn_triggers[fn_id].on_error), 1)
