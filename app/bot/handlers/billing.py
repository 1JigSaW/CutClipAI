import httpx

from aiogram import Router, F
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery, Message

from app.bot.keyboards.inline import get_balance_keyboard, get_buy_coins_keyboard
from app.bot.texts.messages import (
    BALANCE_MESSAGE,
    BUY_COINS_MESSAGE,
    COINS_ADDED_MESSAGE,
)
from app.core.config import settings
from app.core.logger import get_logger, log_error
from app.services.billing.wallet import WalletService

logger = get_logger(__name__)
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
    if not callback.message or not callback.from_user:
        return

    user_id = callback.from_user.id

    logger.info(
        f"User checking balance | user_id={user_id}",
    )

    balance = wallet_service.get_balance(
        user_id=user_id,
    )

    logger.debug(
        f"Balance retrieved | user_id={user_id} | balance={balance}",
    )

    await callback.message.answer(
        text=BALANCE_MESSAGE.format(
            balance=balance,
        ),
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
    if not callback.message:
        return

    await callback.message.answer(
        text=BUY_COINS_MESSAGE,
        reply_markup=get_buy_coins_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("buy_stars:"))
async def handle_buy_stars(
    callback: CallbackQuery,
) -> None:
    """
    Handle buy coins callback - send invoice for Telegram Stars.

    Args:
        callback: Callback query object
    """
    if not callback.message or not callback.from_user:
        return

    data_parts = callback.data.split(":")
    amount = int(data_parts[1])
    stars_price = int(data_parts[2])

    user_id = callback.from_user.id

    logger.info(
        f"User creating invoice | user_id={user_id} | "
        f"amount={amount} | stars={stars_price}",
    )

    # Use XTR for Telegram Stars
    prices = [
        LabeledPrice(
            label=f"{amount} AI Clips",
            amount=stars_price,
        )
    ]

    await callback.message.answer_invoice(
        title=f"Top Up: {amount} Coins",
        description=f"Get {amount} AI-powered video clips with subtitles. "
                    f"1 Clip = 1 Coin.",
        prices=prices,
        payload=f"buy_coins:{amount}",
        currency="XTR",
        provider_token="", # Empty for Telegram Stars
    )

    await callback.answer()


@router.pre_checkout_query()
async def handle_pre_checkout(
    pre_checkout_query: PreCheckoutQuery,
) -> None:
    """
    Handle pre-checkout query. Always answer OK for stars.
    """
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(
    message: Message,
) -> None:
    """
    Handle successful payment and add coins to wallet.
    """
    if not message.successful_payment or not message.from_user:
        return

    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    
    if payload.startswith("buy_coins:"):
        amount = int(payload.split(":")[1])
        
        logger.info(
            f"Payment successful | user_id={user_id} | amount={amount}",
        )

        async with httpx.AsyncClient() as client:
            headers = {"X-API-Key": settings.API_SECRET_KEY}
            
            response = await client.post(
                url=f"{settings.API_BASE_URL}/billing/buy",
                json={
                    "user_id": user_id,
                    "amount": amount,
                },
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                new_balance = data["new_balance"]

                await message.answer(
                    text=COINS_ADDED_MESSAGE.format(
                        amount=amount,
                        balance=new_balance,
                    ),
                )
            else:
                logger.error(
                    f"Failed to update balance after payment | user_id={user_id} | "
                    f"amount={amount} | status_code={response.status_code}",
                )
                await message.answer(
                    text="❌ Payment received but failed to update balance. "
                         "Please contact support with your payment ID.",
                )

