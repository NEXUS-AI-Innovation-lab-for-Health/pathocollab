from minio import Minio
from minio.error import S3Error
import os
from dotenv import load_dotenv
import logging
import mimetypes

load_dotenv()
logger = logging.getLogger(__name__)

class MinioService:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME") or os.getenv("MINIO_BUCKET_WSI") or "pixtral-wsi-images"
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        self.lazy_init = os.getenv("MINIO_LAZY_INIT", "true").lower() == "true"

        if not self.lazy_init:
            self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket {self.bucket_name} created")
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")

    def upload_file(self, file_data: bytes, object_name: str, content_type: str):
        from io import BytesIO
        try:
            self._ensure_bucket_exists()

            self.client.put_object(
                self.bucket_name,
                object_name,
                BytesIO(file_data),
                length=len(file_data),
                content_type=content_type,
            )
            logger.info(f"File uploaded: {object_name}")
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise

    def upload_path(self, file_path: str, object_name: str, content_type: str | None = None):
        try:
            self._ensure_bucket_exists()
            
            guessed_type, _ = mimetypes.guess_type(file_path)
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path,
                content_type=content_type or guessed_type or "application/octet-stream",
            )
            logger.info(f"File uploaded from path: {object_name}")
        except S3Error as e:
            logger.error(f"Error uploading file from path: {e}")
            raise

    def get_presigned_url(self, object_name: str, expiry_hours: int = 24) -> str:
        from datetime import timedelta
        try:
            return self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(hours=expiry_hours),
            )
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            return ""

    def get_object(self, object_name: str):
        try:
            return self.client.get_object(self.bucket_name, object_name)
        except S3Error as e:
            logger.error(f"Error getting object: {e}")
            return None

    def get_object_bytes(self, object_name: str) -> bytes | None:
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

    def object_exists(self, object_name: str) -> bool:
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def list_prefixes(self, prefix: str):
        it = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=False)
        prefixes = set()
        for obj in it:
            name = obj.object_name
            if name.endswith("/"):
                prefixes.add(name)
            else:
                if prefix in name:
                    rest = name[len(prefix):]
                    if "/" in rest:
                        prefixes.add(prefix + rest.split("/")[0] + "/")
        return sorted(prefixes)

    def list_objects(self, prefix: str):
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