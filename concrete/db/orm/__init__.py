from sqlmodel import SQLModel

from . import models
from .setup import SessionLocal, engine

SQLModel.metadata.create_all(bind=engine)

__all__ = ["models", "schemas", "SessionLocal"]
