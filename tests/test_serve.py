import unittest


from oaas_sdk2_py import start_grpc_server
from .sample_cls import Msg, SampleObj, oaas


class TestStuff(unittest.IsolatedAsyncioTestCase):
    async def test_with_engine(self):
        port = 28080
        grpc_server = await start_grpc_server(oaas, port=port)
        p_id = 0
        task = await oaas.serve_local_function(
            cls_id="default.test", fn_name="fn-1", partition_id=p_id, obj_id=1
        )
        try:
            ctx = oaas.new_context(partition_id=p_id)
            cls_meta = oaas.meta_repo.get_cls_meta("default.test")
            obj: SampleObj = ctx.create_object_from_ref(cls_meta, 1)
            result = await obj.sample_fn(msg=Msg(msg="test"))
            assert result is not None
            assert result.ok
            assert result.msg == "test"
        finally:
            task.cancel()
            grpc_server.close()
