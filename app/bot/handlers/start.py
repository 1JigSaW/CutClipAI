from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards.inline import get_buy_coins_keyboard
from app.bot.texts.messages import BALANCE_MESSAGE, WELCOME_MESSAGE
from app.services.billing.wallet import WalletService

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
    user_id = message.from_user.id

    balance = wallet_service.get_balance(user_id=user_id)

    await message.answer(
        text=WELCOME_MESSAGE,
        reply_markup=get_buy_coins_keyboard(),
    )

    await message.answer(
        text=BALANCE_MESSAGE.format(balance=balance),
        reply_markup=get_buy_coins_keyboard(),
    )

