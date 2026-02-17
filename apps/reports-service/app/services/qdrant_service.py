from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os
from dotenv import load_dotenv
import logging
import hashlib

load_dotenv()
logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "pixtral_reports")
        self.client = QdrantClient(url=self.url)
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Créer la collection si elle n'existe pas"""
        try:
            collections = self.client.get_collections().collections
            if not any(col.name == self.collection_name for col in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
                )
                logger.info(f"Collection {self.collection_name} created")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
    
    def store_report_embedding(self, report_id: str, report_text: str, embedding: list[float]):
        """Stocker un rapport et son embedding"""
        try:
            point = PointStruct(
                id=self._generate_id(report_id),
                vector=embedding,
                payload={
                    "report_id": report_id,
                    "text": report_text[:1000]  # Limite pour payload
                }
            )
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            logger.info(f"Report embedding stored: {report_id}")
        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
    
    def search_similar_reports(self, query_embedding: list[float], limit: int = 5) -> list:
        """Rechercher des rapports similaires"""
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Error searching similar reports: {e}")
            return []
    
    @staticmethod
    def _generate_id(report_id: str) -> int:
        """Générer un ID numérique pour Qdrant"""
        return int(hashlib.sha256(report_id.encode()).hexdigest()[:16], 16) % (2**63)
