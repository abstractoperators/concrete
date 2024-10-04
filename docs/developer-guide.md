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
# Developer Guide

## Module Overview
This module provides a set of commands and configurations for managing the development, testing, and deployment of applications using Docker, Poetry, and AWS services. It includes commands for building, running, and deploying web applications, as well as managing dependencies and database migrations.

## Makefile Commands

### Setup
- **install**: Installs the project dependencies using Poetry.
  ```shell
  make install
  ```

### Run Tests
- **test**: Runs the test suite using pytest.
  ```shell
  make test
  ```

### Demo Commands
- **helloworld**: Creates a simple "Hello World" program.
  ```shell
  make helloworld
  ```
- **helloworld_celery**: Creates a simple "Hello World" program using Celery. Requires RabbitMQ and a Celery worker to be running.
  ```shell
  make helloworld_celery
  ```
- **simpleflask**: Provides the code for a Flask application with a single route rendering an HTML template.
  ```shell
  make simpleflask
  ```
- **deploysimpleflask**: Deploys a simple "Hello World" Flask application. Requires dind-builder to be running.
  ```shell
  make deploysimpleflask
  ```

### Build Commands
- **build-webapp-demo**: Builds the webapp-demo service using Docker Compose.
  ```shell
  make build-webapp-demo
  ```
- **build-webapp-homepage**: Builds the webapp-homepage service using Docker Compose.
  ```shell
  make build-webapp-homepage
  ```
- **build-docs**: Builds the documentation using MkDocs.
  ```shell
  make build-docs
  ```

### Run Commands
- **run-webapp-demo**: Stops and starts the webapp-demo service.
  ```shell
  make run-webapp-demo
  ```
- **run-webapp-homepage**: Stops and starts the webapp-homepage service.
  ```shell
  make run-webapp-homepage
  ```
- **run-postgres**: Starts the PostgreSQL service and applies all migrations to the database.
  ```shell
  make run-postgres
  ```

### AWS Commands
- **aws-ecr-login**: Logs into the AWS ECR registry.
  ```shell
  make aws-ecr-login
  ```
- **aws-ecr-push-homepage**: Builds and pushes the webapp-homepage image to AWS ECR.
  ```shell
  make aws-ecr-push-homepage
  ```

### Local Development without Docker
- **local-docs**: Builds and serves the documentation locally using MkDocs.
  ```shell
  make local-docs
  ```
- **local-api**: Runs the FastAPI server for the web application API locally.
  ```shell
  make local-api
  ```
- **local-webapp-main**: Runs the main web application server locally.
  ```shell
  make local-webapp-main
  ```

## Notes
- Ensure that your AWS credentials are configured for the default profile before running AWS commands.
- For webhook functionality, consider using a service like ngrok to expose your local server to the internet.# Module Documentation

## Module Overview
This module provides the core functionality for connecting to a database using SQLAlchemy and SQLModel, managing sessions, and initializing the database schema. It leverages environment variables for configuration and supports both SQLite and PostgreSQL databases.

## Environment Configuration
The module uses the `dotenv` package to load environment variables from a `.env` file. Ensure that the following variables are set in your `.env` file:

```.env
DB_DRIVER=sqlite  # or postgresql+psycopg
DB_USERNAME=your_username  # applicable for PostgreSQL
DB_PASSWORD=your_password  # applicable for PostgreSQL
DB_PORT=your_port  # applicable for PostgreSQL
DB_HOST=your_host  # applicable for PostgreSQL
DB_DATABASE=your_database_name  # applicable for PostgreSQL
```

## Database Connection
The database connection URL is constructed using the `sqlalchemy.URL` method. The default database is SQLite, but it can be configured to connect to a PostgreSQL database by setting the appropriate environment variables.

### Example of Database URL Construction
```python
SQLALCHEMY_DATABASE_URL = URL.create(
    drivername=os.environ.get("DB_DRIVER", "sqlite"),
    username=os.environ.get("DB_USERNAME", None),
    password=os.environ.get("DB_PASSWORD", None),
    host=os.environ.get("DB_HOST", None),
    port=db_port,
    database=os.environ.get("DB_DATABASE", "sql_app.db"),
)
```

## Session Management
The module provides a context manager for managing database sessions. This ensures that sessions are properly closed after use, preventing potential memory leaks or connection issues.

### Using the Session Context Manager
```python
with Session() as session:
    # Perform database operations here
```

## Database Initialization
For SQLite, the database schema is created automatically when the module is loaded. For PostgreSQL, the database schema should be managed using Alembic migrations as described in the existing documentation.

### Example of Schema Creation for SQLite
```python
if SQLALCHEMY_DATABASE_URL.drivername == "sqlite":
    SQLModel.metadata.create_all(engine)
```

## Logging
The module emits a log message indicating the database connection details using the `CLIClient` class. This can be useful for debugging and ensuring that the application is connecting to the correct database.

