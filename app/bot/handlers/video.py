import asyncio
import httpx
import os
import tempfile
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, FSInputFile

from app.bot.keyboards.inline import get_buy_coins_keyboard
from app.bot.texts.messages import (
    CLIPS_READY_MESSAGE,
    DOWNLOADING_MESSAGE,
    ERROR_MESSAGE,
    INVALID_GOOGLE_DRIVE_LINK_MESSAGE,
    NO_COINS_MESSAGE,
    PROCESSING_MESSAGE,
)
from app.core.config import settings
from app.core.logger import get_logger, log_error
from app.services.billing.wallet import WalletService

logger = get_logger(__name__)
router = Router()
wallet_service = WalletService()
from app.services.storage.s3 import S3Service
from app.utils.billing.validators import check_balance_for_video_processing
from app.utils.video.google_drive import (
    extract_file_id_from_url,
    get_download_url_via_api,
    is_google_drive_url,
)

logger = get_logger(__name__)
router = Router()


async def poll_task_status(
    client: httpx.AsyncClient,
    task_id: str,
    max_attempts: int = 720,
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
    headers = {"X-API-Key": settings.API_SECRET_KEY}
    
    for attempt in range(max_attempts):
        try:
            response = await client.get(
                url=f"{settings.API_BASE_URL}/video/status/{task_id}",
                headers=headers,
            )

            if response.status_code != 200:
                logger.warning(
                    f"Task status request failed | task_id={task_id} | "
                    f"status_code={response.status_code} | attempt={attempt+1}/{max_attempts}"
                )
                await asyncio.sleep(delay)
                continue

            data = response.json()
            status = data.get("status")

            if status == "completed":
                return data.get("result")
            elif status == "failed":
                logger.error(f"Task failed on server | task_id={task_id}")
                return None

        except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError) as e:
            logger.warning(
                f"Connection error while polling task status | task_id={task_id} | "
                f"error={type(e).__name__} | attempt={attempt+1}/{max_attempts}"
            )
        except Exception as e:
            log_error(
                logger=logger,
                message="Unexpected error while polling task status",
                error=e,
                context={"task_id": task_id, "attempt": attempt + 1},
            )

        await asyncio.sleep(delay)

    return None


