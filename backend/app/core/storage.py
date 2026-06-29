from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
import io
import uuid
from datetime import timedelta
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class StorageService:
    """MinIO/S3 storage service for file management."""
    
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure the bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket: {e}")
    
    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        content_type: str,
        folder: str = "uploads"
    ) -> str:
        """Upload a file to storage."""
        # Generate unique path
        file_id = str(uuid.uuid4())
        extension = file_name.split(".")[-1] if "." in file_name else ""
        object_name = f"{folder}/{file_id}.{extension}" if extension else f"{folder}/{file_id}"
        
        try:
            # Get file size
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)
            
            self.client.put_object(
                self.bucket,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
            )
            
            logger.info(f"Uploaded file: {object_name}")
            return object_name
            
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes to storage."""
        try:
            data_stream = io.BytesIO(data)
            self.client.put_object(
                self.bucket,
                object_name,
                data_stream,
                len(data),
                content_type=content_type,
            )
            logger.info(f"Uploaded bytes: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading bytes: {e}")
            raise
    
    def download_file(self, object_name: str) -> bytes:
        """Download a file from storage."""
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error downloading file: {e}")
            raise
    
    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Get a presigned URL for file download."""
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=expires,
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def delete_file(self, object_name: str) -> bool:
        """Delete a file from storage."""
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Deleted file: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> list:
        """List files with optional prefix."""
        try:
            objects = self.client.list_objects(
                self.bucket,
                prefix=prefix,
                recursive=True,
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def get_file_info(self, object_name: str) -> Optional[dict]:
        """Get file metadata."""
        try:
            stat = self.client.stat_object(self.bucket, object_name)
            return {
                "name": object_name,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
            }
        except S3Error:
            return None


# Singleton instance
storage_service = StorageService()

