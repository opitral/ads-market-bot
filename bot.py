import argparse
import asyncio
import logging

from aiogram import Bot, Dispatcher

from config_reader import config
from database.engine import drop_db, create_db, session_maker
from handlers import admin, vendor, group
from middlewares.db import DatabaseSessionMiddleware


async def on_startup(bot: Bot) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop-database", action="store_true")
    parser.add_argument("--no-drop-database", action="store_false")
    args = parser.parse_args()

    if args.drop_database:
        await drop_db()

    await create_db()

    for admin_telegram_id in config.ADMIN_TELEGRAM_IDS:
        await bot.send_message(admin_telegram_id, "Бот запущен")


async def on_shutdown(bot: Bot) -> None:
    for admin_telegram_id in config.ADMIN_TELEGRAM_IDS:
        await bot.send_message(admin_telegram_id, "Бот остановлен")


async def main():
    logging.basicConfig(level=logging.INFO)

    file_handler = logging.FileHandler("bot.log")
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(file_handler)

    bot = Bot(token=config.BOT_API_TOKEN.get_secret_value())
    dp = Dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.update.middleware(DatabaseSessionMiddleware(session_pool=session_maker))

    dp.include_router(admin.router)
    dp.include_router(vendor.router)
    dp.include_router(group.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
