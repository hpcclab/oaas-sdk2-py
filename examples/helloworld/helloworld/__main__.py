import asyncio
import json
import os
import sys
from .__init__ import main, oaas

if __name__ == '__main__':
    os.environ.setdefault("OPRC_ODGM_URL", "http://localhost:10000")
    if sys.argv.__len__() > 1 and sys.argv[1] == "gen":
        oaas.meta_repo.print_pkg()
    else:
        asyncio.run(main())