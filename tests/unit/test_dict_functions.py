from pydantic import BaseModel
from oaas_sdk2_py import Oparaca, OaasObject


class TestResultModel(BaseModel):
    __test__ = False
    success: bool
    message: str
    data: dict = {}


def test_dict_function_support():
    oaas = Oparaca()
    test_cls_meta = oaas.new_cls("DictTestClass")

    @test_cls_meta
    class DictTestObj(OaasObject):
        @test_cls_meta.func()
        def process_dict(self, data: dict) -> TestResultModel:
            return TestResultModel(
                success=True,
                message=f"Processed dict with keys: {list(data.keys())}",
                data=data,
            )

        @test_cls_meta.func()
        def process_untyped(self, data) -> TestResultModel:
            return TestResultModel(
                success=True,
                message=f"Processed untyped data: {type(data).__name__}",
                data=data if isinstance(data, dict) else {"raw": str(data)},
            )

    assert "process_dict" in test_cls_meta.func_dict
    assert "process_untyped" in test_cls_meta.func_dict
    dict_func_meta = test_cls_meta.func_dict["process_dict"]
    untyped_func_meta = test_cls_meta.func_dict["process_untyped"]
    assert dict_func_meta.name == "process_dict"
    assert untyped_func_meta.name == "process_untyped"


def test_async_dict_function_support():
    oaas = Oparaca()
    async_test_cls_meta = oaas.new_cls("AsyncDictTestClass")

    @async_test_cls_meta
    class AsyncDictTestObj(OaasObject):
        @async_test_cls_meta.func()
        async def process_dict_async(self, data: dict) -> TestResultModel:
            return TestResultModel(
                success=True,
                message=f"Async processed dict with keys: {list(data.keys())}",
                data=data,
            )

        @async_test_cls_meta.func()
        async def process_untyped_async(self, data) -> TestResultModel:
            return TestResultModel(
                success=True,
                message=f"Async processed untyped data: {type(data).__name__}",
                data=data if isinstance(data, dict) else {"raw": str(data)},
            )

    assert "process_dict_async" in async_test_cls_meta.func_dict
    assert "process_untyped_async" in async_test_cls_meta.func_dict
    dict_func_meta = async_test_cls_meta.func_dict["process_dict_async"]
    untyped_func_meta = async_test_cls_meta.func_dict["process_untyped_async"]
    assert dict_func_meta.name == "process_dict_async"
    assert dict_func_meta.is_async
    assert untyped_func_meta.name == "process_untyped_async"
    assert untyped_func_meta.is_async


def test_dict_function_caller_creation():
    oaas = Oparaca()
    test_cls_meta = oaas.new_cls("CallerTestClass")

    @test_cls_meta
    class CallerTestObj(OaasObject):
        @test_cls_meta.func()
        def dict_func(self, data: dict) -> dict:
            return {"received": data}

        @test_cls_meta.func()
        def untyped_func(self, data) -> dict:
            return {"received": data}

    dict_func_meta = test_cls_meta.func_dict["dict_func"]
    untyped_func_meta = test_cls_meta.func_dict["untyped_func"]
    assert dict_func_meta.invoke_handler is not None
    assert untyped_func_meta.invoke_handler is not None
