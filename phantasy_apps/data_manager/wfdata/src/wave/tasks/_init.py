import logging
import sys
from pathlib import Path

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler("/files/shared/ap/HLA/wfdata/log")
for handler in (stream_handler, file_handler):
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# the root dirpath for data file storate
data_rootdir = Path("/files/shared/ap/HLA/wfdata")
# data_rootdir = Path("./test-data")
