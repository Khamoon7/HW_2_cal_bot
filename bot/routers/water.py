from __future__ import annotations

from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.repo import Repo
from bot.keyboards import kb_water_quick
from bot.menu import hide_menu
from bot.utils.ui import show_menu_for_user

router = Router()


class WaterFSM(StatesGroup):
    """
    FSM для ручного ввода воды (когда пользователь выбирает "Ввести вручную").
    """
    custom_ml = State()


def _parse_int(text: str) -> int | None:
    """
    Безопасный парсинг int из текста.
    """
    try:
        return int(text.strip())
    except Exception:
        return None


@router.message(Command("log_water"))
async def log_water(message: Message) -> None:
    """
    Команда /log_water - показывает быстрые варианты добавления воды.
    """
    await message.answer("Сколько воды добавим? 💧", reply_markup=hide_menu())
    await message.answer("Выбери вариант:", reply_markup=kb_water_quick())


@router.callback_query(F.data.startswith("water_add:"))
async def water_add(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker,
) -> None:
    """
    Обработка inline-кнопок воды:
    - water_add:<ml>
    - water_add:custom (переход на ручной ввод)
    """
    val = callback.data.split(":", 1)[1]

    # Ручной ввод
    if val == "custom":
        await state.set_state(WaterFSM.custom_ml)
        await callback.message.answer("Введи количество воды в мл, например 250:")
        await callback.answer()
        return

    # Быстрый вариант (100/200/300/500)
    ml = int(val)
    await _add_water(callback.message, ml, session_factory, tg_id=callback.from_user.id)
    await callback.answer()


@router.message(WaterFSM.custom_ml)
async def water_custom(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker,
) -> None:
    """
    Ручной ввод миллилитров воды.
    """
    ml = _parse_int(message.text or "")
    if ml is None or ml <= 0 or ml > 5000:
        await message.answer("Введи мл (1..5000), например 250.")
        return

    await _add_water(message, ml, session_factory, tg_id=message.from_user.id)
    await state.clear()


async def _add_water(
    message: Message,
    ml: int,
    session_factory: async_sessionmaker,
    *,
    tg_id: int | None = None,
) -> None:
    """
    Добавляет воду в DayStat.water_ml за текущий день и возвращает пользователя в меню.
    """
    # tg_id либо передали явно (например, из CallbackQuery), либо берём из Message
    actual_tg_id = tg_id if tg_id is not None else message.from_user.id

    async with session_factory() as session:
        repo = Repo(session)

        # Создаём пользователя при первом обращении
        user = await repo.get_or_create_user(actual_tg_id)

        # Достаём/создаём дневную статистику и увеличиваем воду
        st = await repo.get_or_create_day(user.id, date.today())
        st.water_ml += int(ml)

        await session.commit()

    await message.answer(f"Записано ✅ +{ml} мл.")
    await show_menu_for_user(message, session_factory, tg_id=actual_tg_id)
