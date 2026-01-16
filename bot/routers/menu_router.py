from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.keyboards import kb_plot, kb_water_quick
from bot.menu import hide_menu
from bot.routers.food import FoodFSM
from bot.routers.profile import start_profile_flow
from bot.routers.progress import check_progress
from bot.routers.recommendations import recommend
from bot.routers.workout import WorkoutFSM
from bot.utils.ui import show_menu_for_user

router = Router()


@router.message(F.text == "Создать профиль")
async def m_create_profile(message: Message, state: FSMContext) -> None:
    """
    Запуск заполнения профиля (для новых пользователей).
    """
    await message.answer("Ок, настраиваем профиль 👇", reply_markup=hide_menu())
    await start_profile_flow(message, state)


@router.message(F.text == "Профиль")
async def m_profile(message: Message, state: FSMContext) -> None:
    """
    Повторный запуск заполнения/редактирования профиля.
    """
    await message.answer("Профиль 👇", reply_markup=hide_menu())
    await start_profile_flow(message, state)


@router.message(F.text == "Прогресс")
async def m_progress(message: Message, session_factory: async_sessionmaker) -> None:
    """
    Показать текущий прогресс пользователя.
    """
    await check_progress(message, session_factory)


@router.message(F.text == "Вода")
async def m_water(message: Message) -> None:
    """
    Быстрый лог воды: предлагаем варианты в inline-кнопках.
    """
    await message.answer("Сколько воды добавить?", reply_markup=hide_menu())
    await message.answer("Выбери вариант:", reply_markup=kb_water_quick())


@router.message(F.text == "Еда")
async def m_food(message: Message, state: FSMContext) -> None:
    """
    Запуск сценария логирования еды (FSM).
    """
    await message.answer(
        "Введите название продукта.\n\n"
        "Как вводить:\n"
        "— По одному продукту за раз (например: банан, овсянка, chicken breast).\n"
        "— Можно на русском или на английском.\n"
        "— Я покажу несколько вариантов - выбери самый подходящий.\n\n"
        "Важно: на английском обычно точнее (русский запрос я могу автоматически перевести и искать уже по переводу).",
        reply_markup=hide_menu(),
    )
    await state.set_state(FoodFSM.query)


@router.message(F.text == "Тренировка")
async def m_workout(message: Message, state: FSMContext) -> None:
    """
    Запуск сценария логирования тренировки (FSM).
    """
    await message.answer("Введите тип тренировки (например бег):", reply_markup=hide_menu())
    await state.set_state(WorkoutFSM.type_)


@router.message(F.text == "Графики")
async def m_plots(message: Message) -> None:
    """
    Выбор периода для построения графиков.
    """
    await message.answer("Что построить?", reply_markup=hide_menu())
    await message.answer("Выбери:", reply_markup=kb_plot())


@router.message(F.text == "Рекомендации")
async def m_rec(message: Message, session_factory: async_sessionmaker) -> None:
    """
    Показать рекомендации (питание/вода/нагрузка) на основе данных пользователя.
    """
    await recommend(message, session_factory)


@router.message(F.text == "Помощь")
async def m_help(message: Message, session_factory: async_sessionmaker) -> None:
    """
    Справка по боту + возврат в меню.
    """
    await message.answer(
        "Выбирай кнопками снизу.\n\n"
        "Если что, есть команды:\n"
        "/set_profile\n/log_water\n/log_food\n/log_workout\n/check_progress\n/plot\n/recommend"
    )
    await show_menu_for_user(message, session_factory)
