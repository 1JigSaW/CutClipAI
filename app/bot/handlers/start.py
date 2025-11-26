from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.bot.keyboards.inline import get_upload_video_keyboard
from app.bot.texts.messages import ERROR_MESSAGE, START_MESSAGE, VIDEO_REQUIREMENTS_MESSAGE

router = Router()


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
            await message.answer(
                text=ERROR_MESSAGE,
            )
            return

        await message.answer(
            text=START_MESSAGE,
            reply_markup=get_upload_video_keyboard(),
        )
    except Exception:
        await message.answer(
            text=ERROR_MESSAGE,
            reply_markup=ReplyKeyboardRemove(),
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
    await callback.message.answer(
        text=VIDEO_REQUIREMENTS_MESSAGE,
    )
    await callback.answer()