### Example of Logging Connection
```python
CLIClient.emit(f'Connecting to database at {SQLALCHEMY_DATABASE_URL}')
```

## Notes
- Ensure that the required environment variables are set before running the application.
- The context manager for sessions should be used to ensure proper resource management.# Module Documentation

## Module Overview
This module provides the core functionality for connecting to a database using SQLAlchemy and SQLModel, managing sessions, and initializing the database schema. It leverages environment variables for configuration and supports both SQLite and PostgreSQL databases.

## Environment Configuration
The module uses the `dotenv` package to load environment variables from a `.env` file. Ensure that the following variables are set in your `.env` file:

```.env
DB_DRIVER=sqlite  # or postgresql+psycopg
DB_USERNAME=your_username  # applicable for PostgreSQL
DB_PASSWORD=your_password  # applicable for PostgreSQL
DB_PORT=your_port  # applicable for PostgreSQL
DB_HOST=your_host  # applicable for PostgreSQL
DB_DATABASE=your_database_name  # applicable for PostgreSQL
```

## Database Connection
The database connection URL is constructed using the `sqlalchemy.URL` method. The default database is SQLite, but it can be configured to connect to a PostgreSQL database by setting the appropriate environment variables.

### Example of Database URL Construction
```python
SQLALCHEMY_DATABASE_URL = URL.create(
    drivername=os.environ.get("DB_DRIVER", "sqlite"),
    username=os.environ.get("DB_USERNAME", None),
    password=os.environ.get("DB_PASSWORD", None),
    host=os.environ.get("DB_HOST", None),
    port=db_port,
    database=os.environ.get("DB_DATABASE", "sql_app.db"),
)
```

## Session Management
The module provides a context manager for managing database sessions. This ensures that sessions are properly closed after use, preventing potential memory leaks or connection issues.

### Using the Session Context Manager
```python
with Session() as session:
    # Perform database operations here
```

## Database Initialization
For SQLite, the database schema is created automatically when the module is loaded. For PostgreSQL, the database schema should be managed using Alembic migrations as described in the existing documentation.

### Example of Schema Creation for SQLite
```python
if SQLALCHEMY_DATABASE_URL.drivername == "sqlite":
    SQLModel.metadata.create_all(engine)
```

## Logging
The module emits a log message indicating the database connection details using the `CLIClient` class. This can be useful for debugging and ensuring that the application is connecting to the correct database.

### Example of Logging Connection
```python
CLIClient.emit(f'Connecting to database at {SQLALCHEMY_DATABASE_URL}')
```

## Notes
- Ensure that the required environment variables are set before running the application.
- The context manager for sessions should be used to ensure proper resource management.# Module Documentation

## Module Overview
This module provides the core functionality for managing database migrations and schema definitions using Alembic in conjunction with SQLAlchemy and SQLModel. It defines the database schema for various entities and their relationships, ensuring that the application can effectively manage data persistence and integrity.

## Migration Scripts
Migration scripts are generated using Alembic and are essential for tracking changes to the database schema over time. Each migration script contains an `upgrade` function to apply changes and a `downgrade` function to revert them.

### Example Migration Script Structure
```python
"""
Revision ID: ad1893077e4f
Revises: 
Create Date: 2024-10-04 10:58:17.584346
"""

from typing import Sequence, Union
import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ad1893077e4f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'node',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('parent_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['node.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Additional table creation commands...


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('operatortoollink')
    op.drop_table('client')
    # Additional table drop commands...
```  

## Database Schema Definition
The module defines several tables that represent the core entities of the application. Each table is created with specific columns and constraints to maintain data integrity.

### Defined Tables
- **node**: Represents a hierarchical structure with potential parent-child relationships.
- **orchestrator**: Contains metadata about orchestrators, including type and ownership details.
- **reponode**: Stores information about repositories, including organization and repository names, along with their relationships to other nodes.
- **tool**: Represents tools that can be linked to operators.
- **message**: Captures messages related to orchestrators, including their status and content.
- **operator**: Defines operators with instructions and their associated orchestrators.
- **client**: Represents clients that interact with operators and orchestrators.
- **operatortoollink**: A linking table that associates operators with tools.

### Example of Table Creation
```python
op.create_table(
    'orchestrator',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('type_name', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
    sa.Column('owner', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
    sa.Column('foo', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
    sa.PrimaryKeyConstraint('id'),
)
```

## Indexing
To improve query performance, several indexes are created on the `reponode` table, allowing for efficient lookups based on organization and repository names.

### Example of Index Creation
```python
op.create_index('ix_org_repo', 'reponode', ['org', 'repo'], unique=False)
```

## Notes
- Ensure that migration scripts are properly versioned and tracked in your version control system.
- Review and adjust auto-generated migration commands as necessary to fit your application's requirements.