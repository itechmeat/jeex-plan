from logging.config import fileConfig
import sys
import os
import asyncio

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import models without app context
from alembic_models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

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
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
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
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=url,
    )

    # Check if this is an async engine
    if isinstance(connectable, AsyncEngine):
        # Check if there's already a running event loop
        try:
            asyncio.get_running_loop()
            # If we get here, there's already a running loop, so schedule the coroutine
            asyncio.create_task(run_async_migrations(connectable))
        except RuntimeError:
            # No running loop, so we can use asyncio.run
            asyncio.run(run_async_migrations(connectable))
    else:
        with connectable.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()


async def run_async_migrations(connectable):
    """Run migrations in async mode."""
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


def do_run_migrations(connection):
    """Helper function to run migrations synchronously within async context."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
