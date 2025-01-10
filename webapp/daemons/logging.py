import logging
import os

from concrete_db.orm.models import Base
from concrete_db.orm.setup import Session
from sqlmodel import Field

dname = os.path.dirname(__file__)

logging.basicConfig(
    level=logging.DEBUG,
    filename=os.path.join(dname, "server.log"),
    filemode="w",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class Log(Base, table=True):
    level: str = Field(default=None, max_length=10)
    message: str = Field(default=None)


class LogDBHandler(logging.Handler):
    """
    Custom logging handler to log to database as specified by env variables.
    """

    def __init__(self, app: str):
        super.__init__()

    def emit(self, record: logging.log):
        with Session() as session:
            log = Log(
                level=record.levelname,
                message=record.message,
            )
            session.add(log)
            session.commit()
