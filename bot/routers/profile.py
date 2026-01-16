from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.repo import Repo
from bot.keyboards import kb_goal, kb_sex, kb_yesno
from bot.menu import hide_menu
from bot.services.nutrition import apply_goal, bmr_mifflin, tdee_from_bmr
from bot.utils.ui import show_menu_for_user

router = Router()


class ProfileFSM(StatesGroup):
    """
    FSM заполнения профиля пользователя:
    - sex -> weight -> height -> age -> activity -> city -> goal -> (manual calories)
    """
    sex = State()
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()
    goal = State()
    manual_cal = State()
    manual_cal_value = State()


def _parse_float(text: str) -> float | None:
    """
    Парсинг float из строки (поддерживает запятую).
    """
    try:
        return float(text.replace(",", ".").strip())
    except Exception:
        return None


def _parse_int(text: str) -> int | None:
    """
    Парсинг int из строки.
    """
    try:
        return int(text.strip())
    except Exception:
        return None


async def start_profile_flow(message: Message, state: FSMContext) -> None:
    """
    Запускает процесс заполнения профиля (с первого шага: выбор пола).
    """
    await state.set_state(ProfileFSM.sex)
    await message.answer(
        "Давай настроим профиль 👇\n"
        "Это нужно, чтобы я правильно считал калории и воду.\n\n"
        "Для начала - выбери пол:",
        reply_markup=kb_sex(),
    )


@router.message(Command("set_profile"))
async def set_profile(message: Message, state: FSMContext) -> None:
    """
    Команда /set_profile - начать заполнение профиля.
    """
    await message.answer("Ок, настраиваем профиль 👇", reply_markup=hide_menu())
    await start_profile_flow(message, state)


