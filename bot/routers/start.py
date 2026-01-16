from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.utils.ui import show_menu_for_user

router = Router()

@router.message(CommandStart())
async def start(message: Message, session_factory: async_sessionmaker) -> None:
    """
    Команда /start - приветствие и показ стартового меню.
    """
    await message.answer(
        "Привет! 👋\n"
        "Я помогу тебе следить за едой, водой и тренировками - без заморочек.\n\n"
        "Что можно делать:\n"
        "🥗 отмечать еду\n"
        "💧 закрывать норму воды\n"
        "🏋️ логировать тренировки\n"
        "📊 смотреть прогресс и получать подсказки\n"
        "👤 настроить профиль, чтобы цели считались точно\n\n"
        "Жми кнопку ниже - начнём 👇"
    )
    await show_menu_for_user(message, session_factory)


@router.message(Command("help"))
async def help_cmd(message: Message, session_factory: async_sessionmaker):
    """
    Команда /help - отображение помощи по боту.
    """
    await message.answer(
        "ℹ️ Как пользоваться ботом\n\n"
        "Можно через кнопки или команды.\n\n"
        "🥗 Еда - записывать, что поел\n"
        "💧 Вода - отмечать стаканы/объём\n"
        "🏋️ Тренировка - фиксировать активность\n"
        "📊 Прогресс - итоги за день\n"
        "👤 Профиль - параметры и цель\n\n"
        "Команды:\n"
        "/set_profile — профиль\n"
        "/log_food — еда\n"
        "/log_water — вода\n"
        "/log_workout — тренировка\n"
        "/check_progress — прогресс\n"
        "/plot — графики\n\n"
        "Открывай меню 👇"
    )
    await show_menu_for_user(message, session_factory)