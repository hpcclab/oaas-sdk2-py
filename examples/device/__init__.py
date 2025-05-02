import json
from oaas_sdk2_py import Oparaca, start_grpc_server, InvocationRequest, InvocationResponse
from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.engine import Session, logger, BaseObject
from oaas_sdk2_py.model import ObjectMeta
from oaas_sdk2_py.pb.oprc import ResponseStatus
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
            status=ResponseStatus.OKAY,
            payload=payload
        )




async def main(port=8080):
    server = await start_grpc_server(oaas, port=port)
    logger.info(f'Serving on {port}')
    await server.wait_closed()

