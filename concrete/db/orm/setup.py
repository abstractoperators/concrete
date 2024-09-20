import os

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

# TODO Remove; in-memory is worse because it's harder to examine.
if os.path.exists("sql_app.db"):
    os.remove("sql_app.db")

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///sql_app.db")
print(f"SQLALCHEMY_DATABASE_URL: {SQLALCHEMY_DATABASE_URL}")

# https://github.com/fastapi/sqlmodel/issues/75
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
