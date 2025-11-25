import httpx

from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.bot.keyboards.inline import get_balance_keyboard, get_buy_coins_keyboard
from app.bot.texts.messages import (
    BALANCE_MESSAGE,
    BUY_COINS_MESSAGE,
    COINS_ADDED_MESSAGE,
)
from app.core.config import settings
from app.services.billing.wallet import WalletService

router = Router()

wallet_service = WalletService()


@router.callback_query(F.data == "check_balance")
async def handle_check_balance(
    callback: CallbackQuery,
) -> None:
    """
    Handle balance check callback.

    Args:
        callback: Callback query object
    """
    user_id = callback.from_user.id

    balance = wallet_service.get_balance(user_id=user_id)

    await callback.message.answer(
        text=BALANCE_MESSAGE.format(balance=balance),
        reply_markup=get_balance_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "buy_coins_menu")
async def handle_buy_coins_menu(
    callback: CallbackQuery,
) -> None:
    """
    Handle buy coins menu callback.

    Args:
        callback: Callback query object
    """
    await callback.message.answer(
        text=BUY_COINS_MESSAGE,
        reply_markup=get_buy_coins_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("buy_coins:"))
async def handle_buy_coins(
    callback: CallbackQuery,
) -> None:
    """
    Handle buy coins callback.

    Args:
        callback: Callback query object
    """
    user_id = callback.from_user.id
    amount_str = callback.data.split(":")[1]
    amount = int(amount_str)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f"{settings.API_BASE_URL}/billing/buy",
            json={
                "user_id": user_id,
                "amount": amount,
            },
        )

        if response.status_code == 200:
            data = response.json()
            new_balance = data["new_balance"]

            await callback.message.answer(
                text=COINS_ADDED_MESSAGE.format(
                    amount=amount,
                    balance=new_balance,
                ),
            )
        else:
            await callback.message.answer(
                text="❌ Failed to purchase coins. Please try again.",
            )

    await callback.answer()

