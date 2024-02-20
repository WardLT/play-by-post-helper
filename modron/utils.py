from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from hashlib import sha1
import logging

from dateutil.tz import tzlocal

logger = logging.getLogger(__name__)


def get_local_tz_offset() -> timedelta:
    """Get the local offset to the current time"""

    return tzlocal().utcoffset(datetime.now())


@cache
def get_version() -> str:
    """Compute a version of the library via a hash"""

    lib_path = Path(__file__).parent
    py_files = sorted(lib_path.rglob("*.py"))
    logger.info(f'Computing hash over {len(py_files)} Python files')
    hasher = sha1()
    for file in py_files:
        hasher.update(file.read_bytes())
    return hasher.hexdigest()
