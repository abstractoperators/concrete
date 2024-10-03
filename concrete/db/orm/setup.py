import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import URL
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session as SQLModelSession
from sqlmodel import create_engine

from concrete.clients import CLIClient

load_dotenv()
SQLALCHEMY_DATABASE_URL = URL.create(
    drivername=os.getenv("DB_DRIVER", "sqlite"),
    username=os.getenv("DB_USERNAME", ""),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", ""),
    port=int(os.getenv("DB_PORT", "")),
    database=os.getenv("DB_DATABASE", ""),
)

CLIClient.emit(SQLALCHEMY_DATABASE_URL.database)
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
