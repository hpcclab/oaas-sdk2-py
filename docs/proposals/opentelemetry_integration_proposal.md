# Proposal: OpenTelemetry Integration (Tracing, Metrics, Logs)

Scope: Add optional, configurable OpenTelemetry (OTel) tracing, metrics, and log export for the Rust runtime (`oprc-py` crate) and surface a Python-facing enablement API that captures ("scrapes") Python logs and forwards them into the same OTel pipeline. Interface‑first design; implementation details are sketched for feasibility.

## Goals
- End-to-end distributed tracing across RPC boundaries (Rust <-> Python logical operations) with W3C Trace Context propagation.
- Baseline metrics for RPC throughput, latency, errors, serialization size, and session counts.
- Unified log pipeline: Rust `tracing` events + Python `logging` records exported via OTLP.
- Configuration via environment variables & programmatic API; entirely opt-in and zero overhead (beyond a cheap feature flag) when disabled.
- Minimal disruption: additive, backward compatible, safe defaults.

## Non-Goals
- Full custom query UI (delegated to external backends like Jaeger, Tempo, Honeycomb, OTEL collectors).
- Advanced metrics cardinality management (initial release ships with conservative label sets).
- Automatic profiling / continuous CPU & memory capture (future consideration).

## User-Facing Summary
| Capability | Python User Experience | Default |
|------------|------------------------|---------|
| Tracing | `oaas.enable_telemetry(traces=True)` or env vars | Off |
| Metrics | Same call; emitted from Rust runtime | Off |
| Logs | Python logs automatically forwarded once enabled | Off |
| Export Endpoint | `OAAS_OTEL_EXPORTER_OTLP_ENDPOINT` | none |
| Service Name | `OAAS_SERVICE_NAME` or param | Derived from package/module |
| Sampling | `OAAS_OTEL_TRACES_SAMPLER=parentbased_always_on|ratio:0.1` | always_on |

## Architecture Overview
```
+-----------------+          +------------------+          +----------------------+
|  Python Service |  FFI     |   Rust (oprc-py)  |  OTLP    |  OTel Collector /    |
|  (user methods) +--------->+  Tracing/Metrics  +--------->+  Backend (Jaeger...) |
|  logging, ctx    <---------+  Context Propag.  | <--------+  (optional feedback) |
+-----------------+          +------------------+          +----------------------+
         ^   ^                       ^   ^
         |   |                       |   |
  (traceparent)                 (rpc spans, metrics, logs)
```

### Data Flows
1. Python method invocation begins: a span is created (Python helper) OR context extracted from inbound RPC metadata.
2. RPC call from Python -> Rust: context injected into invocation request headers; Rust extracts and creates child span.
3. Rust internal operations (serialization, handler dispatch) emit structured tracing events and metrics.
4. Python logging records (via custom handler) are forwarded through an FFI function into Rust, converted to `tracing::Event`, and exported via OTel log pipeline or converted into span events.

## Rust Instrumentation Plan (`oprc-py` crate)
Add dependencies (feature-gated):
```toml
[features]
telemetry = ["tracing", "tracing-subscriber", "tracing-opentelemetry", "opentelemetry", "opentelemetry-otlp"]

[dependencies]
tracing = { version = "0.1", optional = true }
tracing-subscriber = { version = "0.3", optional = true, features=["env-filter","registry"] }
tracing-opentelemetry = { version = "0.23", optional = true }
opentelemetry = { version = "0.23", optional = true, features=["rt-tokio"] }
opentelemetry-otlp = { version = "0.16", optional = true, features=["http-proto", "reqwest-client"] }
opentelemetry-semantic-conventions = { version = "0.16", optional = true }
```

### Initialization
Function `telemetry::init(config: TelemetryConfig)` (called from Python enable API) sets:
- Tracer provider with resource attrs: `service.name`, `service.version`, `deployment.environment`.
- Optional batch span processor (Tokio runtime) with OTLP exporter (grpc or http/proto autodetect).
- Metrics: use OTel `Meter` to create instruments (counter, histogram, up/down counter) – exported via same OTLP endpoint (Temporarily optional if metrics stabilization concerns; can ship behind sub-flag `enable_metrics`).
- Logs: near-term pragmatic approach—map log records + Python forwarded logs into span events (or use `tracing-opentelemetry` logs API if stable). Future upgrade path: native OTel logs pipeline once crate maturity is sufficient.

### Instrumentation Points
| File | Span / Metric | Notes |
|------|---------------|-------|
| `engine.rs` | Root span per engine run / request dispatch | Name: `engine.dispatch` |
| `rpc.rs` | Child span per RPC call | Name: `rpc.call` attributes (method, cls_id, object_id) |
Implementation Note (updated): A unified `telemetry` module now exposes `telemetry::instrument(fut, span_name)` which wraps a future with a span when the `telemetry` feature is compiled, and is a no-op otherwise. This removes scattered `#[cfg(feature="telemetry")]` blocks and centralizes the feature gate. Python log forwarding uses `telemetry::forward_log` behind the same module, and initialization occurs through `telemetry::init`.

