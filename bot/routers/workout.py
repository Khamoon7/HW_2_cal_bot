from __future__ import annotations

from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.models import WorkoutLog
from bot.db.repo import Repo
from bot.keyboards import kb_intensity
from bot.menu import hide_menu
from bot.services.nutrition import workout_extra_water, workout_kcal
from bot.utils.ui import show_menu_for_user

router = Router()


class WorkoutFSM(StatesGroup):
    """
    FSM для логирования тренировки:
    - type_: тип тренировки (бег, зал, йога и т.п.)
    - minutes: длительность в минутах
    - intensity: интенсивность нагрузки
    """
    type_ = State()
    minutes = State()
    intensity = State()


def _parse_int(text: str) -> int | None:
    """
    Безопасный парсинг int из строки.
    """
    try:
        return int(text.strip())
    except Exception:
        return None


@router.message(Command("log_workout"))
async def log_workout(message: Message, state: FSMContext) -> None:
    """
    Команда /log_workout - запуск сценария логирования тренировки.
    """
    await message.answer(
        "Какая была тренировка? 🏋️\n"
        "Например: бег, зал, йога",
        reply_markup=hide_menu(),
    )
    await state.set_state(WorkoutFSM.type_)


@router.message(WorkoutFSM.type_)
async def workout_type(message: Message, state: FSMContext) -> None:
    """
    Шаг 1: ввод типа тренировки.
    """
    workout_type_text = (message.text or "").strip()
    if not workout_type_text:
        await message.answer("Тип пустой. Напиши, например: бег")
        return

    await state.update_data(type=workout_type_text)
    await state.set_state(WorkoutFSM.minutes)
    await message.answer("Сколько минут? (например 30)")


@router.message(WorkoutFSM.minutes)
async def workout_minutes(message: Message, state: FSMContext) -> None:
    """
    Шаг 2: ввод длительности тренировки в минутах.
    """
    mins = _parse_int(message.text or "")
    if mins is None or mins <= 0 or mins > 600:
        await message.answer("Введи минуты (1..600), например 30.")
        return

    await state.update_data(minutes=mins)
    await state.set_state(WorkoutFSM.intensity)
    await message.answer("Интенсивность:", reply_markup=kb_intensity())


@router.callback_query(WorkoutFSM.intensity, F.data.startswith("int:"))
async def workout_intensity(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker,
) -> None:
    """
    Шаг 3: выбор интенсивности, расчёт калорий и сохранение тренировки.
    """
    intensity = callback.data.split(":", 1)[1]
    data = await state.get_data()

    workout_type_text = data["type"]
    mins = int(data["minutes"])

    async with session_factory() as session:
        repo = Repo(session)
        user = await repo.get_or_create_user(callback.from_user.id)

        # Без веса нельзя корректно посчитать калории
        if not user.weight_kg:
            await callback.message.answer("Сначала настрой профиль: Создать профиль / Профиль")
            await state.clear()
            await show_menu_for_user(callback.message, session_factory, tg_id=callback.from_user.id)
            await callback.answer()
            return

        # Расчёты
        kcal = workout_kcal(workout_type_text, mins, intensity, float(user.weight_kg))
        extra_water = workout_extra_water(mins)

        # Обновление агрегатов за сегодня
        st = await repo.get_or_create_day(user.id, date.today())
        st.calories_out += float(kcal)
        st.water_ml += int(extra_water)

        # Лог тренировки
        session.add(
            WorkoutLog(
                user_id=user.id,
                day=date.today(),
                workout_type=workout_type_text,
                minutes=mins,
                intensity=intensity,
                kcal_burned=float(kcal),
                extra_water_ml=int(extra_water),
            )
        )
        await session.commit()

    intensity_txt = (
        "лёгкая"
        if intensity == "low"
        else "средняя"
        if intensity == "medium"
        else "высокая"
    )

    await callback.message.answer(
        "Записано ✅\n"
        f"🏋️ {workout_type_text} {mins} мин ({intensity_txt})\n"
        f"🔥 Сожжено: ~{kcal:.0f} ккал\n"
        f"💧 Дополнительно выпей: {extra_water} мл (я уже добавил в воду за сегодня)"
    )

    await state.clear()
    await show_menu_for_user(callback.message, session_factory, tg_id=callback.from_user.id)
    await callback.answer()
