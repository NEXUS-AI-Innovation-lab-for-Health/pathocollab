from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Modèle temporaire pour la migration
class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    images = relationship("Image", back_populates="case", cascade="all, delete-orphan")

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))  # Nom de fichier unique
    original_filename = Column(String(255))  # Nom original du fichier
    object_name = Column(String(500))  # Chemin dans MinIO
    content_type = Column(String(100))  # MIME type
    size = Column(Integer)  # Taille en octets
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=True)
    url = Column(String(500))  # URL publique
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    case = relationship("Case", back_populates="images")