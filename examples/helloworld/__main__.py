import asyncio
import logging
import os
import sys
from .__init__ import main, oaas

def setup_event_loop():
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
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    level = logging.getLevelName(LOG_LEVEL)
    logging.basicConfig(level=level)
    logging.getLogger('hpack').setLevel(logging.CRITICAL)
    os.environ.setdefault("OPRC_ODGM_URL", "http://localhost:10000")
    if sys.argv.__len__() > 1 and sys.argv[1] == "gen":
        oaas.meta_repo.print_pkg()
    else:
        os.environ.setdefault("HTTP_PORT", "8080")
        port = int(os.environ.get("HTTP_PORT"))
        setup_event_loop()
        asyncio.run(main(port))