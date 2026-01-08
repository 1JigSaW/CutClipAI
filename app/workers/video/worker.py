import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from celery import group

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logger import get_logger, log_error
from app.models.transaction.transaction import TransactionType
from app.services.billing.pricing import PricingService
from app.services.billing.wallet import WalletService
from app.services.storage.s3 import S3Service
from app.services.video.pipeline import VideoPipeline
from app.utils.billing.validators import check_balance_for_video_processing
from app.utils.video.files import create_temp_dir, create_temp_file, delete_temp_files

logger = get_logger(__name__)


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
    logger.info(
        f"Starting video processing task | user_id={user_id} | s3_key={s3_key}",
    )

    wallet_service = WalletService()
    pricing_service = PricingService()
    s3_service = S3Service()

    max_clips = settings.MAX_CLIPS_COUNT
    reserved_cost = max_clips * settings.COINS_PER_CLIP

    temp_file_path = None
    temp_files_to_cleanup = []

    try:
        suffix = Path(s3_key).suffix
        temp_file_path = create_temp_file(
            suffix=suffix,
            prefix="video_",
        )

        logger.info(
            f"Downloading video from S3 | user_id={user_id} | s3_key={s3_key} | "
            f"temp_path={temp_file_path}",
        )

        download_start = time.time()
        s3_service.download_file(
            s3_key=s3_key,
            local_path=temp_file_path,
        )
        download_time = time.time() - download_start

        file_size = os.path.getsize(temp_file_path)
        file_size_mb = file_size / (1024 * 1024)
        download_speed = file_size_mb / download_time if download_time > 0 else 0
        
        logger.info(
            f"Video downloaded from S3 | user_id={user_id} | "
            f"size={file_size_mb:.2f}MB | time={download_time:.1f}s | "
            f"speed={download_speed:.2f}MB/s",
        )

        temp_files_to_cleanup.append(temp_file_path)

        logger.info(
            f"Starting video pipeline processing | user_id={user_id} | "
            f"file_path={temp_file_path} | file_size={file_size_mb:.2f}MB",
        )

        import gc
        gc.collect()

        pipeline_start = time.time()
        pipeline = VideoPipeline()
        clip_paths = pipeline.process_optimized(
            file_path=temp_file_path,
            user_id=user_id,
        )
        pipeline_time = time.time() - pipeline_start

        logger.info(
            f"Video pipeline completed | user_id={user_id} | "
            f"clips_count={len(clip_paths)} | pipeline_time={pipeline_time:.1f}s",
        )

        clips_count = len(clip_paths)
        actual_cost = pricing_service.calculate_cost(clips_count=clips_count)

        # Calculate refund: reserved (max) - actual
        refund_amount = reserved_cost - actual_cost
        
        if refund_amount > 0:
            logger.info(
                f"Refunding unused coins | user_id={user_id} | "
                f"reserved={reserved_cost} | actual={actual_cost} | refund={refund_amount}",
            )
            wallet_service.add_coins(
                user_id=user_id,
                amount=refund_amount,
                description=f"Refund for video task: {s3_key}",
                transaction_type=TransactionType.REFUND,
            )

        logger.info(
            f"Video processing completed | user_id={user_id} | "
            f"clips_count={clips_count} | cost={actual_cost} coins",
        )

        clip_s3_keys = []
        for idx, clip_path in enumerate(clip_paths, 1):
            logger.debug(
                f"Uploading clip {idx}/{clips_count} to S3 | user_id={user_id} | "
                f"clip_path={clip_path}",
            )

            clip_s3_key = s3_service.upload_file(
                file_path=clip_path,
                prefix=f"videos/output/{user_id}",
            )
            clip_s3_keys.append(clip_s3_key)
            temp_files_to_cleanup.append(clip_path)

            logger.debug(
                f"Clip {idx}/{clips_count} uploaded to S3 | user_id={user_id} | "
                f"s3_key={clip_s3_key}",
            )

        logger.info(
            f"Video processing task completed successfully | user_id={user_id} | "
            f"clips_count={clips_count} | clip_s3_keys={len(clip_s3_keys)}",
        )

        return {
            "status": "success",
            "clips_count": clips_count,
            "clip_s3_keys": clip_s3_keys,
        }

    except Exception as e:
        log_error(
            logger=logger,
            message=f"Video processing task failed | user_id={user_id} | Refunding reserved coins",
            error=e,
            context={"s3_key": s3_key},
        )
        
        # Refund everything on error
        wallet_service.add_coins(
            user_id=user_id,
            amount=reserved_cost,
            description=f"Error refund for video task: {s3_key}",
            transaction_type=TransactionType.REFUND,
        )
        
        return {
            "status": "error",
            "message": str(e),
        }
    finally:
        if temp_files_to_cleanup:
            logger.debug(
                f"Cleaning up temp files | user_id={user_id} | "
                f"files_count={len(temp_files_to_cleanup)}",
            )
            delete_temp_files(file_paths=temp_files_to_cleanup)

