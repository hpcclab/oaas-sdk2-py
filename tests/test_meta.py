from oaas_sdk2_py.model import ClsMeta, FuncMeta
from .sample_cls import SampleObj, sample_cls_meta

def test_cls():
    cls_meta = SampleObj.__cls_meta__
    assert isinstance(cls_meta, ClsMeta)
    assert cls_meta == sample_cls_meta
    assert cls_meta.cls_id == "default.test"
    assert cls_meta.name == "test"
    assert cls_meta.pkg == "default"
    
def test_func():
    greet = SampleObj.greet
    assert isinstance(greet, FuncMeta)
    assert greet.name == "greet"
    assert not greet.stateless
    assert not greet.serve_with_agent
    assert SampleObj.local_fn.serve_with_agent