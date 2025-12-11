import os
import tempfile

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from celery.result import AsyncResult

from fastapi import HTTPException

from app.core.celery_app import celery_app
from app.core.logger import get_logger, log_error
from app.services.storage.s3 import S3Service
from app.utils.billing.validators import check_balance_for_video_processing
from app.utils.video.files import temp_file_context
from app.workers.video.worker import process_video_task

logger = get_logger(__name__)

router = APIRouter(
    prefix="/video",
    tags=["video"],
)


class ProcessVideoResponse(BaseModel):
    task_id: str


class VideoStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None


@router.post(
    path="/process",
    response_model=ProcessVideoResponse,
)
async def process_video(
    user_id: int = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload video and start processing task.

    Args:
        user_id: Telegram user ID
        file: Video file to process

    Returns:
        Task ID for status checking
    """
    if not file:
        logger.error(f"Received request without file | user_id={user_id}")
        raise HTTPException(status_code=400, detail="File is required")

    has_sufficient_balance, balance, required_cost = check_balance_for_video_processing(
        user_id=user_id,
    )
    
    if not has_sufficient_balance:
        logger.warning(
            f"Insufficient balance before processing | user_id={user_id} | "
            f"balance={balance} | required={required_cost}",
        )
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient balance. Required: {required_cost} coins, have: {balance} coins",
        )

    file_name = file.filename or "video.mp4"
    suffix = os.path.splitext(file_name)[1]

    logger.info(
        f"Received video upload request | user_id={user_id} | filename={file_name} | "
        f"balance={balance} | required_cost={required_cost}",
    )

    task = None
    try:
        with temp_file_context(
            suffix=suffix,
            prefix="upload_",
        ) as temp_path:
            file_size = 0
            chunk_size = 1024 * 64
            
            with open(temp_path, "wb") as f:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    file_size += len(chunk)

            logger.info(
                f"Video file saved to temp | user_id={user_id} | "
                f"size={file_size} bytes | path={temp_path}",
            )

            s3_service = S3Service()
            s3_key = s3_service.upload_file(
                file_path=temp_path,
                prefix=f"videos/input/{user_id}",
            )

            logger.info(
                f"Video uploaded to S3 | user_id={user_id} | s3_key={s3_key}",
            )

            task = process_video_task.delay(
                s3_key=s3_key,
                user_id=user_id,
            )

            logger.info(
                f"Video processing task created | user_id={user_id} | "
                f"task_id={task.id} | s3_key={s3_key}",
            )

    except Exception as e:
        log_error(
            logger=logger,
            message=f"Failed to process video upload | user_id={user_id}",
            error=e,
            context={
                "filename": file_name,
            },
        )
        raise

    return ProcessVideoResponse(
        task_id=task.id,
    )


@router.get(
    path="/status/{task_id}",
    response_model=VideoStatusResponse,
)
async def get_video_status(
    task_id: str,
):
    """
    Get video processing task status.

    Args:
        task_id: Celery task ID

    Returns:
        Task status and result if ready
    """
    logger.debug(f"Checking task status | task_id={task_id}")

    task = AsyncResult(id=task_id, app=celery_app)

    if task.state == "PENDING":
        response = {
            "task_id": task_id,
            "status": "pending",
            "result": None,
        }
        logger.debug(f"Task is pending | task_id={task_id}")
    elif task.state in ("PROGRESS", "STARTED"):
        response = {
            "task_id": task_id,
            "status": "processing",
            "result": task.info if task.info else {},
        }
        logger.debug(f"Task is processing | task_id={task_id} | state={task.state}")
    elif task.state == "SUCCESS":
        response = {
            "task_id": task_id,
            "status": "completed",
            "result": task.result,
        }
        logger.info(f"Task completed successfully | task_id={task_id}")
    elif task.state == "FAILURE":
        error_info = str(task.info) if task.info else "Unknown error"
        response = {
            "task_id": task_id,
            "status": "failed",
            "result": {"error": error_info},
        }
        logger.error(
            f"Task failed | task_id={task_id} | state={task.state} | error={error_info}",
        )
    else:
        response = {
            "task_id": task_id,
            "status": "pending",
            "result": None,
        }
        logger.warning(
            f"Task in unknown state | task_id={task_id} | state={task.state} | info={task.info}",
        )

    return VideoStatusResponse(**response)

