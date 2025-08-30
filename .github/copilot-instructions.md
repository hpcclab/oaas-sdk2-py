# Copilot instructions for oaas-sdk2-py

Purpose: help AI agents be productive in this codebase by capturing the architecture, workflows, and project-specific conventions you’ll actually use here.

## Architecture at a glance
- Two layers coexist:
  - Legacy API: `Oparaca`, `Session`, `BaseObject` (see `oaas_sdk2_py/engine.py`, `session.py`, `obj.py`). Still supported and used by some tests.
  - Simplified API: global `oaas` service registry with decorators and auto state mgmt (see `oaas_sdk2_py/simplified/**`). Prefer this for new code.
- Data plane and RPC:
  - Backed by Rust crate `oprc-py` (PyO3), exposing `DataManager` and `RpcManager` used by `Oparaca`.
  - Mock mode swaps in local managers for fast tests (`mock.py`).
- Object model:
  - `@oaas.service(name, package)` registers a class; `@oaas.method` exposes RPC methods.
  - Typed attributes on a service subclass of `OaasObject` become persisted state via `StateDescriptor` indices; serialization handled for you.
  - Accessors `@oaas.getter/@oaas.setter` read/write persisted fields directly and are NOT exported as standalone RPC endpoints.
- Serving and agents:
  - gRPC server: `OaasService.start_server()` hosts all registered services for client RPC calls (independent of agents).
  - Agents: `serve_with_agent=True` methods are consumed by background agents started via `OaasService.start_agent()`; they listen on message-queue keys (see `engine.run_agent`).
  - Invocation handlers auto-commit after each call to persist state (see `handler.py`).

## Core workflows
- Install and build (uses uv):
  - Sync deps and build wheel: `uv sync`, `uv build`.
  - Use `uv run` to execute Python commands in the project environment (examples: `uv run pytest -v`, `uv run python -m examples.helloworld`).
  - Rust bridge dev: `just maturin-dev` inside `oprc-py` if changing Rust core.
- Tests:
  - Pytest config lives in `pyproject.toml` and `pytest.ini`; async is auto.
  - Typical run: `uv run pytest -v` (uses `tests/`), includes integration like `test_serve.py` and simplified API tests.
- Local/server runs:
  - Example package entry: `examples/helloworld/__main__.py` calls `oaas.run_or_gen()`.
  - Modes: no args → start server (HTTP_PORT env, default 8080); `gen` → print package spec (YAML by default or `--format json`).
  - Run locally with uv: `uv run python -m examples.helloworld`.
  - Docker: `docker-compose.yml` spins up ODGM + router + an app container using `deploy/Dockerfile` with `deploy/oaas-run.sh` autodetecting script/module to run.

## Project conventions and patterns
- Prefer simplified API:
  - Define services: `@oaas.service("Name", package="pkg") class S(OaasObject): ...`
  - Add methods: `@oaas.method()` or `@oaas.method(stateless=True, serve_with_agent=True)`.
  - Persisted state: declare typed attributes on the class (e.g., `count: int = 0`) — they’re auto-serialized and stored by index.
  - Accessors are for direct state access and not exported as RPC: `@oaas.getter("count")`, `@oaas.setter("count")`.
- Config and sessions:
  - Configure once: `oaas.configure(OaasConfig(mock_mode=True|False, async_mode=True|False, auto_commit=...))`.
  - AutoSessionManager is created under the hood and used by handlers; manual `Session` is still available via legacy API or `OaasService.get_session()`.
- Server vs agent:
  - Server is for external gRPC calls to regular methods; agents handle `serve_with_agent=True` methods for a specific object id.
  - Agents are per object instance; default object id is `1` if not provided.
- Package metadata export:
  - Use `@oaas.package(...)` on the class to include version/metadata; export via `oaas.print_pkg()` or CLI `gen`. See `repo.py` and `simplified/service.py`.

## Examples you can mirror
- Minimal service:
  - File: `README.md` Quick Start; also see tests in `tests/test_simplified_compatibility.py` for patterns covering state, methods, mock mode.
- Server/agent lifecycle:
  - Start server: `oaas.start_server(port=8080)` / `oaas.stop_server()`; check `is_server_running()` and `get_server_info()`.
  - Start/stop agent: `await oaas.start_agent(ServiceClass, obj_id=123)` / `await oaas.stop_agent(...)`; list via `oaas.list_agents()`.

## Key files and directories
- Simplified API: `oaas_sdk2_py/simplified/{service.py,objects.py,decorators.py,accessors.py,state_descriptor.py,session_manager.py,config.py}`
- Legacy bridge/engine: `oaas_sdk2_py/{engine.py,handler.py,session.py,obj.py,model.py,repo.py,mock.py}`
- CI/release and runner image: `.github/workflows/{CI.yml,runner-image.yml}`
- Runtime container: `deploy/{Dockerfile,oaas-run.sh}`
- Compose topology for local ODGM/router/app: `docker-compose.yml`

Notes and gotchas
- Handlers always commit after invocation; avoid performing long-running work that shouldn’t be part of a commit cycle.
- In mock mode, `OaasObject.create(local=True)` is implied; in non-mock mode, you may want explicit `local=False` for remote semantics.
- Accessors don’t create RPC endpoints; expose external reads/writes via methods when needed.

If anything here is unclear or you want more detail (e.g., ODGM routing keys, accessor projections), say what you’re building and I’ll refine these rules.