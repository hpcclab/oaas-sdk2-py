from __future__ import annotations
import os
import logging

from oaas_sdk2_py.config import OaasConfig
from oaas_sdk2_py.telemetry import shutdown_telemetry_py
from .service import Counter, init_telemetry_if_requested
from oaas_sdk2_py import oaas
logging.basicConfig(level="INFO")

oaas.configure(OaasConfig(mock_mode=True, async_mode=True))
# Manual opt-in (safe even if already auto-enabled)
if os.environ.get("DEMO_FORCE_ENABLE_TELEMETRY"):
    init_telemetry_if_requested()

# Create an object instance (id=1 implicit) and exercise methods
counter = Counter.create()
print("Initial count:", counter.count)
print("Increment ->", counter.inc())
print("Increment by 5 ->", counter.inc(5))
print("Busy work latency ms ->", counter.busy(80))

print("If OTEL env vars were set, spans and logs were exported.")
print("Set OTEL_EXPORTER_OTLP_ENDPOINT to enable real export, e.g.:")
print("  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317")
print("  export OTEL_SERVICE_NAME=telemetry-demo")
print("  python -m examples.telemetry_demo")


shutdown_telemetry_py()