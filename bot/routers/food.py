from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import settings
from bot.db.models import FoodLog
from bot.db.repo import Repo
from bot.keyboards import kb_food_pick
from bot.menu import hide_menu
from bot.services.food_calorieninjas import search_calorieninjas
from bot.services.food_openfoodfacts import search_openfoodfacts
from bot.services.translate import maybe_translate_ru_to_en
from bot.utils.ui import show_menu_for_user

router = Router()


class FoodFSM(StatesGroup):
    """
    FSM для логирования еды:
    - query: ввод названия продукта
    - pick: выбор продукта из списка
    - manual_kcal100: ручной ввод ккал/100г
    - grams: ввод граммов и сохранение в БД
    """
    query = State()
    pick = State()
    grams = State()
    manual_kcal100 = State()


def _parse_float(text: str) -> float | None:
    """
    Безопасный парсинг float из текста (поддерживает запятую).
    """
    try:
        return float(text.replace(",", ".").strip())
    except Exception:
        return None


@router.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext) -> None:
    """
    Команда /log_food - запускает сценарий логирования еды.
    """
    await message.answer(
        "Напиши, что ты съел 🍽️\n\n"
        "Как вводить:\n"
        "— По одному продукту за раз (например: банан, овсянка, chicken breast).\n"
        "— Можно на русском или на английском.\n"
        "— Я покажу несколько вариантов - выбери самый подходящий.\n\n"
        "Важно: на английском обычно точнее (русский запрос я могу автоматически перевести и искать уже по переводу).",
        reply_markup=hide_menu(),
    )
    await state.set_state(FoodFSM.query)


@router.message(FoodFSM.query)
async def food_query(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker,
) -> None:
    """
    Шаг 1: принимаем строку запроса и собираем кандидатов из:
    1) локальной БД (FoodCustom)
    2) CalorieNinjas (при необходимости - через автоперевод)
    3) OpenFoodFacts (при необходимости - через автоперевод)

    Далее показываем inline-клавиатуру выбора (top-5) либо просим ввести ккал вручную.
    """
    query = (message.text or "").strip()
    if not query:
        await message.answer("Пусто. Напиши продукт, например: банан")
        return

    await state.update_data(query=query)

    # 1) Локальная БД (кастомные продукты)
    async with session_factory() as session:
        repo = Repo(session)
        custom = await repo.find_custom_food(query, limit=5)

    items: list[dict] = [
        {"name": c.name, "kcal_per_100g": c.kcal_per_100g, "source": "myDB"} for c in custom
    ]

    # 2) CalorieNinjas (по исходному запросу)
    cn = await search_calorieninjas(query, settings.calorieninjas_api_key, limit=5)
    for it in cn:
        items.append({"name": it["name"], "kcal_per_100g": it["kcal_per_100g"], "source": "CN"})

    # Если по-русски CN ничего не нашёл - пробуем перевести запрос на английский
    if len(cn) == 0:
        tr = await maybe_translate_ru_to_en(query, settings.translate_enabled)
        if tr:
            cn2 = await search_calorieninjas(tr, settings.calorieninjas_api_key, limit=5)
            for it in cn2:
                items.append({"name": it["name"], "kcal_per_100g": it["kcal_per_100g"], "source": "CN-en"})

        # 3) OpenFoodFacts (по исходному запросу)
        off = await search_openfoodfacts(query, limit=5)
        for it in off:
            items.append({"name": it["name"], "kcal_per_100g": it["kcal_per_100g"], "source": "OFF"})

        # Если OFF ничего не нашёл - пробуем перевод
        if len(off) == 0:
            tr = await maybe_translate_ru_to_en(query, settings.translate_enabled)
            if tr:
                off2 = await search_openfoodfacts(tr, limit=5)
                for it in off2:
                    items.append({"name": it["name"], "kcal_per_100g": it["kcal_per_100g"], "source": "OFF-en"})

    # Дедупликация по имени (без учёта регистра) + ограничение топ-5
    cleaned: list[dict] = []
    seen: set[str] = set()
    for it in items:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(it)

    cleaned = cleaned[:5]
    await state.update_data(items=cleaned)

    # Если вариантов нет - просим ввести ккал/100г вручную и сохраним в FoodCustom
    if not cleaned:
        await state.set_state(FoodFSM.manual_kcal100)
        await message.answer(
            "Я не нашёл надёжных данных по этому продукту 😕\n\n"
            "Введи калорийность в **ккал на 100 г** -\n"
            "Я сохраню продукт в нашу базу, и в следующий раз он будет находиться автоматически."
        )
        return

    # Переходим к выбору продукта
    await state.set_state(FoodFSM.pick)
    await message.answer(
        "Выбери продукт из списка или введи вручную:",
        reply_markup=kb_food_pick(cleaned),
    )


