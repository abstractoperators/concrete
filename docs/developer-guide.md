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
## Docker Setup

This module utilizes Docker to create a consistent environment for building and running the application. Below are the steps and explanations for the Docker setup used in this project.

### Dockerfile Overview

The Dockerfile is divided into two main stages: the builder stage and the runtime stage. This multi-stage build helps to keep the final image lightweight by separating the build dependencies from the runtime environment.

#### Builder Stage

```dockerfile
FROM python:3.11.10-bookworm AS builder

RUN pip install poetry==1.8

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --only main,webapp --no-root
```

- **Base Image**: The builder stage starts from the `python:3.11.10-bookworm` image, which includes Python 3.11.10.
- **Poetry Installation**: It installs Poetry version 1.8 for dependency management.
- **Environment Variables**: Several environment variables are set to configure Poetry's behavior, including disabling interaction and enabling virtual environments within the project directory.
- **Working Directory**: The working directory is set to `/app`.
- **Dependency Installation**: The `pyproject.toml` and `poetry.lock` files are copied, and dependencies are installed using Poetry, with caching enabled for efficiency.

#### Runtime Stage

```dockerfile
FROM python:3.11.10-slim-bullseye AS runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 

WORKDIR /app
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY concrete ./concrete
COPY webapp ./webapp
COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN pip install --no-deps .

RUN chmod +x ./webapp/demo/scripts/start.sh
EXPOSE 80
CMD ["./webapp/demo/scripts/start.sh"]
```

- **Base Image**: The runtime stage uses the `python:3.11.10-slim-bullseye` image, which is a smaller version of the Python image.
- **Environment Variables**: Similar environment variables are set to ensure the virtual environment is used correctly.
- **Working Directory**: The working directory is again set to `/app`.
- **Copying Artifacts**: The virtual environment created in the builder stage is copied over to the runtime stage, along with the application code and configuration files.
- **Final Installation**: The application is installed without dependencies since they are already included in the virtual environment.
- **Script Permissions**: The startup script is made executable.
- **Port Exposure**: Port 80 is exposed for web traffic.
- **Startup Command**: The container is configured to run the startup script when it is launched.

### Building and Running the Docker Container

To build and run the Docker container, use the following commands:

```shell
# Build the Docker image
docker build -t my_app_image .

# Run the Docker container
docker run -p 80:80 my_app_image
```

Replace `my_app_image` with your desired image name. The application will be accessible on port 80 of your localhost.