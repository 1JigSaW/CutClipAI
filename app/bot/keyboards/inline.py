from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_buy_coins_keyboard() -> InlineKeyboardMarkup:
    """
    Create inline keyboard for buying coins.

    Returns:
        Inline keyboard markup with coin purchase options
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="5 coins",
                    callback_data="buy_coins:5",
                ),
                InlineKeyboardButton(
                    text="20 coins",
                    callback_data="buy_coins:20",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="50 coins",
                    callback_data="buy_coins:50",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Check balance",
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
                    text="Buy coins",
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
        ]
    )
    return keyboard