async def process_video_file(
    local_path: str,
    user_id: int,
    message: Message,
) -> None:
    """
    Process video file through API.

    Args:
        local_path: Path to local video file
        user_id: Telegram user ID
        message: Telegram message object
    """
    file_name = Path(local_path).name
    file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

    logger.info(
        f"Starting video processing | user_id={user_id} | "
        f"file={file_name} | size={file_size} bytes",
    )

    has_sufficient_balance, balance, required_cost = check_balance_for_video_processing(
        user_id=user_id,
    )
    
    if not has_sufficient_balance:
        logger.warning(
            f"Insufficient balance before processing | user_id={user_id} | "
            f"balance={balance} | required={required_cost}",
        )
        await message.answer(
            text=NO_COINS_MESSAGE.format(
                required=settings.MAX_CLIPS_COUNT,
                balance=balance,
            ),
            reply_markup=get_buy_coins_keyboard(),
        )
        return

    logger.info(
        f"Connecting to API | user_id={user_id} | "
        f"api_url={settings.API_BASE_URL}",
    )

    async with httpx.AsyncClient(
        timeout=600.0,
    ) as client:
        headers = {"X-API-Key": settings.API_SECRET_KEY}
        
        try:
            logger.debug(
                f"Checking API health | api_url={settings.API_BASE_URL}/health",
            )
            health_check = await client.get(
                url=f"{settings.API_BASE_URL}/health",
                timeout=5.0,
            )
            if health_check.status_code != 200:
                logger.warning(
                    f"API health check failed | user_id={user_id} | "
                    f"status_code={health_check.status_code} | "
                    f"api_url={settings.API_BASE_URL}",
                )
            else:
                logger.debug(
                    f"API health check passed | user_id={user_id}",
                )
        except Exception as e:
            logger.warning(
                f"API health check failed | user_id={user_id} | "
                f"api_url={settings.API_BASE_URL} | error={e} | "
                f"Will try to send file anyway",
            )

        with open(
            local_path,
            "rb",
        ) as video_file:
            logger.debug(
                f"Sending file to API | user_id={user_id} | "
                f"file_name={file_name} | file_size={file_size} | "
                f"api_url={settings.API_BASE_URL}",
            )

            try:
                response = await client.post(
                    url=f"{settings.API_BASE_URL}/video/process",
                    data={
                        "user_id": user_id,
                    },
                    files={
                        "file": (
                            file_name,
                            video_file,
                            "video/mp4",
                        ),
                    },
                    headers=headers,
                )
            except httpx.ConnectError as e:
                logger.error(
                    f"Failed to connect to API | user_id={user_id} | "
                    f"api_url={settings.API_BASE_URL} | error={e}",
                )
                await message.answer(
                    text="❌ Failed to connect to processing server. "
                    "Please check that API server is running.",
                )
                return
            except httpx.TimeoutException as e:
                logger.error(
                    f"API request timeout | user_id={user_id} | "
                    f"api_url={settings.API_BASE_URL} | error={e}",
                )
                await message.answer(
                    text="❌ Server response timeout exceeded. "
                    "Please try again later.",
                )
                return

        if response.status_code == 402:
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass
            
            error_detail = error_data.get("detail", "Insufficient balance")
            logger.warning(
                f"Insufficient balance for video processing | user_id={user_id} | "
                f"error={error_detail}",
            )
            
            balance_response = await client.get(
                url=f"{settings.API_BASE_URL}/billing/balance/{user_id}",
            )
            balance = 0
            if balance_response.status_code == 200:
                balance_data = balance_response.json()
                balance = balance_data.get("balance", 0)
            
            max_cost = settings.MAX_CLIPS_COUNT * settings.COINS_PER_CLIP
            await message.answer(
                text=NO_COINS_MESSAGE.format(
                    required=max_cost,
                    balance=balance,
                ),
                reply_markup=get_buy_coins_keyboard(),
            )
            return

        if response.status_code != 200:
            error_detail = ""
            try:
                error_detail = response.text
            except Exception:
                pass

            logger.error(
                f"Failed to start video processing | user_id={user_id} | "
                f"status_code={response.status_code} | error={error_detail}",
            )
            await message.answer(
                text=ERROR_MESSAGE,
            )
            return

        task_data = response.json()
        task_id = task_data["task_id"]

        logger.info(
            f"Video processing task created | user_id={user_id} | task_id={task_id}",
        )

        await message.answer(
            text=PROCESSING_MESSAGE.format(
                balance=balance - settings.MAX_CLIPS_COUNT,
            ),
        )

        result = await poll_task_status(
            client=client,
            task_id=task_id,
        )

        if result is None:
            logger.error(
                f"Video processing failed or timed out | user_id={user_id} | task_id={task_id}",
            )
            await message.answer(
                text=ERROR_MESSAGE,
            )
            return

        if result.get("status") == "no_coins":
            clips_count = result.get(
                "clips_count",
                0,
            )
            logger.warning(
                f"Insufficient balance for video processing | user_id={user_id} | "
                f"required_clips={clips_count}",
            )

            balance_response = await client.get(
                url=f"{settings.API_BASE_URL}/billing/balance/{user_id}",
            )
            balance = 0
            if balance_response.status_code == 200:
                balance_data = balance_response.json()
                balance = balance_data.get(
                    "balance",
                    0,
                )

            await message.answer(
                text=NO_COINS_MESSAGE.format(
                    required=clips_count,
                    balance=balance,
                ),
                reply_markup=get_buy_coins_keyboard(),
            )
            return

        if result.get("status") == "success":
            clip_s3_keys = result.get(
                "clip_s3_keys",
                [],
            )
            clips_count = len(clip_s3_keys)

            logger.info(
                f"Video processing completed | user_id={user_id} | "
                f"clips_count={clips_count} | task_id={task_id}",
            )

            # Get final balance after processing
            final_balance = wallet_service.get_balance(
                user_id=user_id,
            )

            await message.answer(
                text=CLIPS_READY_MESSAGE.format(
                    clips_count=clips_count,
                    balance=final_balance,
                ),
            )

            s3_service = S3Service()
            temp_clip_files = []

            async def download_and_send_clip(
                idx: int,
                clip_s3_key: str,
            ) -> str:
                logger.debug(
                    f"Downloading clip {idx}/{clips_count} | user_id={user_id} | "
                    f"s3_key={clip_s3_key}",
                )

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

                logger.debug(
                    f"Sending clip {idx}/{clips_count} to user | user_id={user_id} | "
                    f"path={temp_clip_path}",
                )

                video_input = FSInputFile(path=temp_clip_path)
                await message.answer_video(
                    video=video_input,
                )

                logger.debug(
                    f"Sent clip {idx}/{clips_count} to user | user_id={user_id}",
                )

                return temp_clip_path

            try:
                tasks = [
                    download_and_send_clip(
                        idx=idx,
                        clip_s3_key=clip_s3_key,
                    )
                    for idx, clip_s3_key in enumerate(clip_s3_keys, 1)
                ]
                
                temp_clip_files = await asyncio.gather(*tasks)
            finally:
                for temp_clip_path in temp_clip_files:
                    if os.path.exists(temp_clip_path):
                        os.unlink(temp_clip_path)
                        logger.debug(f"Cleaned up clip file | path={temp_clip_path}")
        else:
            logger.error(
                f"Video processing returned unknown status | user_id={user_id} | "
                f"status={result.get('status')} | task_id={task_id}",
            )
            await message.answer(
                text=ERROR_MESSAGE,
            )


