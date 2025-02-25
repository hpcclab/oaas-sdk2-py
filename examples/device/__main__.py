import asyncio
import logging
import os
import sys
from .__init__ import main, oaas

def run_device():
    # TODO run in device agent mode
    pass

if __name__ == '__main__':
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    level = logging.getLevelName(LOG_LEVEL)
    logging.basicConfig(level=level)
    logging.getLogger('hpack').setLevel(logging.CRITICAL)
    os.environ.setdefault("OPRC_ODGM_URL", "http://localhost:10000")
    if sys.argv.__len__() > 1 and sys.argv[1] == "gen":
        oaas.meta_repo.print_pkg()
    if sys.argv.__len__() > 1 and sys.argv[1] == "agent":
        run_device()
    else:
        os.environ.setdefault("HTTP_PORT", "8080")
        port = int(os.environ.get("HTTP_PORT"))
        asyncio.run(main(port))