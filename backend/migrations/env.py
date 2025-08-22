import os
from pathlib import Path
from alembic import context
from sqlalchemy import create_engine, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Database URL constructed from DB_PATH env var, defaulting to the runtime path
DB_PATH = Path(os.getenv("DB_PATH", "/app/data/whispr.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

# No SQLAlchemy models to autogenerate from (yet)
target_metadata = None

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
