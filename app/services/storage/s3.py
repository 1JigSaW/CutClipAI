import os
import uuid
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class S3Service:
    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region: str = None,
        bucket_name: str = None,
        endpoint_url: Optional[str] = None,
    ):
        self.access_key_id = access_key_id or settings.AWS_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.AWS_SECRET_ACCESS_KEY
        self.region = region or settings.AWS_REGION
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL

        session = boto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )

        s3_client_kwargs = {}
        if self.endpoint_url:
            s3_client_kwargs["endpoint_url"] = self.endpoint_url

        self.s3_client = session.client(
            service_name="s3",
            **s3_client_kwargs,
        )

        max_concurrency = settings.S3_MAX_CONCURRENCY
        logger.info(
            f"S3 TransferConfig initialized | max_concurrency={max_concurrency}",
        )
        
        self.transfer_config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=max_concurrency,
            multipart_chunksize=1024 * 25,
            use_threads=True,
        )

    def upload_file(
        self,
        file_path: str,
        s3_key: Optional[str] = None,
        prefix: str = "uploads",
    ) -> str:
        """
        Upload file to S3.

        Args:
            file_path: Local file path to upload
            s3_key: S3 key (path) for the file. If not provided, will be generated
            prefix: Prefix for S3 key generation

        Returns:
            S3 key of uploaded file
        """
        if s3_key is None:
            file_extension = Path(file_path).suffix
            unique_id = str(uuid.uuid4())
            s3_key = f"{prefix}/{unique_id}{file_extension}"

        try:
            self.s3_client.upload_file(
                Filename=file_path,
                Bucket=self.bucket_name,
                Key=s3_key,
                Config=self.transfer_config,
            )
            return s3_key
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {str(e)}")

    def download_file(
        self,
        s3_key: str,
        local_path: str,
    ) -> str:
        """
        Download file from S3 to local path.

        Args:
            s3_key: S3 key (path) of the file
            local_path: Local path where to save the file

        Returns:
            Local path to downloaded file
        """
        local_file_path = Path(local_path)
        local_file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=s3_key,
                Filename=str(local_path),
                Config=self.transfer_config,
            )
            return str(local_path)
        except ClientError as e:
            raise Exception(f"Failed to download file from S3: {str(e)}")

    def delete_file(
        self,
        s3_key: str,
    ) -> None:
        """
        Delete file from S3.

        Args:
            s3_key: S3 key (path) of the file to delete
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
        except ClientError as e:
            raise Exception(f"Failed to delete file from S3: {str(e)}")

    def get_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
    ) -> str:
        """
        Generate presigned URL for file access.

        Args:
            s3_key: S3 key (path) of the file
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                },
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    def file_exists(
        self,
        s3_key: str,
    ) -> bool:
        """
        Check if file exists in S3.

        Args:
            s3_key: S3 key (path) of the file

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            return True
        except ClientError:
            return False