@router.message(F.video)
async def handle_video(
    message: Message,
) -> None:
    """
    Handle video file upload.

    Args:
        message: Telegram message with video
    """
    if not message.from_user or not message.video:
        return

    user_id = message.from_user.id
    file_id = message.video.file_id

    logger.info(
        f"Received video file | user_id={user_id} | file_id={file_id}",
    )

    local_path = None

    try:
        file = await message.bot.get_file(
            file_id=file_id,
        )

        file_path = Path(file.file_path)
        file_extension = file_path.suffix
        file_size = message.video.file_size

        logger.info(
            f"Downloading video file | user_id={user_id} | "
            f"file_path={file.file_path} | size={file_size}",
        )

        local_path = f"/tmp/{file.file_id}{file_extension}"

        await message.bot.download_file(
            file_path=file.file_path,
            destination=local_path,
        )

        logger.info(
            f"Video file downloaded | user_id={user_id} | local_path={local_path}",
        )

        await process_video_file(
            local_path=local_path,
            user_id=user_id,
            message=message,
        )

    except Exception as e:
        log_error(
            logger=logger,
            message=f"Failed to handle video file | user_id={user_id}",
            error=e,
            context={"file_id": file_id},
        )
        await message.answer(
            text=ERROR_MESSAGE,
        )
    finally:
        if local_path and os.path.exists(local_path):
            os.unlink(local_path)
            logger.debug(
                f"Cleaned up temp file | path={local_path}",
            )


