import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import URL
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session as SQLModelSession
from sqlmodel import create_engine

from concrete.clients import CLIClient

load_dotenv(override=True)
db_username = os.environ.get("DB_USERNAME") or None
db_password = os.environ.get("DB_PASSWORD") if db_username else None
db_host = os.environ.get("DB_HOST") or None
db_port_str = os.environ.get("DB_PORT") or None
db_port = int(db_port_str) if db_host and db_port_str else None
SQLALCHEMY_DATABASE_URL = URL.create(
    drivername=os.environ.get("DB_DRIVER", "sqlite"),
    username=db_username,
    password=db_password,
    host=db_host,
    port=db_port,
    database=os.environ.get("DB_DATABASE", "sql_app.db"),
)

CLIClient.emit(f'ORM URL configured as: {SQLALCHEMY_DATABASE_URL}')

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
