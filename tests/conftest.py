"""
Shared pytest fixtures and configuration for OaaS SDK tests.
"""

import pytest
from oaas_sdk2_py.simplified import oaas, OaasConfig


@pytest.fixture(scope="function")
def setup_oaas():
    """Setup OaaS with mock mode for testing."""
    config = OaasConfig(async_mode=True, mock_mode=True)
    oaas.configure(config)
    yield
    # Cleanup after test
    try:
        # Stop any running servers/agents
        if hasattr(oaas, 'stop_all_agents'):
            import asyncio
            asyncio.get_event_loop().run_until_complete(oaas.stop_all_agents())
        if hasattr(oaas, 'is_server_running') and oaas.is_server_running():
            oaas.stop_server()
    except:
        pass


@pytest.fixture(scope="function") 
def mock_config():
    """Provide a mock OaaS configuration."""
    return OaasConfig(async_mode=True, mock_mode=True)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
