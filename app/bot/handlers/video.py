import asyncio
import httpx
import os
import tempfile
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message

from app.bot.keyboards.inline import get_buy_coins_keyboard
from app.bot.texts.messages import (
    CLIPS_READY_MESSAGE,
    ERROR_MESSAGE,
    NO_COINS_MESSAGE,
    PROCESSING_MESSAGE,
)
from app.core.config import settings
from app.services.storage.s3 import S3Service

router = Router()


@router.message(F.video)
async def handle_video(
    message: Message,
) -> None:
    """
    Handle video file upload.

    Args:
        message: Telegram message with video
    """
    user_id = message.from_user.id

    local_path = None

    try:
        file = await message.bot.get_file(
            file_id=message.video.file_id,
        )

        file_path = Path(file.file_path)
        file_extension = file_path.suffix

        local_path = f"/tmp/{file.file_id}{file_extension}"

        await message.bot.download_file(
            file_path=file.file_path,
            destination=local_path,
        )

        async with httpx.AsyncClient() as client:
            with open(local_path, "rb") as video_file:
                response = await client.post(
                    url=f"{settings.API_BASE_URL}/video/process",
                    params={"user_id": user_id},
                    files={"file": (file_path.name, video_file, "video/mp4")},
                )

            if response.status_code != 200:
                await message.answer(text=ERROR_MESSAGE)
                return

            task_data = response.json()
            task_id = task_data["task_id"]

            await message.answer(text=PROCESSING_MESSAGE)

            result = await poll_task_status(
                client=client,
                task_id=task_id,
            )

            if result is None:
                await message.answer(text=ERROR_MESSAGE)
                return

            if result.get("status") == "no_coins":
                balance_response = await client.get(
                    url=f"{settings.API_BASE_URL}/billing/balance/{user_id}",
                )
                balance = 0
                if balance_response.status_code == 200:
                    balance_data = balance_response.json()
                    balance = balance_data.get("balance", 0)

                await message.answer(
                    text=NO_COINS_MESSAGE.format(
                        required=result.get("clips_count", 0),
                        balance=balance,
                    ),
                    reply_markup=get_buy_coins_keyboard(),
                )
                return

            if result.get("status") == "success":
                clip_s3_keys = result.get("clip_s3_keys", [])
                clips_count = len(clip_s3_keys)

                await message.answer(
                    text=CLIPS_READY_MESSAGE.format(clips_count=clips_count),
                )

                s3_service = S3Service()
                temp_clip_files = []

                try:
                    for clip_s3_key in clip_s3_keys:
                        clip_extension = Path(clip_s3_key).suffix
                        temp_fd, temp_clip_path = tempfile.mkstemp(
                            suffix=clip_extension,
                            dir=settings.TEMP_DIR,
                        )
                        os.close(temp_fd)

                        s3_service.download_file(
                            s3_key=clip_s3_key,
                            local_path=temp_clip_path,
                        )

                        temp_clip_files.append(temp_clip_path)

                        with open(temp_clip_path, "rb") as clip_file:
                            await message.answer_video(
                                video=clip_file,
                            )
                finally:
                    for temp_clip_path in temp_clip_files:
                        if os.path.exists(temp_clip_path):
                            os.unlink(temp_clip_path)
            else:
                await message.answer(text=ERROR_MESSAGE)

    except Exception as e:
        await message.answer(text=ERROR_MESSAGE)
    finally:
        if local_path and os.path.exists(local_path):
            os.unlink(local_path)


async def poll_task_status(
    client: httpx.AsyncClient,
    task_id: str,
    max_attempts: int = 120,
    delay: int = 5,
) -> dict | None:
    """
    Poll task status until completion.

    Args:
        client: HTTP client
        task_id: Task ID to poll
        max_attempts: Maximum polling attempts
        delay: Delay between attempts in seconds

    Returns:
        Task result dictionary or None
    """
    for _ in range(max_attempts):
        response = await client.get(
            url=f"{settings.API_BASE_URL}/video/status/{task_id}",
        )

        if response.status_code != 200:
            return None

        data = response.json()
        status = data.get("status")

        if status == "completed":
            return data.get("result")
        elif status == "failed":
            return None

        await asyncio.sleep(delay)

    return None

