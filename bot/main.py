import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.db.session import make_engine, make_session_factory, init_db
from bot.logging_mw import LoggingMiddleware

from bot.routers.food import router as food_router
from bot.routers.menu_router import router as menu_router
from bot.routers.plots import router as plots_router
from bot.routers.profile import router as profile_router
from bot.routers.progress import router as progress_router
from bot.routers.recommendations import router as rec_router
from bot.routers.start import router as start_router
from bot.routers.water import router as water_router
from bot.routers.workout import router as workout_router


async def main():
    """
    Точка входа: инициализация логов, БД, диспетчера и запуск polling.
    """
    # Настройка логирования
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("bot")
    logger.info("Инициализация...")

    # Инициализация БД и фабрики сессий (кладём в dp для доступа из роутеров)
    engine = make_engine(settings.db_path)
    await init_db(engine)
    session_factory = make_session_factory(engine)

    # Инициализация Telegram-бота и диспетчера
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware логирования апдейтов
    dp.update.middleware(LoggingMiddleware())

    # Dependency injection: доступ к session_factory из хэндлеров через data["session_factory"]
    dp["session_factory"] = session_factory

    # Подключение роутеров
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(water_router)
    dp.include_router(food_router)
    dp.include_router(workout_router)
    dp.include_router(progress_router)
    dp.include_router(plots_router)
    dp.include_router(rec_router)
    dp.include_router(menu_router)

    logging.getLogger("bot").info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запуск приложения
    asyncio.run(main())
