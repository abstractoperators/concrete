import os
from logging.config import fileConfig

import dotenv
from alembic import context
from sqlalchemy import URL, engine_from_config, pool
from sqlmodel import SQLModel

dotenv.load_dotenv(override=True)


from concrete.db.orm.models import *  # noqa: F401, F403, E402

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
DB_PORT = os.environ.get("DB_PORT")
db_port = int(DB_PORT) if DB_PORT else None
SQLALCHEMY_DATABASE_URL = URL.create(
    drivername=os.environ.get("DB_DRIVER", "sqlite"),
    username=os.environ.get("DB_USERNAME", None),
    password=os.environ.get("DB_PASSWORD", None),
    host=os.environ.get("DB_HOST", None),
    port=db_port,
    database=os.environ.get("DB_DATABASE", "sql_app.db"),
)

config.set_main_option('sqlalchemy.url', str(SQLALCHEMY_DATABASE_URL).replace('***', os.environ.get('DB_PASSWORD', "")))


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
