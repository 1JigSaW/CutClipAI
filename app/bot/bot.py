import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import billing, start, video
from app.core.config import settings


async def main() -> None:
    """
    Initialize and start Telegram bot.
    """
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(router=start.router)
    dp.include_router(router=video.router)
    dp.include_router(router=billing.router)

    await dp.start_polling(bot=bot)


if __name__ == "__main__":
    asyncio.run(main())

