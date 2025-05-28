import asyncio
import oprc_py
import sys
import signal

class TestHandler:
    def invoke_fn(self, req: oprc_py.InvocationRequest) -> oprc_py.InvocationResponse:
        return oprc_py.InvocationResponse(req.payload)

    def invoke_obj(self, req: oprc_py.ObjectInvocationRequest) -> oprc_py.InvocationResponse:
        payload = f"hello from python ({req.cls_id}, {req.fn_id}, {req.object_id})".encode("utf-8")
        return oprc_py.InvocationResponse(payload)

async def test_callback():
    return "test"
    
if __name__ == "__main__":
    if sys.platform != "win32":
        import uvloop
        uvloop.install()
    else:
        import winloop
        winloop.install()
    oprc_py.init_logger("info")
    engine = oprc_py.OaasEngine()
    loop = asyncio.new_event_loop() 
    engine.serve_grpc_server(8080, TestHandler())
    try:
        # loop.run_forever()
        # Create an event to wait on
        stop_event = asyncio.Event()

        # Set up signal handlers
        def handle_sigterm(signum, frame):
            print("Received SIGTERM, shutting down...")
            stop_event.set()

        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigterm)  # Also handle Ctrl+C

        # Wait until the event is set by a signal
        loop.run_until_complete(stop_event.wait())
    finally:
        engine.stop_server()