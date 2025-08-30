from pydantic import BaseModel
from oaas_sdk2_py import Oparaca, BaseObject


class TestResultModel(BaseModel):
    __test__ = False  # prevent pytest from collecting as a test class
    success: bool
    message: str
    data: dict = {}


def test_dict_function_support():
    """Test that cls_meta.func() supports dictionary input types"""
    oaas = Oparaca()
    test_cls_meta = oaas.new_cls("DictTestClass")
    
    @test_cls_meta
    class DictTestObj(BaseObject):
        
        @test_cls_meta.func()
        def process_dict(self, data: dict) -> TestResultModel:
            """Function that explicitly accepts dict type"""
            return TestResultModel(
                success=True,
                message=f"Processed dict with keys: {list(data.keys())}",
                data=data
            )
        
        @test_cls_meta.func()
        def process_untyped(self, data) -> TestResultModel:
            """Function without type annotation (should default to dict)"""
            return TestResultModel(
                success=True,
                message=f"Processed untyped data: {type(data).__name__}",
                data=data if isinstance(data, dict) else {"raw": str(data)}
            )
    
    # Test that the functions are properly registered
    assert "process_dict" in test_cls_meta.func_dict
    assert "process_untyped" in test_cls_meta.func_dict
    
    # Test function metadata
    dict_func_meta = test_cls_meta.func_dict["process_dict"]
    untyped_func_meta = test_cls_meta.func_dict["process_untyped"]
    
    assert dict_func_meta.name == "process_dict"
    assert untyped_func_meta.name == "process_untyped"
    
    print("✓ Dictionary function support tests passed!")


def test_async_dict_function_support():
    """Test that cls_meta.func() supports dictionary input types for async functions"""
    oaas = Oparaca()
    async_test_cls_meta = oaas.new_cls("AsyncDictTestClass")
    
    @async_test_cls_meta
    class AsyncDictTestObj(BaseObject):
        
        @async_test_cls_meta.func()
        async def process_dict_async(self, data: dict) -> TestResultModel:
            """Async function that explicitly accepts dict type"""
            return TestResultModel(
                success=True,
                message=f"Async processed dict with keys: {list(data.keys())}",
                data=data
            )
        
        @async_test_cls_meta.func()
        async def process_untyped_async(self, data) -> TestResultModel:
            """Async function without type annotation (should default to dict)"""
            return TestResultModel(
                success=True,
                message=f"Async processed untyped data: {type(data).__name__}",
                data=data if isinstance(data, dict) else {"raw": str(data)}
            )
    
    # Test that the functions are properly registered
    assert "process_dict_async" in async_test_cls_meta.func_dict
    assert "process_untyped_async" in async_test_cls_meta.func_dict
    
    # Test function metadata
    dict_func_meta = async_test_cls_meta.func_dict["process_dict_async"]
    untyped_func_meta = async_test_cls_meta.func_dict["process_untyped_async"]
    
    assert dict_func_meta.name == "process_dict_async"
    assert dict_func_meta.is_async
    assert untyped_func_meta.name == "process_untyped_async"
    assert untyped_func_meta.is_async
    
    print("✓ Async dictionary function support tests passed!")


def test_dict_function_caller_creation():
    """Test that the caller functions are created correctly for dict types"""
    oaas = Oparaca()
    test_cls_meta = oaas.new_cls("CallerTestClass")
    
    @test_cls_meta
    class CallerTestObj(BaseObject):
        
        @test_cls_meta.func()
        def dict_func(self, data: dict) -> dict:
            return {"received": data}
        
        @test_cls_meta.func()
        def untyped_func(self, data) -> dict:
            return {"received": data}
    
    # Test that invoke handlers are created
    dict_func_meta = test_cls_meta.func_dict["dict_func"]
    untyped_func_meta = test_cls_meta.func_dict["untyped_func"]
    
    assert dict_func_meta.invoke_handler is not None
    assert untyped_func_meta.invoke_handler is not None
    
    print("✓ Dictionary function caller creation tests passed!")


if __name__ == "__main__":
    test_dict_function_support()
    test_async_dict_function_support()
    test_dict_function_caller_creation()
    print("\n🎉 All dictionary function tests passed!")
