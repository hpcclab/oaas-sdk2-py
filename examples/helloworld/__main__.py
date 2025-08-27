import asyncio
import logging
import os
import sys
from oaas_sdk2_py import oaas


def setup_event_loop():
    """Set up the most appropriate event loop for the platform."""
    import asyncio
    import platform
    if platform.system() != "Windows":
        try:
            import uvloop # type: ignore
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logging.info("Using uvloop")
        except ImportError:
            logging.warning("uvloop not available, using asyncio")
    else:
        logging.info("Running on Windows, using winloop")
        try:
            import winloop # type: ignore
            winloop.install()
            logging.info("Using winloop")
        except ImportError:
            logging.warning("winloop not available, using asyncio")

if __name__ == '__main__':
    # Set up logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(level=LOG_LEVEL)
    logging.getLogger('hpack').setLevel(logging.CRITICAL)
    
    # Set default environment variables
    os.environ.setdefault("OPRC_ODGM_URL", "http://localhost:10000")
    os.environ.setdefault("HTTP_PORT", "8080")
    
    if len(sys.argv) > 1 and sys.argv[1] == "gen":
        print(oaas.print_pkg())
    else:
        port = int(os.environ.get("HTTP_PORT", "8080"))
        setup_event_loop()
        loop = asyncio.new_event_loop() 
        oaas.start_server(port=port, loop=loop)
        try:
            loop.run_forever()
        finally:
            oaas.stop_server()