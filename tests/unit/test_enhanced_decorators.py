#!/usr/bin/env python3
# Copied from tests/test_enhanced_decorators.py (mock-only context)
from oaas_sdk2_py.simplified import (
    OaasObject, OaasConfig, oaas,
    DecoratorError,
    DebugLevel, configure_debug,
)
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import pytest
import traceback


class TestRequest(BaseModel):
    __test__ = False
    value: int = 0
    data: str = ""
    timestamp: datetime = datetime.now()


class TestResponse(BaseModel):
    __test__ = False
    result: int = 0
    message: str = ""
    processed_at: datetime = datetime.now()


class TestEnhancedDecorators:
    def test_enhanced_service_decorator_basic(self):
        configure_debug(level=DebugLevel.DEBUG, performance_monitoring=True)
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)

        try:
            @oaas.service("EnhancedTestService", package="test")
            class EnhancedTestService(OaasObject):
                counter: int = 0
                name: str = "test"
                tags: List[str] = []
                metadata: Dict[str, Any] = {}

                @oaas.method()
                def increment(self) -> TestResponse:
                    self.counter += 1
                    return TestResponse(result=self.counter, message="incremented")

                @oaas.method(name="custom_name", stateless=True)
                def stateless_method(self, req: TestRequest) -> TestResponse:
                    return TestResponse(result=req.value * 2, message="doubled")

                @oaas.method(strict=True, timeout=5.0)
                async def async_method(self, req: TestRequest) -> TestResponse:
                    await asyncio.sleep(0.1)
                    return TestResponse(result=req.value, message="async processed")

                @oaas.method(retry_count=3, retry_delay=0.1)
                def retry_method(self, req: TestRequest) -> TestResponse:
                    if not hasattr(self, '_retry_attempts'):
                        self._retry_attempts = 0
                    self._retry_attempts += 1
                    if self._retry_attempts < 3:
                        raise ValueError("Simulated failure")
                    return TestResponse(result=req.value, message="retry successful")

            service = EnhancedTestService.create(obj_id=1)
            result = service.increment()
            assert result.result == 1 and result.message == "incremented"
            result = service.stateless_method(TestRequest(value=5))
            assert result.result == 10 and result.message == "doubled"

            async def test_async():
                result = await service.async_method(TestRequest(value=42))
                assert result.result == 42 and result.message == "async processed"

            asyncio.run(test_async())
            result = service.retry_method(TestRequest(value=100))
            assert result.result == 100 and result.message == "retry successful"

            # Basic sanity: service registered and callable paths executed

        except Exception as e:
            traceback.print_exc()
            pytest.fail(f"Enhanced service decorator test failed: {e}")

    def test_enhanced_method_decorator_features(self):
        configure_debug(level=DebugLevel.DEBUG, performance_monitoring=True)
        config = OaasConfig(mock_mode=True)
        oaas.configure(config)

        try:
            @oaas.service("MethodTestService", package="test")
            class MethodTestService(OaasObject):
                @oaas.method(timeout=1.0)
                async def timeout_method(self, req: TestRequest) -> TestResponse:
                    await asyncio.sleep(2.0)
                    return TestResponse(result=req.value, message="should not reach here")

                @oaas.method(retry_count=2, retry_delay=0.1)
                def flaky_method(self, req: TestRequest) -> TestResponse:
                    raise ValueError("Always fails")

                @oaas.method(serve_with_agent=True)
                def agent_method(self, req: TestRequest) -> TestResponse:
                    return TestResponse(result=req.value, message="agent processed")

            service = MethodTestService.create(obj_id=1)

            async def test_timeout():
                with pytest.raises(Exception):
                    await service.timeout_method(TestRequest(value=1))

            asyncio.run(test_timeout())

            with pytest.raises(DecoratorError) as ectx:
                service.flaky_method(TestRequest(value=1))
            assert "failed" in str(ectx.value).lower()

            result = service.agent_method(TestRequest(value=42))
            assert result.result == 42 and result.message == "agent processed"

        except Exception as e:
            traceback.print_exc()
            pytest.fail(f"Enhanced method decorator test failed: {e}")
