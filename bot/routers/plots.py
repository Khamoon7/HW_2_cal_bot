from __future__ import annotations

from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import settings
from bot.db.models import DayStat
from bot.db.repo import Repo
from bot.keyboards import kb_plot
from bot.menu import hide_menu
from bot.services.nutrition import apply_goal, bmr_mifflin, tdee_from_bmr, water_goal_ml
from bot.services.plots import plot_day, plot_week
from bot.services.weather import get_temperature_c
from bot.utils.ui import show_menu_for_user

router = Router()


@router.message(Command("plot"))
async def plot_menu(message: Message) -> None:
    """
    Команда /plot - показывает меню выбора графика.
    """
    await message.answer("Что построить?", reply_markup=hide_menu())
    await message.answer("Выбери:", reply_markup=kb_plot())


@router.callback_query(F.data == "plot:week")
async def plot_week_cb(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    """
    Callback: построить графики за последние 7 дней и отправить картинку.
    """
    img = await _build_week_plot(session_factory, tg_id=callback.from_user.id)

    await callback.message.answer_photo(
        BufferedInputFile(img, filename="week.png"),
        caption="Графики за 7 дней",
    )
    await show_menu_for_user(callback.message, session_factory, tg_id=callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "plot:day")
async def plot_day_cb(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    """
    Callback: построить прогресс за сегодня (вода + калории) и отправить картинку.
    """
    progress = await _get_today_progress_dict(session_factory, tg_id=callback.from_user.id)
    if progress is None:
        await callback.message.answer("Сначала создай профиль: Создать профиль")
        await show_menu_for_user(callback.message, session_factory, tg_id=callback.from_user.id)
        await callback.answer()
        return

    img = plot_day(progress)
    await callback.message.answer_photo(
        BufferedInputFile(img, filename="day.png"),
        caption="Прогресс за сегодня",
    )
    await show_menu_for_user(callback.message, session_factory, tg_id=callback.from_user.id)
    await callback.answer()


async def _build_week_plot(session_factory: async_sessionmaker, tg_id: int) -> bytes:
    """
    Собирает данные за последние 7 дней из DayStat и строит общий недельный график.
    Возвращает PNG в bytes.
    """
    async with session_factory() as session:
        repo = Repo(session)
        user = await repo.get_or_create_user(tg_id)

        # Даты от (сегодня-6) до сегодня (включительно), в хронологическом порядке
        days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]

        # Забираем статистику за диапазон
        res = await session.execute(
            select(DayStat).where(
                DayStat.user_id == user.id,
                DayStat.day >= days[0],
                DayStat.day <= days[-1],
            )
        )
        stats = {st.day: st for st in res.scalars().all()}

        # Данные по каждому дню (если записи нет - ставим 0)
        water: list[int] = []
        cal_in: list[float] = []
        cal_out: list[float] = []

        for d in days:
            st = stats.get(d)
            water.append(int(st.water_ml) if st else 0)
            cal_in.append(float(st.calories_in) if st else 0.0)
            cal_out.append(float(st.calories_out) if st else 0.0)

    return plot_week(days, water, cal_in, cal_out)


async def _get_today_progress_dict(
    session_factory: async_sessionmaker,
    tg_id: int,
) -> dict | None:
    """
    Собирает «прогресс за сегодня» для plot_day().

    Возвращает None, если профиль пользователя заполнен не полностью
    (нельзя корректно посчитать цели воды/калорий).
    """
    async with session_factory() as session:
        repo = Repo(session)
        user = await repo.get_or_create_user(tg_id)

        # Проверка, что профиль заполнен (без этого цели не считаем)
        if not (
            user.sex
            and user.weight_kg
            and user.height_cm
            and user.age
            and user.activity_min_per_day is not None
            and user.city
            and user.goal
        ):
            return None

        # Берём/создаём дневную статистику за сегодня
        st = await repo.get_or_create_day(user.id, date.today())

        # Цель по воде зависит от веса, активности и температуры (если есть ключ OpenWeather)
        temp = (
            await get_temperature_c(user.city, settings.openweather_api_key)
            if settings.openweather_api_key
            else None
        )
        w_goal = water_goal_ml(float(user.weight_kg), int(user.activity_min_per_day), temp)

        # Цель по калориям: ручная (если задана) иначе считаем через BMR -> TDEE -> goal
        if user.calorie_goal_manual is not None:
            cal_goal = int(user.calorie_goal_manual)
        else:
            act = int(user.activity_min_per_day)
            level = "low" if act < 30 else ("medium" if act < 60 else "high")

            bmr = bmr_mifflin(user.sex, float(user.weight_kg), float(user.height_cm), int(user.age))
            tdee = tdee_from_bmr(bmr, level)
            cal_goal = int(apply_goal(tdee, user.goal))

    return {
        "water_ml": int(st.water_ml),
        "water_goal_ml": int(w_goal),
        "calories_in": float(st.calories_in),
        "calories_out": float(st.calories_out),
        "calorie_goal": int(cal_goal),
    }
