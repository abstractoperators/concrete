import logging
import os

from concrete_db.orm.models import Base, MetadataMixin, init_sqlite_db
from concrete_db.orm.setup import Session
from sqlmodel import Field

dname = os.path.dirname(__file__)

logging.basicConfig(
    level=logging.DEBUG,
    filename=os.path.join(dname, "server.log"),
    filemode="w",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class LogBase(Base):
    level: str = Field(default=None, description="Log level, e.g., INFO, WARNING,...", max_length=10)
    message: str = Field(default=None, description="Log message. Possibly a json dump.")


class Log(LogBase, MetadataMixin, table=True):
    pass


init_sqlite_db()


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
