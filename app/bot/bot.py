import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import billing, start, video
from app.core.config import settings


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

    bot = Bot(token=token.strip())
    storage = MemoryStorage()
    dp = Dispatcher(
        storage=storage,
    )

    dp.include_router(router=start.router)
    dp.include_router(router=video.router)
    dp.include_router(router=billing.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

