import inspect
from oaas_sdk2_py.model import ClsMeta, FuncMeta
from .sample_cls import AsyncSampleObj, SampleObj, async_sample_cls_meta

def test_cls():
    cls_meta = AsyncSampleObj.__cls_meta__
    assert isinstance(cls_meta, ClsMeta)
    assert cls_meta == async_sample_cls_meta
    assert cls_meta.cls_id == "default.TestAsync"
    assert cls_meta.name == "TestAsync"
    assert cls_meta.pkg == "default"
    
def test_func():
    greet = AsyncSampleObj.greet
    assert isinstance(greet, FuncMeta)
    assert greet.name == "greet"
    assert not greet.stateless
    assert not greet.serve_with_agent
    assert AsyncSampleObj.local_fn.serve_with_agent
    
def test_sync_func():
    sync_greet = SampleObj.greet
    assert isinstance(sync_greet, FuncMeta)
    assert not inspect.iscoroutinefunction(sync_greet.invoke_handler)
    assert not inspect.iscoroutinefunction(sync_greet.func)
    assert not sync_greet.is_async