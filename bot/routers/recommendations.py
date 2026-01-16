from __future__ import annotations

import random
from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import settings
from bot.db.repo import Repo
from bot.menu import hide_menu
from bot.services.nutrition import (
    apply_goal,
    bmr_mifflin,
    tdee_from_bmr,
    water_goal_ml,
)
from bot.services.weather import get_temperature_c
from bot.utils.ui import show_menu_for_user

router = Router()


@router.message(Command("recommend"))
async def recommend(message: Message, session_factory: async_sessionmaker) -> None:
    """
    Команда /recommend - выдаёт рекомендации на сегодня:
    - вода (выпито / цель / осталось)
    - калории (сколько осталось/перебор)
    - активность
    - конкретная идея еды (рандом, но стабильно в рамках дня)
    """
    await message.answer("Смотрю, как у тебя дела сегодня 👀", reply_markup=hide_menu())

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
            await message.answer("Сначала заполни профиль - так рекомендации будут точнее 🙌")
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

        # Вода
        water_goal = water_goal_ml(
            float(user.weight_kg),
            int(user.activity_min_per_day),
            temp,
        )
        water_drunk = int(st.water_ml)
        water_left = max(0, int(water_goal) - water_drunk)

        # Цель по калориям: ручная (если задана) иначе рассчитываем
        if user.calorie_goal_manual is not None:
            cal_goal = int(user.calorie_goal_manual)
        else:
            act = int(user.activity_min_per_day)
            level = "low" if act < 30 else ("medium" if act < 60 else "high")

            bmr = bmr_mifflin(
                user.sex,
                float(user.weight_kg),
                float(user.height_cm),
                int(user.age),
            )
            tdee = tdee_from_bmr(bmr, level)
            cal_goal = int(apply_goal(tdee, user.goal))

        # Текущие значения
        cal_in = float(st.calories_in)
        cal_out = float(st.calories_out)

        # Остаток по еде:
        # 1) по "чистому" лимиту
        cal_left_plain = cal_goal - int(cal_in)
        # 2) с учётом активности
        cal_left_with_activity = cal_goal + int(cal_out) - int(cal_in)

        # Флаг активности
        trained_today = cal_out >= 30.0  # небольшой порог, чтобы шум не считался тренировкой

    # Рандомные идеи еды
    meal_big = [
        "куриную грудку + бурый рис + овощи",
        "индейку + гречку + салат",
        "омлет 2–3 яйца + овощи + тост цельнозерновой",
        "тунец/лосось + картофель/рис + овощи",
        "творог 5% + ягоды + орехи (немного)",
    ]
    meal_mid = [
        "йогурт/кефир + банан",
        "творог + ягоды",
        "2 яйца + овощи",
        "овсянку (небольшая порция) + фрукты",
        "протеиновый батончик (если ок по составу)",
    ]
    meal_low = [
        "овощной салат + тунец/курица",
        "огурцы/помидоры + 150–200 г нежирного белка",
        "суп/бульон + овощи",
        "яблоко/груша",
        "морковь/сельдерей",
    ]

    # Делаем выбор идей "стабильным" на день (чтобы не прыгало каждое открытие)
    seed_base = f"{message.from_user.id}:{date.today().isoformat()}"
    rnd = random.Random(seed_base)

    lines: list[str] = []

    # Вода
    if water_left > 0:
        if water_left >= 600:
            lines.append(f"💧 По воде ещё осталось {water_left} мл. Самое время выпить стакан-два.")
        else:
            lines.append(f"💧 Осталось совсем немного - {water_left} мл, и норма будет закрыта.")
    else:
        lines.append("💧 С водой сегодня всё отлично, норма выполнена ✅")

    # Калории (сколько осталось / перебор)
    if cal_left_plain >= 0:
        lines.append(f"🍽️ Еда: съедено {cal_in:.0f} из {cal_goal} ккал. Осталось ~{cal_left_plain} ккал.")
    else:
        lines.append(
            f"🍽️ Еда: съедено {cal_in:.0f} при цели {cal_goal} ккал - перебор ~{abs(cal_left_plain)} ккал."
        )

    # Активность / тренировка
    if trained_today:
        lines.append(
            f"🔥 Отлично поработал сегодня - тренировка была, "
            f"сжёг около {int(cal_out)} ккал."
        )
        if cal_left_with_activity > 0:
            lines.append(f"Можно спокойно добрать ещё ~{cal_left_with_activity} ккал.")
    else:
        lines.append(
            "🏃 Сегодня без тренировки. "
            "Если найдёшь 15–25 минут - лёгкая активность сейчас будет в самый раз."
        )

    # Конкретная идея, что поесть (рандом)
    if cal_left_with_activity >= 500:
        idea = rnd.choice(meal_big)
        lines.append(f"🥙 Идея: съешь {idea}.")
    elif 150 <= cal_left_with_activity < 500:
        idea = rnd.choice(meal_mid)
        lines.append(f"🥙 Идея: {idea}.")
    else:
        idea = rnd.choice(meal_low)
        lines.append(f"🥙 Идея (лёгкий вариант): {idea}.")

    await message.answer("Вот что у тебя на сегодня:\n\n" + "\n".join(lines))
    await show_menu_for_user(message, session_factory)
