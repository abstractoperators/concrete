# Developer Guide

Welcome to Abstract Operator's developer guide for `concrete`!
This guide will take you through environment setup in order to run the codebase locally and contribute to our project. It's recommended that you use MacOS, Unix, or Linux as an operating system for development; we do not support nor provide instructions for Windows systems and development.

## Setup

### [Github Repository](https://github.com)

```shell
# HTTPS
git clone https://github.com/abstractoperators/concrete.git

# SSH
git clone git@github.com:abstractoperators/concrete.git
```

### [Python](https://www.python.org)

#### [Pyenv](https://github.com/pyenv/pyenv)

Pyenv allows you to manage multiple versions of Python on your computer.
It can configure a default Python version globally or on a directory basis.

> We recommend following the official instructions on the Pyenv Github repository for
[Installation](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation),
completing the entire block before skipping to [Python Version](#python-version).

Alternatively, you can follow our abridged instructions here:

```shell
curl https://pyenv.run | bash  # to install Pyenv
```

For **bash**:

```shell
echo -e 'export PYENV_ROOT="$HOME/.pyenv"\nexport PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo -e 'eval "$(pyenv init --path)"\n eval "$(pyenv init -)"' >> ~/.bashrc  # to set up environment variables
```

For **zsh**:

```shell
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
```

And finally for both:

```shell
exec "$SHELL"  # restarts the terminal shell process
```

#### Python Version
After you've installed Pyenv, we can install the required version of Python:
```shell
pyenv install 3.11.9  # to install Python 3.11.9

pyenv global 3.11.9

# Alternatively, to set in a particular directory where the projects will be built
# cd /Users/personmcpersonsonson/git/concreteproject
# pyenv local 3.11.9
```

### [Poetry](https://python-poetry.org)

Concrete uses poetry for dependency management and environment isolation.

> Again, we recommend following the official
[installation instructions](https://python-poetry.org/docs/#installing-with-the-official-installer).

Otherwise, run the following:

```shell
curl -sSL https://install.python-poetry.org | python3 -
```

By default, poetry as a command should be accessible.
If not, you'll need to manually add it to your path.

For example, on MacOS systems:

```shell
# bash
echo -e 'export PATH="~/Library/Application Support/pypoetry/venv/bin/poetry:$PATH"' >> ~/.bashrc

# zsh
echo -e 'export PATH="~/Library/Application Support/pypoetry/venv/bin/poetry:$PATH"' >> ~/.zshrc
```

For Linux/Unix:

```shell
# bash
echo -e 'export PATH="~/.local/share/pypoetry/venv/bin/poetry"' >> ~/.bashrc

# zsh
echo -e 'export PATH="~/.local/share/pypoetry/venv/bin/poetry"' >> ~/.zshrc
```

In addition to package and dependency management, we use Poetry to augment the developer git workflow.
The following command will install the correct dependencies to run `concrete` locally as well as the precommit packages to pass our PR validations.
In the root folder of the repository:

```shell
make install
```

If you find yourself needing to run the pre-commit manually, use the following:

```shell
poetry run pre-commit run --all-files
```

### Environment Variables

We recommend you store all of the relevant environment variables into a `.env` file
located in the root directory of `concrete`.
A full `.env` developer example can be found [in our repository](https://github.com/abstractoperators/concrete/blob/02cc58605f5b0b507434985ef2bd3ed7bb7e3881/.env.example).

Be sure to set the `ENV` variable as necessary:

```shell
ENV=DEV
ENV=PRODUCTION
```

#### [OpenAI](https://openai.com/index/openai-api/)

By default, operators rely on OpenAI ChatGPT 4 models to process queries. OpenAI requires a key to access its API:

```shell
OPENAI_API_KEY=<your api key here>
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
```shell
make run-postgres
```

When developing locally outside of docker, `DB_HOST` should be set to `localhost`. When developing inside docker, `DB_HOST` should be set to `host.docker.internal`.

### [Alembic](https://alembic.sqlalchemy.org/en/latest/)

We use Alembic to manage database migrations and schema creation for Postgres, our choice of database.

Migration scripts are tracked with git, and can be used to recreate database schemas at a particular point in time.
This can be especially useful for testing staging/prod migrations, because we can recreate their schemas locally.

#### Usage

SQLModel models are used to define migration scripts. To set up your system for autogenerated migrations:

1. Import all defined models in `migrations/env.py`, e.g. `from concrete.db.orm.models import *`.

2. Configure target metadata in `migrations/env.py`, e.g. `target_metadata = SQLModel.metadata`.

3. Import sqlmodel in `script.py.mako` (this is a template file for generating scripts), e.g. `from sqlmodel import SQLModel`.

4. Add database URL to `alembic.ini` file, e.g. `
sqlalchemy.url = postgresql+psycopg://local_user:local_password@localhost:5432/local_db`

To create a new migration script, run

```shell
alembic revision --autogenerate -m 'migration name'
```

This will generate a migration script taking the existing database schema to whatever schema is defined by the SQLModel models.

To apply the migration script, run `alembic upgrade head`.
This will alter the database schema.
You can also use relative migration numbers, e.g. `alembic upgrade +1`, or `alembic downgrade -2`.
Similarly, you can use `alembic downgrade partial_migration_number`.

> By default, `make run-postgres` applies all migrations to the database, initializing it with the latest schema. 

#### Manual Script Adjustments

It's sometimes necessary to manually adjust the autogenerated Alembic scripts.
Here are some common patterns and their solutions:

1. Adding a unique, non-nullable column `name` to a table `user` with existing rows:
```python
# add column as nullable first to avoid supplying nonunique default
op.add_column('user', sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))

# define view on table with relevant columns, e.g. primary key and desired column
old_user = sa.Table(
    'user',
    sa.MetaData(),
    sa.Column('id', sa.Uuid()),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=64)),
)
connection = op.get_bind()

# select relevant (aka all) existing rows for column insertion
results = connection.execute(
    sa.select(
        old_tools.c.id,
    )
).fetchall()

# update every existing record with a unique value in desired column
for i, (id,) in enumerate(results):
    new_name = id
    connection.execute(old_tools.update().where(old_tools.c.id == id).values(name=new_name))

# alter column to become non-nullable as was originally desired
op.alter_column('tool', 'name', nullable=False)
```

2. Renaming an existing column `a` to `b` in table `alphabet`:
```python
op.alter_column('operator', 'a', new_column_name='b')
```

For a deeper dive, please examine the [alembic operations reference](https://alembic.sqlalchemy.org/en/latest/ops.html).

## Web Dev

### Allow local subdomains

By default, auth will be enabled on webapps even when run locally.
This requires an auth service to be run, which is hosted at a sub-domain in staging/prod.
To mirror this setup locally add the following lines to the bottom of `/etc/hosts`:

```
127.0.0.1 abop.bot auth.abop.bot
```