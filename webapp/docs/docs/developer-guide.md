# SQL Alchemy

SQLAlchemy is an SQL toolkit and ORM library for Python. We use it in concrete to persist.

## Defining a Construct
Use base class defined in `concrete.orm.models` to define a construct.

```python
from concrete.orm.models import Base

class my_table(Base):
    __tablename__ = "my_table" # Unnecessary; defaults to class_name.lower()
    id = Column(Integer, primary_key=True) # Unnecessary; defaults to autoincrementing id

    # Columns
    my_column: Mapped[str] = mapped_column(String(32))
```

## DB Operations
Use `concrete.db.orm.SessionLocal` to get a session. 
Use this session to perform DB operations. Best practice is to use one session per one transaction. By default, sessions will not flush or commit.

```python
from concrete.db.orm import SessionLocal

# The following solutions achieve the same thing, but with different approaches
# ORM Centric solution

def delete_my_table_orm():
    session = SessionLocal()
    deleted_count = session.query(my_table).filter(my_column == 'my_value').delete()
    session.commit()
    return deleted_count

def delete_my_table_core():
    session = SessionLocal()
    stmt = delete(my_table).where(my_column == 'my_value')
    result = session.execute(stmt)
    deleted_count = result.rowcount
    session.commit()
    return deleted_count
```