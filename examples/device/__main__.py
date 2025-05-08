import asyncio
import logging
import os
import sys

import json

from oprc_py.oprc_py import InvocationRequest, InvocationResponse
from oaas_sdk2_py import Oparaca
from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.engine import Session,  BaseObject
from oaas_sdk2_py.model import ObjectMeta
import psutil

oaas = Oparaca(config=OprcConfig())
device = oaas.new_cls(pkg="example", name="device")

@device
class ComputeDevice(BaseObject):
    def __init__(self, meta: ObjectMeta = None, ctx: Session = None):
        super().__init__(meta, ctx)

    @device.data_getter(index=0)
    async def get_compute_state(self, raw: bytes=None) -> dict:
        return json.loads(raw.decode("utf-8"))


    @device.data_setter(index=0)
    async def set_compute_state(self, data: dict) -> bytes:
        return json.dumps(data).encode("utf-8")
    
    @device.func()
    async def update_state(self, req: InvocationRequest):
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        metrics = {"cpu_percent": cpu_usage, "memory_percent": memory_info.percent}
        self.set_compute_state(metrics)
        payload = json.dumps(metrics).encode("utf-8")
        return InvocationResponse(
            payload=payload
        )


def run_device():
    # TODO run in device agent mode
    pass


def setup_event_loop():
    import asyncio
    import platform
    if platform.system() != "Windows":
        try:
            import uvloop # type: ignore
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logging.info("Using uvloop")
        except ImportError:
            logging.warning("uvloop not available, using asyncio")
    else:
        logging.info("Running on Windows, using winloop")
        try:
            import winloop # type: ignore
            winloop.install()
            logging.info("Using winloop")
        except ImportError:
            logging.warning("winloop not available, using asyncio")


if __name__ == '__main__':
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    level = logging.getLevelName(LOG_LEVEL)
    logging.basicConfig(level=level)
    logging.getLogger('hpack').setLevel(logging.CRITICAL)
    os.environ.setdefault("OPRC_ODGM_URL", "http://localhost:10000")
    if sys.argv.__len__() > 1 and sys.argv[1] == "gen":
        oaas.meta_repo.print_pkg()
    if sys.argv.__len__() > 1 and sys.argv[1] == "agent":
        run_device()
    else:
        os.environ.setdefault("HTTP_PORT", "8080")
        port = int(os.environ.get("HTTP_PORT"))
        setup_event_loop()
        loop = asyncio.new_event_loop() 
        oaas.start_grpc_server(loop, port=port)
        try:
            loop.run_forever()
        finally:
            oaas.stop_server()