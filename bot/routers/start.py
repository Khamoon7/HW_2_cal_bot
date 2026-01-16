from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.utils.ui import show_menu_for_user

router = Router()

@router.message(CommandStart())
async def start(message: Message, session_factory: async_sessionmaker) -> None:
    """
    Команда /start - приветствие и показ стартового меню.
    """
    await message.answer("Привет! Я помогу с водой, калориями, едой и тренировками.")
    await show_menu_for_user(message, session_factory)
