import asyncio
import logging
import unittest

import oprc_py
from .sample_cls import Msg, AsyncSampleObj, oaas, async_sample_cls_meta


class TestServe(unittest.IsolatedAsyncioTestCase):
    
    async def test_grpc_server(self):
        loop = asyncio.get_running_loop() 
        oaas.start_grpc_server(loop, 8080)
        try:
            await asyncio.sleep(1)
        finally:
            oaas.stop_server()
    
    async def test_agent(self):
        oprc_py.init_logger("info,oprc_py=debug")
        loop = asyncio.get_running_loop() 
        await oaas.run_agent(
            loop,
            cls_meta=async_sample_cls_meta,
            obj_id=1,
        )
        try:
            obj: AsyncSampleObj = oaas.load_object(async_sample_cls_meta, 1)
            result = await obj.local_fn(msg=Msg(msg="test"))
            logging.debug("result: %s", result)
            assert result is not None
            assert result.ok
            assert result.msg == "local fn"
        finally:
            await oaas.stop_agent(cls_meta=async_sample_cls_meta, obj_id=1)


if __name__ == "__main__":
    import pytest
    import sys
    pytest.main(sys.argv)