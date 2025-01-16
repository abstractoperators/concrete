import logging
import os

from concrete_db.crud import write_log
from concrete_db.orm.setup import Session

dname = os.path.dirname(__file__)


class LogDBHandler(logging.Handler):
    """
    Custom logging handler to log to database as specified by env variables.
    """

    def __init__(self):
        super().__init__()

    def emit(self, record: logging.LogRecord):
        with Session() as session:
            write_log(session, record)


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
