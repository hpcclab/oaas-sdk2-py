"""Shared pytest fixtures and configuration for OaaS SDK tests (mock-only)."""

import asyncio
import pytest
from oaas_sdk2_py.simplified import oaas, OaasConfig


@pytest.fixture(scope="session", autouse=True)
def configure_mock_session():
    """Session-scoped configuration: mock-only, async mode enabled."""
    oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
    yield
    # Full cleanup after test session
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In rare cases under asyncio_mode=auto, get a fresh loop
            loop = asyncio.new_event_loop()
        loop.run_until_complete(oaas.stop_all_agents())
    except Exception:
        pass


@pytest.fixture(scope="function")
def setup_oaas(event_loop):
    """Per-test setup ensuring mock config and clean agent teardown."""
    oaas.configure(OaasConfig(async_mode=True, mock_mode=True))
    yield
    try:
        event_loop.run_until_complete(oaas.stop_all_agents())
    except Exception:
        pass


@pytest.fixture(scope="function")
def mock_config():
    """Provide a mock OaaS configuration object for direct use."""
    return OaasConfig(async_mode=True, mock_mode=True)


@pytest.fixture(scope="session")
def event_loop():
    """Create a session event loop (Linux-only)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_collection_modifyitems(config, items):
    for item in items:
        fspath = str(getattr(item, "fspath", ""))
        if "/tests/unit/" in fspath:
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.mock_only)
        elif "/tests/integration/" in fspath:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.mock_only)
        elif "/tests/server/" in fspath:
            item.add_marker(pytest.mark.server)
