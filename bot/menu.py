from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def menu_new_user() -> ReplyKeyboardMarkup:
    """
    Клавиатура для нового пользователя без заполненного профиля.
    """
    builder = ReplyKeyboardBuilder()

    # Основные действия для старта
    builder.row(KeyboardButton(text="Создать профиль"))
    builder.row(KeyboardButton(text="Помощь"))

    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def menu_full() -> ReplyKeyboardMarkup:
    """
    Основная клавиатура для пользователя с заполненным профилем.
    """
    builder = ReplyKeyboardBuilder()

    # Профиль и прогресс
    builder.row(
        KeyboardButton(text="Профиль"),
        KeyboardButton(text="Прогресс"),
    )

    # Ежедневные действия
    builder.row(
        KeyboardButton(text="Вода"),
        KeyboardButton(text="Еда"),
        KeyboardButton(text="Тренировка"),
    )

    # Аналитика и помощь
    builder.row(
        KeyboardButton(text="Графики"),
        KeyboardButton(text="Рекомендации"),
        KeyboardButton(text="Помощь"),
    )

    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)

def hide_menu() -> ReplyKeyboardRemove:
    """
    Убирает reply-клавиатуру у пользователя.
    """
    return ReplyKeyboardRemove()