@router.callback_query(FoodFSM.pick, F.data.startswith("food_pick:"))
async def food_pick(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Шаг 2: пользователь выбрал продукт из inline-кнопок либо выбрал ручной ввод.
    """
    idx = callback.data.split(":", 1)[1]
    data = await state.get_data()

    # Ручной ввод ккал/100г
    if idx == "manual":
        await state.set_state(FoodFSM.manual_kcal100)
        await callback.message.answer("Введи калорийность (ккал на 100 г). Например 89:")
        await callback.answer()
        return

    # Выбор из списка
    try:
        i = int(idx)
    except Exception:
        await callback.message.answer("Неверный выбор. Попробуй снова: Еда")
        await state.clear()
        await callback.answer()
        return

    items = data.get("items", [])
    if i < 0 or i >= len(items):
        await callback.message.answer("Неверный выбор. Попробуй снова: Еда")
        await state.clear()
        await callback.answer()
        return

    picked = items[i]
    await state.update_data(picked=picked)
    await state.set_state(FoodFSM.grams)

    kcal = picked.get("kcal_per_100g")
    kcal_txt = "?" if kcal is None else f"{float(kcal):g}"
    await callback.message.answer(f"{picked['name']} — {kcal_txt} ккал/100г.\nСколько грамм ты съел?")
    await callback.answer()


@router.message(FoodFSM.manual_kcal100)
async def food_manual_kcal100(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker,
) -> None:
    """
    Шаг 2 (альтернатива): ручной ввод ккал/100г.
    Сохраняем продукт в FoodCustom и переходим к вводу граммов.
    """
    kcal100 = _parse_float(message.text or "")
    if kcal100 is None or kcal100 <= 0 or kcal100 > 2000:
        await message.answer("Введи ккал/100г (1..2000), например 89.")
        return

    data = await state.get_data()
    query = data.get("query", "Продукт")

    async with session_factory() as session:
        repo = Repo(session)
        await repo.upsert_custom_food(query, float(kcal100))
        await session.commit()

    await state.update_data(picked={"name": query, "kcal_per_100g": float(kcal100), "source": "myDB"})
    await state.set_state(FoodFSM.grams)
    await message.answer(f"Ок ✅ {query} — {kcal100:g} ккал/100г.\nСколько грамм ты съел?")


@router.message(FoodFSM.grams)
async def food_grams(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker,
) -> None:
    """
    Шаг 3: ввод граммов и запись:
    - FoodLog (событие)
    - DayStat.calories_in (агрегация за день)
    """
    grams = _parse_float(message.text or "")
    if grams is None or grams <= 0 or grams > 5000:
        await message.answer("Введи граммы (1..5000), например 150.")
        return

    data = await state.get_data()
    picked = data.get("picked")
    if not picked:
        await message.answer("Что-то пошло не так. Нажми Еда ещё раз.")
        await state.clear()
        await show_menu_for_user(message, session_factory)
        return

    kcal100 = picked.get("kcal_per_100g")
    if kcal100 is None:
        await message.answer("У этого варианта нет калорийности. Выбери другой или введи вручную.")
        await state.clear()
        await show_menu_for_user(message, session_factory)
        return

    kcal = float(kcal100) * float(grams) / 100.0

    async with session_factory() as session:
        repo = Repo(session)
        user = await repo.get_or_create_user(message.from_user.id)

        # Агрегация по текущему дню (локальная дата)
        st = await repo.get_or_create_day(user.id, date.today())
        st.calories_in += float(kcal)

        # Событие (лог приёма пищи)
        session.add(
            FoodLog(
                user_id=user.id,
                day=date.today(),
                name=picked["name"],
                grams=float(grams),
                kcal=float(kcal),
            )
        )

        await session.commit()

    await message.answer(f"Записано ✅ {picked['name']}: {grams:g} г → {kcal:.1f} ккал.")
    await state.clear()
    await show_menu_for_user(message, session_factory)