@router.message(F.text)
async def handle_text_message(
    message: Message,
) -> None:
    """
    Handle text message - check if it's a Google Drive link.

    Args:
        message: Telegram message object
    """
    if not message.text:
        return

    text = message.text.strip()

    if not is_google_drive_url(url=text):
        return

    user_id = message.from_user.id

    logger.info(
        f"Received Google Drive link | user_id={user_id} | url={text[:50]}...",
    )

    local_path = None

    try:
        file_id = extract_file_id_from_url(
            url=text,
        )

        if not file_id:
            logger.warning(
                f"Failed to extract file ID from Google Drive URL | user_id={user_id} | "
                f"url={text[:50]}...",
            )
            await message.answer(
                text=INVALID_GOOGLE_DRIVE_LINK_MESSAGE,
            )
            return

        logger.info(
            f"Extracted file ID from Google Drive URL | user_id={user_id} | file_id={file_id}",
        )

        download_url = get_download_url_via_api(
            file_id=file_id,
        )

        if not download_url:
            logger.error(
                f"Google Drive API key is not configured | user_id={user_id}",
            )
            await message.answer(
                text="❌ Google Drive API is not configured. Please contact administrator.",
            )
            return

        has_sufficient_balance, balance, required_cost = check_balance_for_video_processing(
            user_id=user_id,
        )
        
        if not has_sufficient_balance:
            logger.warning(
                f"Insufficient balance before download | user_id={user_id} | "
                f"balance={balance} | required={required_cost}",
            )
            await message.answer(
                text=NO_COINS_MESSAGE.format(
                    required=settings.MAX_CLIPS_COUNT,
                    balance=balance,
                ),
                reply_markup=get_buy_coins_keyboard(),
            )
            return

        await message.answer(
            text=DOWNLOADING_MESSAGE,
        )

        # Check file size before downloading
        async with httpx.AsyncClient(timeout=10.0) as client:
            head_response = await client.head(download_url, follow_redirects=True)
            if head_response.status_code == 200:
                file_size = int(head_response.headers.get("Content-Length", 0))
                max_size = 4 * 1024 * 1024 * 1024 # 4GB
                if file_size > max_size:
                    logger.warning(f"Google Drive file too large | size={file_size}")
                    await message.answer("❌ This file is too large (max 4GB). Please upload a smaller video.")
                    return

        local_path = f"/tmp/{user_id}_{os.urandom(8).hex()}.mp4"

        logger.info(
            f"Starting download from Google Drive via API | user_id={user_id} | "
            f"file_id={file_id} | local_path={local_path}",
        )

        downloaded_bytes = 0
        async with httpx.AsyncClient(
            timeout=600.0,
            follow_redirects=True,
        ) as client:
            async with client.stream(
                method="GET",
                url=download_url,
            ) as response:
                if response.status_code != 200:
                    logger.error(
                        f"Failed to download from Google Drive API | user_id={user_id} | "
                        f"file_id={file_id} | status_code={response.status_code}",
                    )
                    await message.answer(
                        text=ERROR_MESSAGE,
                    )
                    return

                buffer_size = 1024 * 256
                with open(
                    local_path,
                    "wb",
                    buffering=buffer_size,
                ) as f:
                    async for chunk in response.aiter_bytes(
                        chunk_size=buffer_size,
                    ):
                        f.write(chunk)
                        downloaded_bytes += len(chunk)

        logger.info(
            f"Downloaded video from Google Drive via API | user_id={user_id} | "
            f"file_id={file_id} | size={downloaded_bytes} bytes | local_path={local_path}",
        )

        await process_video_file(
            local_path=local_path,
            user_id=user_id,
            message=message,
        )

    except httpx.TimeoutException as e:
        log_error(
            logger=logger,
            message=f"Timeout processing Google Drive link | user_id={user_id}",
            error=e,
            context={"url": text[:50]},
        )
        await message.answer(
            text=ERROR_MESSAGE,
        )
    except Exception as e:
        log_error(
            logger=logger,
            message=f"Failed to process Google Drive link | user_id={user_id}",
            error=e,
            context={"url": text[:50]},
        )
        await message.answer(
            text=ERROR_MESSAGE,
        )
    finally:
        if local_path and os.path.exists(local_path):
            os.unlink(local_path)
            logger.debug(
                f"Cleaned up temp file | path={local_path}",
            )

