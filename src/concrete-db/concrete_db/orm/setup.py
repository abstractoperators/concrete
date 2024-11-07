import os
from contextlib import contextmanager

from concrete.clients import CLIClient
from dotenv import load_dotenv
from sqlalchemy import URL
from sqlmodel import Session as SQLModelSession
from sqlmodel import create_engine

load_dotenv(override=True)
if (
    (drivername := os.environ.get("DB_DRIVER")) is None
    or (username := os.environ.get("DB_USERNAME")) is None
    or (password := os.environ.get("DB_PASSWORD")) is None
    or (host := os.environ.get("DB_HOST")) is None
    or (db_port := int(os.environ.get("DB_PORT") or "0")) == 0
    or (database := os.environ.get("DB_DATABASE")) is None
):
    CLIClient.emit("Missing environment variables for database connection. Defaulting to SQLite.")
    SQLALCHEMY_DATABASE_URL = URL.create(drivername="sqlite", database="sql_app.db")
else:
    SQLALCHEMY_DATABASE_URL = URL.create(
        drivername=drivername,
        username=username,
        password=password,
        host=host,
        port=db_port,
        database=database,
    )
    CLIClient.emit(f"Database environment variables found. ORM URL configured as: {SQLALCHEMY_DATABASE_URL}")


if SQLALCHEMY_DATABASE_URL.drivername == "sqlite":
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)


@contextmanager
def Session():
    session = SQLModelSession(engine)
    try:
        yield session
    finally:
        session.close()