| `handler/*` | Span around handler execution | Error status mapping |
| `model.rs` / `obj.rs` | Serialization size metrics | Histogram `rpc_payload_bytes` |
| `data.rs` | Storage interactions metrics | `storage_op_latency_ms` |
| `async_handler.rs` / `sync_handler.rs` | Concurrency gauges | Active handlers gauge |

### Metrics (Initial Set)
- Counter: `rpc_requests_total{method,cls_id,success}`
- Histogram: `rpc_request_duration_ms{method,cls_id}` (bounded buckets)
- Counter: `rpc_errors_total{method,cls_id,error_kind}`
- Histogram: `rpc_payload_bytes{direction=IN|OUT}`
- UpDownCounter: `active_sessions`
- Counter: `python_logs_forwarded_total{level}`

### Context Propagation
- Embed trace context into invocation metadata: add optional field `trace_headers: Vec<(String,String)>` inside existing request struct (or a lightweight map) serialized with existing mechanism.
- Extraction: On inbound, attempt `opentelemetry::global::get_text_map_propagator().extract(carrier)`; create span with parent. On outbound, inject before sending.
- Python side uses same W3C headers; if absent, starts new root span.

## Python Integration
Add helper in Python layer (e.g., `oaas_sdk2_py/telemetry.py` – new file) providing:
```python
def enable_telemetry(
    *,
    traces: bool = True,
    metrics: bool = True,
    logs: bool = True,
    endpoint: str | None = None,
    service_name: str | None = None,
    log_level: int = logging.INFO,
    sampler: str | None = None,
) -> None: ...
```
Steps performed:
1. Resolve config from params / env.
2. Call into Rust FFI function `oprc_py.init_telemetry(**resolved)` (exposed via pyo3) which initializes once (idempotent).
3. Install Python `LoggingHandler` subclass that forwards each record to `oprc_py.forward_log(level, msg, module, line, extras)`.
4. Provide context API wrappers (optionally thin; or rely on Rust spans only). Minimal Python span support using `contextvars` for correlation when Python itself originates a call before FFI.

### Python Log Forwarder
Pseudo-code:
```python
class _OtelForwardHandler(logging.Handler):
    def emit(self, record):
        try:
            opc = getattr(oprc_py, "forward_log", None)
            if opc is not None:
                opc(
                    level=record.levelno,
                    message=self.format(record),
                    module=record.module,
                    line=record.lineno,
                    thread=record.threadName,
                )
        except Exception:  # Keep logging robust
            pass
```
Rust side maps to `tracing::event!(Level::INFO, python.module=?, python.line=?, message=? )`.

## Configuration Sources (precedence)
1. Explicit function arguments to `enable_telemetry()`
2. Standard OpenTelemetry environment variables
3. Sensible internal defaults (no-op providers if partially configured)

### Standard Environment Variables (OTel Spec)
We adopt only spec-defined names to avoid fragmentation:
- `OTEL_SERVICE_NAME` (or `service.name` inside `OTEL_RESOURCE_ATTRIBUTES`)
- `OTEL_RESOURCE_ATTRIBUTES` (comma list, e.g. `service.name=oaas-example,deployment.environment=dev`)
- `OTEL_EXPORTER_OTLP_ENDPOINT` (base; e.g. `http://localhost:4318`)
- `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` / `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` / `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` (optional overrides)
- `OTEL_TRACES_SAMPLER` (`always_on`, `always_off`, `parentbased_always_on`, `traceidratio` etc.)
- `OTEL_TRACES_SAMPLER_ARG` (e.g. `0.1` when sampler is `traceidratio`)
- `OTEL_METRICS_EXPORTER` (`otlp` or `none`; default `otlp` when endpoint present)
- `OTEL_LOGS_EXPORTER` (`otlp` or `none`; default `otlp` when endpoint present)
- `OTEL_EXPORTER_OTLP_PROTOCOL` (`http/protobuf` or `grpc`)

### Optional (Runtime Convenience Flags)
For fine control without introducing non-standard keys we interpret absence as disabled:
- Metrics disabled if `OTEL_METRICS_EXPORTER=none`.
- Logs disabled if `OTEL_LOGS_EXPORTER=none`.
- If no OTLP endpoint variables are set, telemetry stays no-op unless explicitly provided via function arguments.

### Service Name Inference
Priority order for determining the effective `service.name` resource attribute:
1. Explicit `service_name` argument to `enable_telemetry()`.
2. `OTEL_SERVICE_NAME` environment variable (or `service.name` inside `OTEL_RESOURCE_ATTRIBUTES`).
3. Single registered OaaS service class: `<package>.<ClassName>` (derived from the `@oaas.service` decorator). If package missing, just `<ClassName>`.
4. Multiple registered service classes: fallback to `oaas-multi` (users should set a name explicitly if they need differentiation). Optionally we could include a deterministic hash suffix later for uniqueness (not necessary initially).
5. Absolute final fallback: `unknown_service:oaas` (mirrors OTel spec guidance) if for some reason registration list is empty at init time.

