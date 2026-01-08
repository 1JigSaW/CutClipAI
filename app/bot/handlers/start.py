from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.bot.keyboards.inline import get_upload_video_keyboard
from app.bot.texts.messages import ERROR_MESSAGE, START_MESSAGE, VIDEO_REQUIREMENTS_MESSAGE, HELP_MESSAGE
from app.core.config import settings
from app.core.logger import get_logger, log_error
from app.services.billing.wallet import WalletService

logger = get_logger(__name__)
router = Router()
wallet_service = WalletService()


@router.message(Command("start"))
async def cmd_start(
    message: Message,
) -> None:
    """
    Handle /start command.

    Args:
        message: Telegram message object
    """
    try:
        if not message.from_user:
            logger.warning(
                "Received /start command without from_user",
            )
            await message.answer(
                text=ERROR_MESSAGE,
            )
            return

        user_id = message.from_user.id
        username = message.from_user.username or "unknown"

        logger.info(
            f"Received /start command | user_id={user_id} | username={username}",
        )

        balance = wallet_service.get_balance(
            user_id=user_id,
        )

        await message.answer(
            text=START_MESSAGE.format(
                balance=balance,
                max_clips=settings.MAX_CLIPS_COUNT,
            ),
            reply_markup=get_upload_video_keyboard(),
        )

        logger.debug(
            f"Sent welcome message | user_id={user_id}",
        )
    except Exception as e:
        log_error(
            logger=logger,
            message="Failed to handle /start command",
            error=e,
        )
        await message.answer(
            text=ERROR_MESSAGE,
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(Command("help"))
async def cmd_help(
    message: Message,
) -> None:
    """
    Handle /help command.

    Args:
        message: Telegram message object
    """
    try:
        user_id = message.from_user.id if message.from_user else "unknown"
        logger.info(
            f"Received /help command | user_id={user_id}",
        )
        await message.answer(
            text=HELP_MESSAGE,
        )
    except Exception as e:
        log_error(
            logger=logger,
            message="Failed to handle /help command",
            error=e,
        )
        await message.answer(
            text=ERROR_MESSAGE,
        )


@router.callback_query(F.data == "upload_video")
async def handle_upload_video_callback(
    callback: CallbackQuery,
) -> None:
    """
    Handle upload video callback.

    Args:
        callback: Callback query object
    """
    user_id = callback.from_user.id

    logger.info(
        f"User requested video upload instructions | user_id={user_id}",
    )

    if not callback.message:
        return

    balance = wallet_service.get_balance(
        user_id=user_id,
    )

    await callback.message.answer(
        text=VIDEO_REQUIREMENTS_MESSAGE.format(
            balance=balance,
            max_clips=settings.MAX_CLIPS_COUNT,
        ),
    )
    await callback.answer()

