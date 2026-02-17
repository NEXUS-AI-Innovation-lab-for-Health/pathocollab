from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Configuration de la base de données pour s'intégrer avec l'infra existante
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://pixtral_user:pixtral_pass@localhost:5432/images_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