The resource may still include other attributes from `OTEL_RESOURCE_ATTRIBUTES`; we never override those except for `service.name` when rules above apply.

### Mapping from Python API Arguments
| Argument | Result if provided | Fallback if None |
|----------|--------------------|------------------|
| `service_name` | Sets / overrides `service.name` | Inference chain above |
| `endpoint` | Sets `OTEL_EXPORTER_OTLP_ENDPOINT` (and used for all signals unless signal-specific endpoints set) | Existing env values |
| `sampler` | Sets `OTEL_TRACES_SAMPLER` (and optionally `OTEL_TRACES_SAMPLER_ARG`) | Env sampler or `parentbased_always_on` |
| `traces/metrics/logs` bools | If False: force corresponding `*_EXPORTER=none` | Use env exporters |

No `OAAS_`-prefixed variables are introduced; users rely on cross-tooling standard names.

## Error Handling & Fallbacks
- Telemetry init failures (exporter unreachable) log a single warning and fall back to no-op providers.
- Forwarded Python log call failures are swallowed (never break user code flow).
- If metrics exporter creation fails but traces succeed, partial enablement persists and is reported.

## Performance Considerations
- Disabled path: all macros behind `#[cfg(feature="telemetry")]` + `if !ENABLED.load(Ordering::Relaxed)` early return.
- Sampling reduces span creation cost; recommend default parent-based always-on.
- Metrics recorders use pre-allocated instruments; attribute cardinality bounded (avoid object_id except in debug builds).
- Python log forwarding is synchronous but minimal; consider batching future optimization if high volume.

## Backward Compatibility
- No required code changes for existing users.
- Telemetry only activates when feature compiled + runtime enabled.
- Invocation schemas add optional metadata—old clients ignore, new clients read.

## Testing Strategy
1. Unit tests (Rust): ensure spans created with expected attributes (use in-memory exporter).
2. Unit tests (Python): enable telemetry and emit logs; assert Rust receives via mock FFI (temporary test hook).
3. Integration test: spin OTLP collector (test container) and assert reception of trace + metrics + log events.
4. Load test: measure overhead with telemetry on/off (target <5% throughput degradation at p50 with sampling 1.0 in moderate load; document results).

## Minimal Implementation Steps
1. Add feature & dependencies to `Cargo.toml`.
2. Create `telemetry.rs` module (config struct, init function, global flags, exporters).
3. Add context inject/extract helpers in `rpc.rs`.
4. Instrument spans & metrics at key points (guarded).
5. Expose pyo3 FFI functions: `init_telemetry`, `forward_log`.
6. Add Python helper module + logging handler.
7. Add docs & example (`examples/telemetry_demo.py`).
8. Write tests with in-memory OTel exporter (Rust) and Python log forwarding.
9. Documentation in `reference.md` & new tutorial section.

## Open Questions
- Should we offer a pure-Python fallback (no Rust feature) that only configures logging & sets trace headers? (Tentative: not in first iteration.)
- Use dedicated OTel logs pipeline vs span events? (Start with span events for stability; upgrade later.)
- Provide pluggable exporter configuration (e.g., stdout, jaeger) vs rely solely on OTLP? (Initial: OTLP + optional stdout.)
- Dynamic reconfiguration (change sampling at runtime)? (Future; first version static.)

## Future Extensions
- Add exemplars / high-cardinality attributes via tail sampling.
- Correlate GC / memory stats metrics.
- Automatic instrumentation for popular async runtimes & HTTP client libs in Python side.
- Structured error events linking to spans with stack traces.

## Quick Reference
- Enable (Python): `oaas.enable_telemetry(endpoint="http://localhost:4318")` (if only one service class registered, its `<package>.<Name>` becomes `service.name`).
- Env only: set `OTEL_EXPORTER_OTLP_ENDPOINT` and optionally `OTEL_SERVICE_NAME`, then call `oaas.enable_telemetry()` (no args needed).
- Disable logs: `OTEL_LOGS_EXPORTER=none` or `oaas.enable_telemetry(logs=False)`.
- Disable metrics: `OTEL_METRICS_EXPORTER=none` or `oaas.enable_telemetry(metrics=False)`.
- Use sampling: `OTEL_TRACES_SAMPLER=traceidratio` + `OTEL_TRACES_SAMPLER_ARG=0.1`.
- Build with feature: `cargo build --features telemetry`.

---
This proposal delivers a cohesive, incremental telemetry layer leveraging OpenTelemetry standards to give immediate observability value while preserving performance and compatibility.
