from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_buy_coins_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for buying coins via Telegram Stars.

    Returns:
        Inline keyboard markup with coin purchase options
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎯 Starter: 10 clips (150 ⭐)",
                    callback_data="buy_stars:10:150",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Creator: 35 clips (450 ⭐) - POPULAR",
                    callback_data="buy_stars:35:450",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💎 Pro: 100 clips (990 ⭐)",
                    callback_data="buy_stars:100:990",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 Check Balance",
                    callback_data="check_balance",
                ),
            ],
        ]
    )
    return keyboard


def get_balance_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for balance check.

    Returns:
        Inline keyboard markup with balance options
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Buy coins",
                    callback_data="buy_coins_menu",
                ),
            ],
        ]
    )
    return keyboard


def get_upload_video_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for video upload.

    Returns:
        Inline keyboard markup with video upload button
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Upload Video",
                    callback_data="upload_video",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💳 Buy Coins",
                    callback_data="buy_coins_menu",
                ),
            ],
        ]
    )
    return keyboard

