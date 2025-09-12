from __future__ import annotations
import logging
import threading
from typing import Optional

try:
    from oprc_py import init_telemetry_py, forward_log_py, shutdown_telemetry_py  # type: ignore
except Exception:  # pragma: no cover - module might not be present in some build contexts
    def init_telemetry_py(service_name: Optional[str], service_version: Optional[str]):  # type: ignore
        return None
    def forward_log_py(level: int, message: str, module: Optional[str], line: Optional[int], thread: Optional[str]):  # type: ignore
        return None
    def shutdown_telemetry_py():  # type: ignore
        return None

_enabled = False
_needs_retry = False

class _ForwardHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - thin wrapper
        if not _enabled:
            return
        try:
            forward_log_py(
                record.levelno,
                record.getMessage(),
                record.module,
                record.lineno,
                threading.current_thread().name,
            )
        except Exception:
            pass

def enable(service_name: str | None = None, service_version: str | None = None, install_logging: bool = True) -> None:
    global _enabled, _needs_retry
    if _enabled:
        return
    try:
        init_telemetry_py(service_name, service_version)
    except Exception as e:  # If runtime not ready yet, mark for retry
        logging.error("Telemetry init failed:", e)
    if install_logging:
        root = logging.getLogger()
        if not any(isinstance(h, _ForwardHandler) for h in root.handlers):
            root.addHandler(_ForwardHandler())
    _enabled = True

def retry_if_needed(service_name: str | None = None, service_version: str | None = None) -> None:
    global _needs_retry
    if not _needs_retry:
        return
    try:
        init_telemetry_py(service_name, service_version)
        _needs_retry = False
    except Exception:
        # Still failing; leave flag set for potential later retry
        pass

def shutdown():  # pragma: no cover - one-liner
    try:
        shutdown_telemetry_py()
    except Exception:
        pass

__all__ = ["enable", "retry_if_needed", "shutdown"]