@router.callback_query(ProfileFSM.sex, F.data.startswith("sex:"))
async def pick_sex(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Шаг 1: выбор пола.
    """
    sex = callback.data.split(":", 1)[1]
    await state.update_data(sex=sex)

    await state.set_state(ProfileFSM.weight)
    await callback.message.answer("Сколько вес? (кг)\nНапример: 80")
    await callback.answer()


@router.message(ProfileFSM.weight)
async def pick_weight(message: Message, state: FSMContext) -> None:
    """
    Шаг 2: ввод веса.
    """
    w = _parse_float(message.text or "")
    if w is None or w <= 0 or w > 500:
        await message.answer("Не понял вес 😅\nНапиши число в кг, например: 80")
        return

    await state.update_data(weight=w)
    await state.set_state(ProfileFSM.height)
    await message.answer("Сколько рост? (см)\nНапример: 184")


@router.message(ProfileFSM.height)
async def pick_height(message: Message, state: FSMContext) -> None:
    """
    Шаг 3: ввод роста.
    """
    h = _parse_float(message.text or "")
    if h is None or h <= 0 or h > 300:
        await message.answer("Не понял рост 😅\nНапиши в см, например: 184")
        return

    await state.update_data(height=h)
    await state.set_state(ProfileFSM.age)
    await message.answer("Сколько лет?\nНапример: 26")


@router.message(ProfileFSM.age)
async def pick_age(message: Message, state: FSMContext) -> None:
    """
    Шаг 4: ввод возраста.
    """
    a = _parse_int(message.text or "")
    if a is None or a <= 0 or a > 120:
        await message.answer("Не понял возраст 😅\nНапиши целое число, например: 26")
        return

    await state.update_data(age=a)
    await state.set_state(ProfileFSM.activity)
    await message.answer("Сколько минут активности у тебя в день?\nНапример: 45")


@router.message(ProfileFSM.activity)
async def pick_activity(message: Message, state: FSMContext) -> None:
    """
    Шаг 5: ввод активности (минут в день).
    """
    act = _parse_int(message.text or "")
    if act is None or act < 0 or act > 1440:
        await message.answer("Введите минуты активности в день (0..1440), например 45.")
        return

    await state.update_data(activity=act)
    await state.set_state(ProfileFSM.city)
    await message.answer("В каком городе ты находишься?\nНапример: Москва)")


@router.message(ProfileFSM.city)
async def pick_city(message: Message, state: FSMContext) -> None:
    """
    Шаг 6: ввод города (используется для погоды и цели по воде).
    """
    city = (message.text or "").strip()
    if not city:
        await message.answer("Город пустой 🙃\nНапиши, например: Москва")
        return

    await state.update_data(city=city)
    await state.set_state(ProfileFSM.goal)
    await message.answer("Какая твоя цель?", reply_markup=kb_goal())


@router.callback_query(ProfileFSM.goal, F.data.startswith("goal:"))
async def pick_goal(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Шаг 7: выбор цели (похудение/поддержание/набор).
    """
    goal = callback.data.split(":", 1)[1]
    await state.update_data(goal=goal)

    await state.set_state(ProfileFSM.manual_cal)
    await callback.message.answer(
        "Хочешь задать цель по калориям вручную?",
        reply_markup=kb_yesno("manualcal"),
    )
    await callback.answer()


@router.callback_query(ProfileFSM.manual_cal, F.data.startswith("manualcal:"))
async def pick_manual(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker,
) -> None:
    """
    Шаг 8: спросили, задаёт ли пользователь калории вручную.
    """
    ans = callback.data.split(":", 1)[1]
    if ans == "yes":
        await state.set_state(ProfileFSM.manual_cal_value)
        await callback.message.answer("Введи цель по калориям (ккал/день), например 2300:")
    else:
        await state.update_data(calorie_goal_manual=None)
        await _save_profile_and_finish(
            callback.message,
            state,
            session_factory,
            tg_id=callback.from_user.id,
        )

    await callback.answer()


@router.message(ProfileFSM.manual_cal_value)
async def manual_cal_value(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker,
) -> None:
    """
    Шаг 8 (альтернатива): ввод ручной цели по калориям.
    """
    val = _parse_int(message.text or "")
    if val is None or val < 800 or val > 8000:
        await message.answer("Введи нормальное число калорий (800..8000), например 2300.")
        return

    await state.update_data(calorie_goal_manual=val)
    await _save_profile_and_finish(message, state, session_factory, tg_id=message.from_user.id)


async def _save_profile_and_finish(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker,
    *,
    tg_id: int | None = None,
) -> None:
    """
    Сохраняет профиль в БД, выводит итоговое сообщение и возвращает пользователя в меню.
    """
    data = await state.get_data()

    # tg_id либо передали явно, либо берём из message.from_user.id
    actual_tg_id = tg_id if tg_id is not None else message.from_user.id

    async with session_factory() as session:
        repo = Repo(session)
        user = await repo.get_or_create_user(actual_tg_id)

        # Заполняем поля профиля
        user.sex = data["sex"]
        user.weight_kg = float(data["weight"])
        user.height_cm = float(data["height"])
        user.age = int(data["age"])
        user.activity_min_per_day = int(data["activity"])
        user.city = data["city"]
        user.goal = data["goal"]
        user.calorie_goal_manual = data.get("calorie_goal_manual")
        user.profile_completed = True

        await session.commit()

        # Выводим пользователю итог (ручная цель или расчётная)
        if user.calorie_goal_manual is None:
            act = user.activity_min_per_day or 0
            level = "low" if act < 30 else ("medium" if act < 60 else "high")

            bmr = bmr_mifflin(user.sex, user.weight_kg, user.height_cm, user.age)
            tdee = tdee_from_bmr(bmr, level)
            cal_goal = apply_goal(tdee, user.goal)

            await message.answer(
                "Профиль сохранён ✅\n"
                f"Рассчитанная цель по калориям: ~{cal_goal} ккал/день."
            )
        else:
            await message.answer(
                "Профиль сохранён ✅\n"
                f"Ваша цель по калориям (ручная): {user.calorie_goal_manual} ккал/день."
            )

    await state.clear()
    await show_menu_for_user(message, session_factory, tg_id=actual_tg_id)
