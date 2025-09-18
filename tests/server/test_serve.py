import asyncio
import unittest

from oaas_sdk2_py import oaas, OaasConfig
from tests.sample_cls import Msg, AsyncSampleObj


class TestServe(unittest.IsolatedAsyncioTestCase):
    async def test_grpc_server(self):
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        loop = asyncio.get_running_loop()
        oaas.start_server(port=8080, loop=loop)
        try:
            await asyncio.sleep(0.1)
        finally:
            oaas.stop_server()

    async def test_agent(self):
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        loop = asyncio.get_running_loop()
        await oaas.start_agent(AsyncSampleObj, obj_id=1, loop=loop)
        try:
            obj: AsyncSampleObj = AsyncSampleObj.load(1)
            result = await obj.local_fn(msg=Msg(msg="test"))
            assert result.ok and result.msg == "local fn"
        finally:
            await oaas.stop_agent(service_class=AsyncSampleObj, obj_id=1)
