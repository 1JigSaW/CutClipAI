import json
import os
import tempfile
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.billing.pricing import PricingService
from app.services.billing.wallet import WalletService
from app.services.storage.s3 import S3Service
from app.services.video.pipeline import VideoPipeline
from app.utils.video.files import delete_temp_files


@celery_app.task(
    name="process_video_task",
)
def process_video_task(
    s3_key: str,
    user_id: int,
) -> dict:
    """
    Celery task to process video through full pipeline.

    Args:
        s3_key: S3 key of uploaded video file
        user_id: Telegram user ID

    Returns:
        Dictionary with clip S3 keys or "no_coins" status
    """
    pipeline = VideoPipeline()
    wallet_service = WalletService()
    pricing_service = PricingService()
    s3_service = S3Service()

    temp_file_path = None
    temp_files_to_cleanup = []

    try:
        suffix = Path(s3_key).suffix
        temp_fd, temp_file_path = tempfile.mkstemp(
            suffix=suffix,
            dir=settings.TEMP_DIR,
        )
        os.close(temp_fd)

        s3_service.download_file(
            s3_key=s3_key,
            local_path=temp_file_path,
        )

        temp_files_to_cleanup.append(temp_file_path)

        clip_paths = pipeline.process(file_path=temp_file_path)

        clips_count = len(clip_paths)
        cost = pricing_service.calculate_cost(clips_count=clips_count)

        charged = wallet_service.charge_coins(
            user_id=user_id,
            amount=cost,
        )

        if not charged:
            return {
                "status": "no_coins",
                "message": "Insufficient balance",
                "clips_count": clips_count,
            }

        clip_s3_keys = []
        for clip_path in clip_paths:
            clip_s3_key = s3_service.upload_file(
                file_path=clip_path,
                prefix=f"videos/output/{user_id}",
            )
            clip_s3_keys.append(clip_s3_key)
            temp_files_to_cleanup.append(clip_path)

        return {
            "status": "success",
            "clips_count": clips_count,
            "clip_s3_keys": clip_s3_keys,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }
    finally:
        if temp_files_to_cleanup:
            delete_temp_files(file_paths=temp_files_to_cleanup)

