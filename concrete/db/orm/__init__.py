from . import models, schemas
from .setup import SessionLocal, SQLModel, engine

SQLModel.metadata.create_all(bind=engine)

__all__ = ["models", "schemas", "SessionLocal"]
