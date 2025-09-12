from __future__ import annotations
import time
import logging
from oaas_sdk2_py.simplified import oaas, OaasObject
from oaas_sdk2_py.telemetry import enable as enable_telemetry

logger = logging.getLogger("telemetry_demo")

@oaas.service("CounterService", package="telemetry.demo")
class Counter(OaasObject):
    count: int = 0

    @oaas.method()
    def inc(self, delta: int = 1) -> int:
        logger.info("Incrementing by %s", delta)
        self.count += delta
        return self.count

    @oaas.method()
    def busy(self, ms: int = 50) -> int:
        logger.info("Simulating busy work for %sms", ms)
        start = time.time()
        time.sleep(ms / 1000.0)
        elapsed = int((time.time() - start) * 1000)
        logger.info("Busy work done in %sms", elapsed)
        return elapsed

# Optional explicit enable; if env vars (OTEL_EXPORTER_OTLP_ENDPOINT etc.) are set,
# the package auto-enables already. This is just to show manual activation.
def init_telemetry_if_requested():
    if not oaas.is_server_running():  # safe place before server start
        enable_telemetry(service_name="telemetry-demo")
