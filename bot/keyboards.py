from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_sex() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора пола пользователя.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="Мужчина", callback_data="sex:male")
    builder.button(text="Женщина", callback_data="sex:female")
    builder.adjust(2)

    return builder.as_markup()


def kb_goal() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора цели пользователя.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="Похудение", callback_data="goal:lose")
    builder.button(text="Поддержание", callback_data="goal:maintain")
    builder.button(text="Набор массы", callback_data="goal:gain")
    builder.adjust(1)

    return builder.as_markup()


def kb_yesno(prefix: str) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура «Да / Нет».

    prefix используется для формирования callback_data:
    <prefix>:yes / <prefix>:no
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="Да", callback_data=f"{prefix}:yes")
    builder.button(text="Нет", callback_data=f"{prefix}:no")
    builder.adjust(2)

    return builder.as_markup()


def kb_water_quick() -> InlineKeyboardMarkup:
    """
    Быстрый выбор объёма выпитой воды.
    """
    builder = InlineKeyboardBuilder()

    # Быстрые варианты объёма
    for ml in (100, 200, 300, 500):
        builder.button(text=f"+{ml} мл", callback_data=f"water_add:{ml}")

    # Ручной ввод
    builder.button(text="Ввести вручную", callback_data="water_add:custom")

    builder.adjust(2, 2, 1)
    return builder.as_markup()


def kb_intensity() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора интенсивности тренировки.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="Лёгкая", callback_data="int:low")
    builder.button(text="Средняя", callback_data="int:medium")
    builder.button(text="Высокая", callback_data="int:high")
    builder.adjust(1)

    return builder.as_markup()


def kb_food_pick(items: list[dict]) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора продукта из списка.

    items: [
        {"name": str, "kcal_per_100g": float | None, "source": str},
        ...
    ]

    callback_data:
      - food_pick:<index>
      - food_pick:manual
    """
    builder = InlineKeyboardBuilder()

    for i, item in enumerate(items):
        kcal = item.get("kcal_per_100g")
        kcal_txt = "?" if kcal is None else f"{kcal:g}"

        source = item.get("source", "")
        title = (item.get("name") or "Без названия").strip()

        # Ограничение длины текста кнопки
        if len(title) > 35:
            title = title[:35] + "…"

        builder.button(
            text=f"{title} — {kcal_txt} ккал/100г ({source})",
            callback_data=f"food_pick:{i}",
        )

    # Ручной ввод калорийности
    builder.button(
        text="Ввести вручную (ккал/100г)",
        callback_data="food_pick:manual",
    )

    builder.adjust(1)
    return builder.as_markup()


def kb_plot() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора периода для графиков.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="Графики за 7 дней", callback_data="plot:week")
    builder.button(text="Графики за сегодня", callback_data="plot:day")
    builder.adjust(1)

    return builder.as_markup()
