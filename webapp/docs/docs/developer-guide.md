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