import unittest
from oprc_py import FnTriggerType, DataTriggerType
from oaas_sdk2_py import oaas, OaasConfig
from tests.sample_cls import SampleObj


class TestEvent(unittest.TestCase):
    def test_add_event(self):
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        obj1: SampleObj = SampleObj.create(obj_id=1)
        obj2: SampleObj = SampleObj.create(obj_id=2)

        obj1.trigger(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)
        obj1.trigger(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)

        self.assertTrue(obj1._obj.event is not None)
        fn_triggers = obj1._obj.event.get_func_triggers()
        self.assertEqual(len(fn_triggers), 1)
        self.assertTrue(obj1.greet._meta.name in fn_triggers)
        on_complete_triggers = fn_triggers[obj1.greet._meta.name].on_complete
        self.assertEqual(len(on_complete_triggers), 1)
        target = on_complete_triggers[0]
        self.assertEqual(target.cls_id, obj2.meta.cls_id)
        self.assertEqual(target.partition_id, obj2.meta.partition_id)
        self.assertEqual(target.object_id, obj2.meta.object_id)
        self.assertEqual(target.fn_id, obj2.sample_fn._meta.name)

    def test_add_data_trigger(self):
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        obj1: SampleObj = SampleObj.create(obj_id=1)
        obj2: SampleObj = SampleObj.create(obj_id=2)
        data_key = 5
        obj1.trigger(data_key, obj2.sample_fn, DataTriggerType.OnUpdate)
        self.assertTrue(obj1._obj.event is not None)
        data_triggers = obj1._obj.event.get_data_triggers()
        self.assertEqual(len(data_triggers), 1)
        self.assertTrue(data_key in data_triggers)
        on_update_triggers = data_triggers[data_key].on_update
        self.assertEqual(len(on_update_triggers), 1)
        target = on_update_triggers[0]
        self.assertEqual(target.cls_id, obj2.meta.cls_id)
        self.assertEqual(target.partition_id, obj2.meta.partition_id)
        self.assertEqual(target.object_id, obj2.meta.object_id)
        self.assertEqual(target.fn_id, obj2.sample_fn._meta.name)

    def test_suppress_fn_trigger(self):
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        obj1: SampleObj = SampleObj.create(obj_id=1)
        obj2: SampleObj = SampleObj.create(obj_id=2)
        obj1.trigger(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)
        fn_triggers = obj1._obj.event.get_func_triggers()
        self.assertEqual(len(fn_triggers), 1)
        self.assertTrue(obj1.greet._meta.name in fn_triggers)
        self.assertEqual(len(fn_triggers[obj1.greet._meta.name].on_complete), 1)
        obj1.suppress(obj1.greet, obj2.sample_fn, FnTriggerType.OnComplete)
        fn_triggers = obj1._obj.event.get_func_triggers()
        if obj1.greet._meta.name in fn_triggers:
            self.assertEqual(len(fn_triggers[obj1.greet._meta.name].on_complete), 0)

    def test_suppress_data_trigger(self):
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        obj1: SampleObj = SampleObj.create(obj_id=1)
        obj2: SampleObj = SampleObj.create(obj_id=2)
        data_key = 10
        obj1.trigger(data_key, obj2.sample_fn, DataTriggerType.OnUpdate)
        data_triggers = obj1._obj.event.get_data_triggers()
        self.assertEqual(len(data_triggers), 1)
        self.assertTrue(data_key in data_triggers)
        self.assertEqual(len(data_triggers[data_key].on_update), 1)
        obj1.suppress(data_key, obj2.sample_fn, DataTriggerType.OnUpdate)
        data_triggers = obj1._obj.event.get_data_triggers()
        if data_key in data_triggers:
            self.assertEqual(len(data_triggers[data_key].on_update), 0)

    def test_multiple_triggers(self):
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        obj1: SampleObj = SampleObj.create(obj_id=1)
        obj2: SampleObj = SampleObj.create(obj_id=2)
        obj3: SampleObj = SampleObj.create(obj_id=3)
        data_key = 15
        obj1.trigger(data_key, obj2.sample_fn, DataTriggerType.OnCreate)
        obj1.trigger(data_key, obj2.greet, DataTriggerType.OnUpdate)
        obj1.trigger(data_key, obj3.sample_fn, DataTriggerType.OnDelete)
        data_triggers = obj1._obj.event.get_data_triggers()
        self.assertEqual(len(data_triggers), 1)
        self.assertTrue(data_key in data_triggers)
        self.assertEqual(len(data_triggers[data_key].on_create), 1)
        self.assertEqual(len(data_triggers[data_key].on_update), 1)
        self.assertEqual(len(data_triggers[data_key].on_delete), 1)
        obj1.trigger(obj1.sample_fn, obj2.sample_fn, FnTriggerType.OnComplete)
        obj1.trigger(obj1.sample_fn, obj3.greet, FnTriggerType.OnError)
        fn_triggers = obj1._obj.event.get_func_triggers()
        self.assertEqual(len(fn_triggers), 1)
        fn_id = obj1.sample_fn._meta.name
        self.assertTrue(fn_id in fn_triggers)
        self.assertEqual(len(fn_triggers[fn_id].on_complete), 1)
        self.assertEqual(len(fn_triggers[fn_id].on_error), 1)
