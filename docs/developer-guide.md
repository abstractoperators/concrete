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

### Defining a Construct
Use base class defined in `concrete.orm.models` to define a construct.

```python
from concrete.orm.models import Base

class my_table(Base):
    __tablename__ = "my_table" # Unnecessary; defaults to class_name.lower()
    id = Column(Integer, primary_key=True) # Unnecessary; defaults to autoincrementing id

    # Columns
    my_column: Mapped[str] = mapped_column(String(32))
```

### DB Operations
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

### Connection to DB

SQLAlchemy requires a database URL. It's constructed using `sqlalchemy.URL` using environment variables. By default, the constructed URL will be a SQLite database.
For a dockerized Postgres database, place the following into your `.env` file.

```.env
DB_DRIVER=postgresql+psycopg
DB_USERNAME=local_user
DB_PASSWORD=local_password
DB_PORT=5432
DB_HOST=localhost 
DB_DATABASE=local_db
```

Start the postgres server using
`make run-postgres`

When developing locally outside of docker, `DB_HOST` should be set to `localhost`. When developing inside docker, `DB_HOST` should be set to `host.docker.internal`.

### Alembic

We use Alembic to manage database migrations and schema creation locally for postgres.

Migration scripts are tracked with git, and can be used to recreate database schemas at a particular point in time. This can be especially useful for testing staging/prod migrations, because we can recreate their schemas locally.

#### Usage

SQLModel models are used to define migration scripts.
Import all defined models in `migrations/env.py`, e.g. `from concrete.db.orm.models import *`.

Configure target metadata in `migrations/env.py`, e.g. `target_metadata = SQLModel.metadata`.

Import sqlmodel in `script.py.mako` (this is a template file for generating scripts), e.g. `from sqlmodel import SQLModel`.

Add database URL to `alembic.ini` file, e.g. `
sqlalchemy.url = postgresql+psycopg://local_user:local_password@localhost:5432/local_db`

To create a new migration script, run `alembic revision --autogenerate -m 'migration name'`. This will generate a migration script taking the existing database schema to whatever schema is defined by the SQLModel models.

To apply the migration script, run `alembic upgrade head`. This will alter the database schema. You can also use relative migration numbers, e.g. `alembic upgrade +1`, or `alembic downgrade -2`. Similarly, you can use `alembic downgrade partial_migration_number`.

By default, `make run-postgres` applies all migrations to the database, initializing it with the latest schema. 

## Web Dev

### Allow local subdomains
By default, auth will be enabled on webapps even when run locally.
This requires an auth service to be run, which is hosted at a sub-domain in staging/prod.
To mirror this setup locally add the following lines to the bottom of `/etc/hosts`

```
127.0.0.1 abop.bot auth.abop.bot