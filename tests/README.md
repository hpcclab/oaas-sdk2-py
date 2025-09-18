# Tests Overview

Structure
- `tests/unit/`: Fast, isolated tests using the simplified API. Always mock-only.
- `tests/integration/`: Multi-component flows in mock mode (e.g., session/RPC chaining). No sleeps; use async/await.
- `tests/server/`: Server/agent lifecycle tests; currently skipped. Activate when non-mock is supported.
- `tests/shared/`: Utilities/services shared by tests.

Conventions
- Global config: mock-only via `tests/conftest.py` autouse fixture.
- Event loop: Linux-focused loop in `event_loop` fixture.
- Markers: `unit`, `integration`, `server`, `mock_only` are auto-applied by folder in `pytest_collection_modifyitems`.
- Accessors: `@oaas.getter/@oaas.setter` are wrapped for persisted state; not exported as RPC.

Running
- All tests:
  ```bash
  uv run pytest -q
  ```
- Units only:
  ```bash
  uv run pytest -q tests/unit
  ```
- Integrations only:
  ```bash
  uv run pytest -q tests/integration
  ```

Notes
- Keep tests asynchronous when calling async paths; avoid time.sleep.
- Server tests are placeholders until non-mock paths are ready.
