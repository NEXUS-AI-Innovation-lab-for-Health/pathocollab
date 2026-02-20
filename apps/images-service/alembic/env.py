from logging.config import fileConfig
from sqlalchemy import create_engine, engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Ajoutez le répertoire parent au chemin Python
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Importez votre modèle SQLAlchemy
from models import Base

# Charger la configuration d'Alembic
config = context.config

# Configurer la journalisation
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Configuration de la cible des métadonnées
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Exécute les migrations en mode 'offline'."""
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
    """Exécute les migrations en mode 'online'."""
    db_url = os.getenv("ALEMBIC_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()