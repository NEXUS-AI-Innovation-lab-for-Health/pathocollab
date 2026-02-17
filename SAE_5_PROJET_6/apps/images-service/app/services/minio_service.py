from minio import Minio
from minio.error import S3Error
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class MinioService:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "pixtral-wsi-images")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Créer le bucket s'il n'existe pas
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket {self.bucket_name} created")
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")
    
    def object_exists(self, object_name: str) -> bool:
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            logger.warning(f"stat_object failed for {object_name}: {e}")
            return False

    def upload_file(self, file_data: bytes, object_name: str, content_type: str):
        """Upload un fichier vers MinIO"""
        from io import BytesIO
        try:
            self.client.put_object(
                self.bucket_name,
                object_name,
                BytesIO(file_data),
                length=len(file_data),
                content_type=content_type
            )
            logger.info(f"File uploaded: {object_name}")
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def get_presigned_url(self, object_name: str, expiry_hours: int = 24) -> str:
        """Générer une URL présignée"""
        from datetime import timedelta
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(hours=expiry_hours)
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            return ""

    def get_object(self, object_name: str):
        """Récupérer un objet depuis MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return response
        except S3Error as e:
            logger.error(f"Error getting object: {e}")
            return None
        
    def list_prefixes(self, prefix: str):
        """
        Retourne la liste des sous-prefixes immédiats (simule des 'dossiers').
        Exemple: prefix='cases/' => ['cases/caseA/', 'cases/caseB/']
        """
        try:
            # delimiter='/' permet d'obtenir des "répertoires"
            it = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=False)
            prefixes = set()
            for obj in it:
                # MinIO Python renvoie parfois obj.object_name sur les objects et les "directories"
                # On récupère la partie prefix jusqu'au prochain /
                name = obj.object_name
                if name.endswith("/"):
                    prefixes.add(name)
                else:
                    # si jamais ça ne remonte pas en dir, on calcule
                    if prefix in name:
                        rest = name[len(prefix):]
                        if "/" in rest:
                            prefixes.add(prefix + rest.split("/")[0] + "/")
            return sorted(prefixes)
        except S3Error as e:
            raise

    def list_objects(self, prefix: str):
        """Liste les objets (fichiers) sous un prefix."""
        try:
            it = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            out = []
            for obj in it:
                if obj.object_name.endswith("/"):
                    continue
                out.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag,
                })
            return out
        except S3Error as e:
            raise

    def get_object_bytes(self, object_name: str) -> bytes:
        """Retourne le contenu d'un objet en bytes."""
        try:
            resp = self.client.get_object(self.bucket_name, object_name)
            try:
                return resp.read()
            finally:
                resp.close()
                resp.release_conn()
        except S3Error as e:
            logger.error(f"Error getting object {object_name}: {e}")
            return None