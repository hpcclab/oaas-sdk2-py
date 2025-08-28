import logging
import os
from oaas_sdk2_py import oaas

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Include time in logs; use a single basicConfig to set both level and format.
logging.basicConfig(
	level=LOG_LEVEL,
	format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
	datefmt="%Y-%m-%d %H:%M:%S",
)

# Silence overly chatty third-party logger
logging.getLogger('hpack').setLevel(logging.CRITICAL)

oaas.run_or_gen()