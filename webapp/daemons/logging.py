import logging
import os

from concrete_db.orm.models import Log
from concrete_db.orm.setup import Session

dname = os.path.dirname(__file__)

logging.basicConfig(
    level=logging.DEBUG,
    filename=os.path.join(dname, "server.log"),
    filemode="w",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class LogDBHandler(logging.Handler):
    """
    Custom logging handler to log to database as specified by env variables.
    """

    def __init__(self):
        super().__init__()

    def emit(self, record: logging.LogRecord):
        with Session() as session:
            log = Log(
                level=record.levelname,
                message=record.getMessage(),
            )
            session.add(log)
            session.commit()
