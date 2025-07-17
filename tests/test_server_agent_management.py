#!/usr/bin/env python3
"""
Test script for server and agent management functionality.

This script tests the new server and agent management features
implemented according to the design specification.
"""

import asyncio
import time
from oaas_sdk2_py.simplified import oaas, OaasObject, OaasConfig, ServerError, AgentError


@oaas.service("TestService", package="test")
class TestService(OaasObject):
    """Test service for agent management testing."""
    
    counter: int = 0
    
    @oaas.method(serve_with_agent=True)
    async def increment(self) -> int:
        """Test method that can be served with agent."""
        self.counter += 1
        return self.counter
    
    @oaas.method(serve_with_agent=True)
    async def get_counter(self) -> int:
        """Get current counter value."""
        return self.counter


async def test_server_management():
    """Test server management functionality."""
    print("Testing Server Management...")
    
    # Configure OaaS
    config = OaasConfig(async_mode=True, mock_mode=True)
    oaas.configure(config)
    
    # Test server status before starting
    print(f"Server running before start: {oaas.is_server_running()}")
    
    # Start server
    try:
        oaas.start_server(port=8081)  # Use different port to avoid conflicts
        print(f"Server started successfully")
        print(f"Server running after start: {oaas.is_server_running()}")
        
        # Get server info
        server_info = oaas.get_server_info()
        print(f"Server info: {server_info}")
        
        # Test starting server again (should fail)
        try:
            oaas.start_server(port=8082)
            print("ERROR: Should not be able to start server twice")
        except ServerError as e:
            print(f"Expected error when starting server twice: {e}")
        
        # Stop server
        oaas.stop_server()
        print(f"Server stopped successfully")
        print(f"Server running after stop: {oaas.is_server_running()}")
        
        # Test stopping server again (should fail)
        try:
            oaas.stop_server()
            print("ERROR: Should not be able to stop server twice")
        except ServerError as e:
            print(f"Expected error when stopping server twice: {e}")
        
        # Test restart functionality
        oaas.restart_server(port=8083)
        print(f"Server restarted successfully on port 8083")
        print(f"Server info after restart: {oaas.get_server_info()}")
        
        oaas.stop_server()
        
    except Exception as e:
        print(f"Server management test error: {e}")
        if oaas.is_server_running():
            oaas.stop_server()


async def test_agent_management():
    """Test agent management functionality."""
    print("\nTesting Agent Management...")
    
    try:
        # Start server first
        oaas.start_server(port=8084)
        
        # Test starting agent for service class
        agent_id = await oaas.start_agent(TestService)
        print(f"Agent started successfully: {agent_id}")
        
        # List agents
        agents = oaas.list_agents()
        print(f"Running agents: {agents}")
        
        # Test starting agent for specific object
        agent_id_obj = await oaas.start_agent(TestService, obj_id=123)
        print(f"Object-specific agent started: {agent_id_obj}")
        
        # List agents again
        agents = oaas.list_agents()
        print(f"Running agents after adding object-specific: {agents}")
        
        # Test starting agent that's already running (should fail)
        try:
            await oaas.start_agent(TestService)
            print("ERROR: Should not be able to start agent twice")
        except AgentError as e:
            print(f"Expected error when starting agent twice: {e}")
        
        # Stop agent by ID
        await oaas.stop_agent(agent_id)
        print(f"Agent {agent_id} stopped successfully")
        
        # Stop agent by service class and object ID
        await oaas.stop_agent(service_class=TestService, obj_id=123)
        print(f"Agent for TestService:123 stopped successfully")
        
        # List agents (should be empty)
        agents = oaas.list_agents()
        print(f"Running agents after stopping all: {agents}")
        
        # Test stopping non-existent agent (should fail)
        try:
            await oaas.stop_agent("non.existent.agent")
            print("ERROR: Should not be able to stop non-existent agent")
        except AgentError as e:
            print(f"Expected error when stopping non-existent agent: {e}")
        
        # Test convenience methods on class
        class_agent_id = await TestService.start_agent()
        print(f"Agent started via class method: {class_agent_id}")
        
        await TestService.stop_agent()
        print(f"Agent stopped via class method")
        
        # Test convenience methods on instance
        service_instance = TestService.create(obj_id=456)
        instance_agent_id = await service_instance.start_instance_agent()
        print(f"Agent started via instance method: {instance_agent_id}")
        
        await service_instance.stop_instance_agent()
        print(f"Agent stopped via instance method")
        
        # Test stop_all_agents
        await oaas.start_agent(TestService, obj_id=1)
        await oaas.start_agent(TestService, obj_id=2)
        print(f"Started multiple agents: {list(oaas.list_agents().keys())}")
        
        await oaas.stop_all_agents()
        print(f"All agents stopped: {list(oaas.list_agents().keys())}")
        
    except Exception as e:
        print(f"Agent management test error: {e}")
    finally:
        # Cleanup
        try:
            await oaas.stop_all_agents()
            if oaas.is_server_running():
                oaas.stop_server()
        except:
            pass


async def test_integration():
    """Test combined server and agent functionality."""
    print("\nTesting Integration...")
    
    try:
        # Configure and start server
        config = OaasConfig(async_mode=True, mock_mode=True)
        oaas.configure(config)
        
        oaas.start_server(port=8085)
        print("Server started for integration test")
        
        # Start agent
        agent_id = await oaas.start_agent(TestService)
        print(f"Agent started for integration test: {agent_id}")
        
        # Simulate some work
        print("Server and agent are running...")
        
        # Check system health
        server_info = oaas.get_server_info()
        agents = oaas.list_agents()
        
        print(f"System status:")
        print(f"  Server: {server_info}")
        print(f"  Agents: {len(agents)} running")
        
        # Cleanup
        await oaas.stop_agent(agent_id)
        oaas.stop_server()
        print("Integration test completed successfully")
        
    except Exception as e:
        print(f"Integration test error: {e}")
    finally:
        try:
            await oaas.stop_all_agents()
            if oaas.is_server_running():
                oaas.stop_server()
        except:
            pass


async def main():
    """Run all tests."""
    print("Starting Server and Agent Management Tests")
    print("=" * 50)
    
    await test_server_management()
    await test_agent_management()
    await test_integration()
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
