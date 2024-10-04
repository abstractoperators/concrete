from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from concrete.db.orm.models import *  # noqa: F401, F403

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
# Module Documentation for Migration Management

This module is responsible for managing database migrations using Alembic, a lightweight database migration tool for use with SQLAlchemy. It provides functionality to run migrations in both offline and online modes, allowing for flexibility depending on the environment.

## Functions

### `run_migrations_offline() -> None`

Run migrations in 'offline' mode.

This function configures the migration context with a database URL instead of an Engine. This allows migrations to be executed without requiring a live database connection. The function emits SQL commands to the script output, which can be useful for generating migration scripts.

#### Steps:
1. Retrieve the database URL from the configuration.
2. Configure the context with the URL and target metadata.
3. Begin a transaction and run the migrations.

### `run_migrations_online() -> None`

Run migrations in 'online' mode.

This function creates a database Engine and establishes a connection to the database. It is used when a live database connection is available and necessary for executing migrations.

#### Steps:
1. Create an Engine using the configuration settings.
2. Connect to the database using the created Engine.
3. Configure the context with the connection and target metadata.
4. Begin a transaction and run the migrations.

## Configuration

The module uses an Alembic Config object to access settings defined in the .ini configuration file. This includes the database URL and logging configuration. The `target_metadata` is set to the metadata of the SQLModel, which is necessary for autogenerating migration scripts based on the defined models.

## Execution Flow

The module checks if the context is in offline mode. If it is, it calls `run_migrations_offline()`. Otherwise, it calls `run_migrations_online()`. This allows the module to adapt to the environment it is running in, ensuring that migrations can be executed appropriately.