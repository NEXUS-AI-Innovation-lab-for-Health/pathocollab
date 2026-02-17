from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.patient import Base as PatientBase
from app.models.case import Base as CaseBase
from dotenv import load_dotenv

load_dotenv()

config = context.config
config.set_main_option('sqlalchemy.url', os.getenv('DATABASE_URL', 'postgresql://pixtral_user:pixtral_pass@localhost:5432/cases_db'))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Combine all Base.metadata
target_metadata = PatientBase.metadata
for base in [CaseBase]:
    for table in base.metadata.tables.values():
        target_metadata._add_table(table.name, table.schema, table)

def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
