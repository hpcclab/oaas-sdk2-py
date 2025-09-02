import asyncio
import logging
import unittest

import oprc_py
from oaas_sdk2_py import oaas, OaasConfig
from .sample_cls import Msg, AsyncSampleObj


class TestServe(unittest.IsolatedAsyncioTestCase):
    
    async def test_grpc_server(self):
        # Configure OaaS for async mock mode and start the server
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        loop = asyncio.get_running_loop() 
        oaas.start_server(port=8080, loop=loop)
        try:
            await asyncio.sleep(1)
        finally:
            oaas.stop_server()
    
    async def test_agent(self):
        oprc_py.init_logger("info,oprc_py=debug")
        # Configure OaaS for async mock mode and start an agent for object 1
        oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
        loop = asyncio.get_running_loop() 
        await oaas.start_agent(AsyncSampleObj, obj_id=1, loop=loop)
        try:
            obj: AsyncSampleObj = AsyncSampleObj.load(1)
            result = await obj.local_fn(msg=Msg(msg="test"))
            logging.debug("result: %s", result)
            assert result is not None
            assert result.ok
            assert result.msg == "local fn"
        finally:
            await oaas.stop_agent(service_class=AsyncSampleObj, obj_id=1)


if __name__ == "__main__":
    import pytest
    import sys
    pytest.main(sys.argv)