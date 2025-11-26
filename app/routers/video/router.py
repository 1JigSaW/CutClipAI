import os
import tempfile

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from celery.result import AsyncResult

from app.core.celery_app import celery_app
from app.services.storage.s3 import S3Service
from app.workers.video.worker import process_video_task

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
    suffix = os.path.splitext(file.filename or "video.mp4")[1]
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, dir="/tmp")

    try:
        with os.fdopen(temp_fd, "wb") as f:
            content = await file.read()
            f.write(content)

        s3_service = S3Service()
        s3_key = s3_service.upload_file(
            file_path=temp_path,
            prefix=f"videos/input/{user_id}",
        )

        if os.path.exists(temp_path):
            os.unlink(temp_path)

        task = process_video_task.delay(
            s3_key=s3_key,
            user_id=user_id,
        )
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
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
    task = AsyncResult(id=task_id, app=celery_app)

    if task.state == "PENDING":
        response = {
            "task_id": task_id,
            "status": "pending",
            "result": None,
        }
    elif task.state == "PROGRESS":
        response = {
            "task_id": task_id,
            "status": "processing",
            "result": task.info,
        }
    elif task.state == "SUCCESS":
        response = {
            "task_id": task_id,
            "status": "completed",
            "result": task.result,
        }
    else:
        response = {
            "task_id": task_id,
            "status": "failed",
            "result": {"error": str(task.info)},
        }

    return VideoStatusResponse(**response)

