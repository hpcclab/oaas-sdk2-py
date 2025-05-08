import asyncio
import oprc_py
import sys

class TestHandler:
    async def invoke_fn(self, req: oprc_py.InvocationRequest) -> oprc_py.InvocationResponse:
        return oprc_py.InvocationResponse(req.payload)

    async def invoke_obj(self, req: oprc_py.ObjectInvocationRequest) -> oprc_py.InvocationResponse:
        payload = f"hello from python ({req.cls_id}, {req.fn_id}, {req.object_id})".encode("utf-8")
        return oprc_py.InvocationResponse(payload)

async def start(engine):
    engine.start_server(TestHandler())

async def test_callback():
    return "test"
    
if __name__ == "__main__":
    if sys.platform != "win32":
        import uvloop
        uvloop.install()
    else:
        import winloop
        winloop.install()
    oprc_py.init_logger()
    engine = oprc_py.OaasEngine()
    loop = asyncio.new_event_loop() 
    engine.serve_grpc_server(loop, TestHandler())
    try:
        loop.run_forever()
    finally:
        engine.stop_server()
        # loop.close()
    
    # asyncio.run(start(engine))