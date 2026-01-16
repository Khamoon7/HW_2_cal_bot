from __future__ import annotations

from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import settings
from bot.db.repo import Repo
from bot.menu import hide_menu
from bot.services.nutrition import apply_goal, bmr_mifflin, tdee_from_bmr, water_goal_ml
from bot.services.weather import get_temperature_c
from bot.utils.ui import show_menu_for_user

router = Router()


@router.message(Command("check_progress"))
async def check_progress(message: Message, session_factory: async_sessionmaker) -> None:
    """
    Команда /check_progress - показывает прогресс за сегодня:
    - вода (выпито / цель / осталось)
    - калории (потреблено / цель / сожжено / баланс)
    - температура (если доступен OpenWeather API key)
    """
    await message.answer("Считаю прогресс…", reply_markup=hide_menu())

    async with session_factory() as session:
        repo = Repo(session)

        user = await repo.get_or_create_user(message.from_user.id)

        # Без заполненного профиля не можем корректно считать цели
        if not (
            user.sex
            and user.weight_kg
            and user.height_cm
            and user.age
            and user.activity_min_per_day is not None
            and user.city
            and user.goal
        ):
            await message.answer("Сначала создай профиль: Создать профиль")
            await show_menu_for_user(message, session_factory)
            return

        # Дневная статистика за сегодня (создаётся при отсутствии)
        st = await repo.get_or_create_day(user.id, date.today())

        # Температура в городе пользователя (влияет на цель по воде)
        temp = (
            await get_temperature_c(user.city, settings.openweather_api_key)
            if settings.openweather_api_key
            else None
        )
        w_goal = water_goal_ml(float(user.weight_kg), int(user.activity_min_per_day), temp)

        # Цель по калориям: ручная (если задана) иначе рассчитываем
        if user.calorie_goal_manual is not None:
            cal_goal = int(user.calorie_goal_manual)
        else:
            act = int(user.activity_min_per_day)
            level = "low" if act < 30 else ("medium" if act < 60 else "high")

            bmr = bmr_mifflin(user.sex, float(user.weight_kg), float(user.height_cm), int(user.age))
            tdee = tdee_from_bmr(bmr, level)
            cal_goal = int(apply_goal(tdee, user.goal))

        # Производные показатели
        water_left = max(0, int(w_goal) - int(st.water_ml))
        balance = float(st.calories_in) - float(st.calories_out)
        temp_txt = "не удалось получить" if temp is None else f"{temp:.1f}°C"

        # Вытаскиваем значения в локальные переменные
        water_ml = int(st.water_ml)
        cal_in = float(st.calories_in)
        cal_out = float(st.calories_out)

    await message.answer(
        "📊 Прогресс за сегодня:\n\n"
        f"🌡️ Температура: {temp_txt}\n\n"
        "💧 Вода:\n"
        f"— Выпито: {water_ml} мл из {int(w_goal)} мл\n"
        f"— Осталось: {water_left} мл\n\n"
        "🔥 Калории:\n"
        f"— Потреблено: {cal_in:.1f} ккал из {cal_goal} ккал\n"
        f"— Сожжено: {cal_out:.1f} ккал\n"
        f"— Баланс (in - out): {balance:.1f} ккал"
    )

    await show_menu_for_user(message, session_factory)
