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


@router.message(Command("recommend"))
async def recommend(message: Message, session_factory: async_sessionmaker) -> None:
    """
    Команда /recommend - выдаёт рекомендации на сегодня по воде и калориям
    на основе текущего прогресса и целей пользователя.
    """
    await message.answer("Готовлю рекомендации…", reply_markup=hide_menu())

    async with session_factory() as session:
        repo = Repo(session)

        user = await repo.get_or_create_user(message.from_user.id)

        # Без заполненного профиля цели не посчитать
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

        # Дневная статистика за сегодня
        st = await repo.get_or_create_day(user.id, date.today())

        # Температура (влияет на цель воды), если задан ключ OpenWeather
        temp = (
            await get_temperature_c(user.city, settings.openweather_api_key)
            if settings.openweather_api_key
            else None
        )

        # Цель по воде и остаток
        w_goal = water_goal_ml(float(user.weight_kg), int(user.activity_min_per_day), temp)
        water_left = max(0, int(w_goal) - int(st.water_ml))

        # Цель по калориям: ручная (если задана) иначе рассчитываем
        if user.calorie_goal_manual is not None:
            cal_goal = int(user.calorie_goal_manual)
        else:
            act = int(user.activity_min_per_day)
            level = "low" if act < 30 else ("medium" if act < 60 else "high")

            bmr = bmr_mifflin(user.sex, float(user.weight_kg), float(user.height_cm), int(user.age))
            tdee = tdee_from_bmr(bmr, level)
            cal_goal = int(apply_goal(tdee, user.goal))

        # Остаток по калориям
        cal_left = max(0, int(cal_goal) - int(st.calories_in))

    # Текстовые подсказки
    tips: list[str] = []

    # Советы по воде
    if water_left >= 600:
        tips.append(
            f"💧 До нормы воды осталось {water_left} мл — попробуй выпить 300–500 мл в ближайший час."
        )
    elif water_left > 0:
        tips.append(f"💧 Осталось {water_left} мл — можно добить одним стаканом.")

    # Советы по калориям
    if cal_left >= 500:
        tips.append("🍽️ По калориям ещё большой запас. Если голоден — выбери белок + овощи + крупу.")
    elif 100 < cal_left < 500:
        tips.append("🍽️ Осталось немного калорий — подойдёт лёгкий перекус: йогурт/творог/фрукты/овощи.")
    else:
        tips.append(
            "🍽️ По цели калорий почти в ноль. Если хочешь поесть — лучше низкокалорийное (овощи, белок)."
        )

    await message.answer("Рекомендации на сегодня:\n" + "\n".join("— " + t for t in tips))
    await show_menu_for_user(message, session_factory)
