import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session as SQLModelSession
from sqlmodel import create_engine

from concrete.clients import CLIClient

load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///sql_app.db")
CLIClient.emit(f'Connecting to database at {SQLALCHEMY_DATABASE_URL}')

# https://github.com/fastapi/sqlmodel/issues/75
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
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
