import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import URL
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session as SQLModelSession
from sqlmodel import create_engine

from concrete.clients import CLIClient

load_dotenv()
DB_PORT = os.environ.get("DB_PORT")
db_port = int(DB_PORT) if DB_PORT else None
SQLALCHEMY_DATABASE_URL = URL.create(
    drivername=os.environ.get("DB_DRIVER", "sqlite"),
    username=os.environ.get("DB_USERNAME", None),
    password=os.environ.get("DB_PASSWORD", None),
    host=os.environ.get("DB_HOST", None),
    port=db_port,
    database=os.environ.get("DB_DATABASE", "sql_app.db"),
)

CLIClient.emit(f'Connecting to database at {SQLALCHEMY_DATABASE_URL}')

if SQLALCHEMY_DATABASE_URL.drivername == "sqlite":
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def Session():
    session = SQLModelSession(engine)
    try:
        yield session
    finally:
        session.close()
