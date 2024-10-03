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
# Developer Guide

## Makefile Commands

The following commands are defined in the Makefile to facilitate various tasks related to the project. Each command can be executed using `make <command>`.

### Setup

#### Install Dependencies

```shell
make install
```
This command installs all the dependencies specified in the `pyproject.toml` file using Poetry.

### Run Tests

```shell
make test
```
This command runs the test suite using pytest.

### Demo Commands

#### Hello World

```shell
make helloworld
```
This command orchestrates the creation of a simple hello world program.

#### Hello World with Celery

```shell
make helloworld_celery
```
This command requires RabbitMQ and a Celery worker to be running. It orchestrates the creation of a simple hello world program with Celery support after a brief sleep period.

#### Simple Flask Application

```shell
make simpleflask
```
This command orchestrates the generation of a Flask application with a single route that renders the HTML template 'index.html', containing a header tag with the text 'Hello, World!'.

### Deployment Commands

#### Deploy Simple Flask Application

```shell
make deploysimpleflask
```
This command orchestrates the creation and deployment of a simple hello world Flask application. Note that it requires the dind-builder to be running and resources created in AWS must be manually deleted.

### Build Commands

#### Build Web Application Demo

```shell
make build-webapp-demo
```
This command builds the webapp-demo service using Docker Compose.

#### Build Web Application Homepage

```shell
make build-webapp-homepage
```
This command builds the webapp-homepage service using Docker Compose.

#### Build DIND Builder

```shell
make build-dind-builder
```
This command builds the dind-builder service using Docker Compose.

#### Build Daemons

```shell
make build-daemons
```
This command builds the daemons service using Docker Compose.

#### Build Documentation

```shell
make build-docs
```
This command builds the documentation using MkDocs and Docker Compose.

#### Build Main Application

```shell
make build-main
```
This command builds the main application using Docker Compose.

### Run Commands

#### Run Web Application Demo

```shell
make run-webapp-demo
```
This command stops any running instance of the webapp-demo service and starts it in detached mode.

#### Run Web Application Homepage

```shell
make run-webapp-homepage
```
This command stops any running instance of the webapp-homepage service and starts it in detached mode.

#### Run DIND Builder

```shell
make run-dind-builder
```
This command stops any running instance of the dind-builder service and starts it in detached mode.

#### Run Daemons

```shell
make run-daemons
```
This command stops any running instance of the daemons service and starts it in detached mode.

#### Run Documentation

```shell
make run-docs
```
This command stops any running instance of the docs service and starts it in detached mode.

#### Run Main Application

```shell
make run-main
```
This command builds and runs the main application in detached mode.

#### Run PostgreSQL

```shell
make run-postgres
```
This command stops any running instance of PostgreSQL and starts it in detached mode.

### AWS Commands

#### AWS ECR Login

```shell
make aws-ecr-login
```
This command logs into the AWS Elastic Container Registry (ECR) using the default profile and credentials.

#### AWS ECR Push Commands

These commands build the Docker images and push them to the AWS ECR:

- **Push Homepage**: `make aws-ecr-push-homepage`
- **Push Demo**: `make aws-ecr-push-demo`
- **Push Docs**: `make aws-ecr-push-docs`
- **Push Daemons**: `make aws-ecr-push-daemons`
- **Push Main**: `make aws-ecr-push-main`

#### Deploy Daemon to AWS Staging

```shell
make deploy-daemon-to-aws-staging
```
This command deploys the daemon service to AWS staging using the specified image URI and container settings.

### Local Development without Docker

#### RabbitMQ

```shell
make rabbitmq
```
This command runs a RabbitMQ container in detached mode.

#### Celery

```shell
make celery
```
This command starts a Celery worker after ensuring RabbitMQ is running, and logs output to a specified log file.

#### Local Documentation

```shell
make local-docs
```
This command builds and serves the documentation locally using MkDocs.

#### Local API

```shell
make local-api
```
This command runs the FastAPI application for the webapp API on port 8001.

#### Local Web Application Main

```shell
make local-webapp-main
```
This command runs the main FastAPI application locally.

#### Local Daemons

```shell
make local-daemons
```
This command runs the daemons locally, ensuring environment variables are sourced from the `.env.daemons` file.# Database Module Documentation

## Overview
This module is responsible for managing the database connection and session handling using SQLAlchemy and SQLModel. It provides a context manager for session management and establishes a connection to the database defined in the environment variables.

## Environment Configuration
The database connection URL is loaded from the environment variable `SQLALCHEMY_DATABASE_URL`. If this variable is not set, it defaults to using a SQLite database located at `sql_app.db`.

### Loading Environment Variables
To load environment variables from a `.env` file, the `dotenv` package is used. Ensure that the `.env` file is present in the project root with the necessary configuration.

```python
from dotenv import load_dotenv
load_dotenv()
```

## Database Engine
The database engine is created using SQLModel's `create_engine` function. It supports both SQLite and other databases, with specific connection arguments for SQLite to allow multi-threaded access.

```python
from sqlmodel import create_engine

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
```

## Session Management
The `SessionLocal` is defined using SQLAlchemy's `sessionmaker`, which is configured to not autocommit or autoflush by default. This ensures that transactions are handled explicitly.

```python
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Context Manager for Sessions
A context manager named `Session` is provided to facilitate session handling. It ensures that sessions are properly closed after use, preventing potential memory leaks or database locks.

```python
from contextlib import contextmanager

@contextmanager
def Session():
    session = SQLModelSession(engine)
    try:
        yield session
    finally:
        session.close()
```

## Usage Example
To use the session context manager, you can wrap your database operations within the `Session` context. This ensures that the session is properly managed and closed after the operations are complete.

```python
with Session() as session:
    # Perform database operations here
    pass
```

## Logging
The module uses the `CLIClient` to emit a log message when connecting to the database, providing visibility into the database connection process.

```python
from concrete.clients import CLIClient
CLIClient.emit(f'Connecting to database at {SQLALCHEMY_DATABASE_URL}')
```