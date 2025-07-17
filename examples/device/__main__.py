import asyncio
import logging
import os
import sys

import psutil
from pydantic import BaseModel

from oaas_sdk2_py import oaas
from oaas_sdk2_py.simplified import OaasObject, OaasConfig


class DeviceMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float


# Configure OaaS with simplified interface
config = OaasConfig(async_mode=True, mock_mode=False)
oaas.configure(config)


@oaas.service("ComputeDevice", package="example")
class ComputeDevice(OaasObject):
    """A compute device that monitors system metrics."""

    @oaas.method(serve_with_agent=True)
    async def update_state(self) -> DeviceMetrics:
        """Update and return current system metrics."""
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        
        return DeviceMetrics(
            cpu_percent=cpu_usage, 
            memory_percent=memory_info.percent
        )

    @oaas.method()
    async def get_system_info(self) -> dict:
        """Get basic system information."""
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        
        return {
            "cpu_percent": cpu_usage,
            "memory_percent": memory_info.percent,
            "available_memory_gb": memory_info.available / (1024**3)
        }

    @oaas.method(serve_with_agent=True)
    async def monitor_continuously(self, duration_seconds: int) -> dict:
        """Monitor system for a specified duration and return average metrics."""
        cpu_samples = []
        memory_samples = []
        
        # Sample every second for the specified duration
        for _ in range(duration_seconds):
            cpu_usage = psutil.cpu_percent(interval=1.0)
            memory_info = psutil.virtual_memory()
            
            cpu_samples.append(cpu_usage)
            memory_samples.append(memory_info.percent)
        
        # Calculate averages
        return {
            "avg_cpu_percent": sum(cpu_samples) / len(cpu_samples),
            "avg_memory_percent": sum(memory_samples) / len(memory_samples),
            "samples_taken": len(cpu_samples),
            "duration_seconds": duration_seconds
        }

    @oaas.method()
    async def is_healthy(self, cpu_threshold: float = 80.0, memory_threshold: float = 90.0) -> bool:
        """Check if system is healthy based on thresholds."""
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        
        cpu_ok = cpu_usage < cpu_threshold
        memory_ok = memory_info.percent < memory_threshold
        
        return cpu_ok and memory_ok

    @oaas.method()
    async def get_cpu_usage(self) -> float:
        """Get current CPU usage as a float."""
        cpu_usage = psutil.cpu_percent(interval=0.1)
        return cpu_usage

    @oaas.method()
    async def get_memory_usage(self) -> float:
        """Get current memory usage as a float."""
        memory_info = psutil.virtual_memory()
        return memory_info.percent

    @oaas.method()
    async def get_process_count(self) -> int:
        """Get number of running processes."""
        return len(psutil.pids())


async def run_device_agent():
    """Run the device as an agent."""
    print("Starting device agent...")
    
    # Start server
    port = int(os.environ.get("HTTP_PORT", "8080"))
    loop = asyncio.get_event_loop()
    oaas.start_server(port=port, loop=loop)
    print("✓ gRPC server started")
    
    try:
        # Start agent for ComputeDevice
        agent_id = await oaas.start_agent(ComputeDevice)
        print(f"✓ ComputeDevice agent started: {agent_id}")
        
        print("🖥️  Device agent is running. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(5)
                # Optionally, update metrics periodically
                device = ComputeDevice.create(local=True)
                metrics = await device.update_state()
                print(f"📊 Current metrics: CPU: {metrics.cpu_percent:.1f}%, Memory: {metrics.memory_percent:.1f}%")
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down device agent...")
            
    finally:
        # Cleanup
        await oaas.stop_all_agents()
        oaas.stop_server()
        print("✓ Device agent stopped")


async def test_device_locally():
    """Test the device functionality locally."""
    print("Testing device functionality locally...")
    
    device = ComputeDevice.create(local=True)
    
    # Test DeviceMetrics return
    metrics = await device.update_state()
    print(f"📊 Current metrics: {metrics}")
    
    # Test dict return
    system_info = await device.get_system_info()
    print(f"�️  System info: {system_info}")
    
    # Test primitive type methods
    print("\n🔧 Testing primitive type methods:")
    
    # Test float returns
    cpu_usage = await device.get_cpu_usage()
    memory_usage = await device.get_memory_usage()
    print(f"  CPU usage: {cpu_usage:.1f}% (type: {type(cpu_usage)})")
    print(f"  Memory usage: {memory_usage:.1f}% (type: {type(memory_usage)})")
    
    # Test int return
    process_count = await device.get_process_count()
    print(f"  Process count: {process_count} (type: {type(process_count)})")
    
    # Test bool return with float parameters
    is_healthy_default = await device.is_healthy()
    is_healthy_strict = await device.is_healthy(50.0, 70.0)  # Stricter thresholds
    print(f"  Is healthy (default): {is_healthy_default} (type: {type(is_healthy_default)})")
    print(f"  Is healthy (strict): {is_healthy_strict} (type: {type(is_healthy_strict)})")
    
    # Test int parameter
    print("\n⏱️  Testing continuous monitoring with int parameter:")
    short_monitor = await device.monitor_continuously(3)  # 3 seconds
    print(f"  3-second monitoring: {short_monitor}")
    
    print("\n✅ Local testing completed (including primitive types!)")


def setup_event_loop():
    """Set up the most appropriate event loop for the platform."""
    import platform
    if platform.system() != "Windows":
        try:
            import uvloop  # type: ignore
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logging.info("Using uvloop")
        except ImportError:
            logging.warning("uvloop not available, using asyncio")
    else:
        logging.info("Running on Windows, using asyncio")
        try:
            import winloop  # type: ignore
            winloop.install()
            logging.info("Using winloop")
        except ImportError:
            logging.warning("winloop not available, using asyncio")


if __name__ == '__main__':
    # Set up logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    level = logging.getLevelName(LOG_LEVEL)
    logging.basicConfig(level=level)
    logging.getLogger('hpack').setLevel(logging.CRITICAL)
    
    # Set default environment variables
    os.environ.setdefault("OPRC_ODGM_URL", "http://localhost:10000")
    os.environ.setdefault("HTTP_PORT", "8080")
    
    if len(sys.argv) > 1 and sys.argv[1] == "gen":
        # Generate package metadata
        print("Generating package metadata...")
        print("Package metadata generation not yet implemented for new API")
    elif len(sys.argv) > 1 and sys.argv[1] == "agent":
        # Run as device agent
        setup_event_loop()
        try:
            asyncio.run(run_device_agent())
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test locally
        setup_event_loop()
        try:
            asyncio.run(test_device_locally())
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        # Run server only (no agents)
        port = int(os.environ.get("HTTP_PORT", "8080"))
        setup_event_loop()
        loop = asyncio.new_event_loop()
        oaas.start_server(port=port, loop=loop)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        finally:
            oaas.stop_server()
            print("✓ Server stopped")
            print("👋 Goodbye!")