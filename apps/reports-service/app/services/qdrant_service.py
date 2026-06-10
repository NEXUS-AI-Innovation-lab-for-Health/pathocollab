from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os
import logging
import hashlib

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(self):
        self.enabled = os.getenv("QDRANT_ENABLED", "true").lower() == "true"
        self.url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "pixtral_reports")
        self.timeout = float(os.getenv("QDRANT_TIMEOUT", "3"))
        self._client = None
        self._collection_checked = False

    @property
    def client(self):
        if not self.enabled:
            raise RuntimeError("Qdrant is disabled")

        if self._client is None:
            self._client = QdrantClient(url=self.url, timeout=self.timeout)

        return self._client

    def is_available(self) -> bool:
        if not self.enabled:
            return False

        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def _ensure_collection_exists(self):
        if not self.enabled:
            return

        if self._collection_checked:
            return

        collections = self.client.get_collections().collections

        if not any(col.name == self.collection_name for col in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            logger.info("Collection %s created", self.collection_name)

        self._collection_checked = True

    def store_report_embedding(self, report_id: str, report_text: str, embedding: list[float]):
        if not self.is_available():
            logger.warning("Qdrant unavailable, skipping embedding storage")
            return

        try:
            self._ensure_collection_exists()
            point = PointStruct(
                id=self._generate_id(report_id),
                vector=embedding,
                payload={
                    "report_id": report_id,
                    "text": report_text[:1000],
                },
            )
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )
        except Exception:
            logger.exception("Error storing embedding in Qdrant")

    def search_similar_reports(self, query_embedding: list[float], limit: int = 5) -> list:
        if not self.is_available():
            return []

        try:
            self._ensure_collection_exists()
            return self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
            )
        except Exception:
            logger.exception("Error searching similar reports in Qdrant")
            return []

    @staticmethod
    def _generate_id(report_id: str) -> int:
        return int(hashlib.sha256(report_id.encode()).hexdigest()[:16], 16) % (2**63)