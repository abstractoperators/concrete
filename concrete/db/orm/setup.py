import os

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from concrete.clients import CLIClient

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///sql_app.db")
CLIClient.emit(f'Connecting to database at {SQLALCHEMY_DATABASE_URL}')

# https://github.com/fastapi/sqlmodel/issues/75
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
