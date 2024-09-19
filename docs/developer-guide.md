# Developer Guide
## Setup
### Pyenv
Pyenv allows you to manage multiple versions of Python on your computer. It can configure a default Python version globally or on a directory basis.

```shell
curl https://pyenv.run | bash  # to install Pyenv

echo -e 'export PYENV_ROOT="$HOME/.pyenv"\nexport PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo -e 'eval "$(pyenv init --path)"\n eval "$(pyenv init -)"' >> ~/.bashrc  # to set up environment variables

exec "$SHELL"  # restarts the terminal shell process

pyenv –version  # to confirm Pyenv has installed successfully

pyenv install 3.11.9  # to install Python 3.11.9

pyenv global 3.11.9

# Alternatively, to set in a particular directory where the projects will be built
# cd /Users/personmcpersonsonson/git/concreteproject
# pyenv local 3.11.9
```

### Poetry
Concrete uses poetry for dependency management and environment isolation.

```shell
curl -sSL https://install.python-poetry.org | python3 -

# By default, poetry as a command should be accessible.
# If not, add it to your path

# For mac
# echo -e 'export PATH="~/Library/Application Support/pypoetry/venv/bin/poetry:$PATH"' >> ~/.bashrc
```

## SQL Alchemy

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
