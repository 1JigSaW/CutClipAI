import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import billing, start, video
from app.core.config import settings
from app.core.logger import get_logger, setup_logging

logger = get_logger(__name__)

setup_logging(level="INFO")


async def main() -> None:
    """
    Initialize and start Telegram bot.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not token.strip():
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set in environment variables. "
            "Please set it in .env file or environment variables."
        )

    bot = Bot(
        token=token.strip(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN,
        ),
    )
    storage = MemoryStorage()
    dp = Dispatcher(
        storage=storage,
    )

    dp.include_router(router=start.router)
    dp.include_router(router=video.router)
    dp.include_router(router=billing.router)

    logger.info(
        f"Starting Telegram bot polling | "
        f"API_BASE_URL={settings.API_BASE_URL} | "
        f"REDIS_HOST={settings.REDIS_HOST}",
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

