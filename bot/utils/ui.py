from __future__ import annotations

from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.repo import Repo
from bot.menu import menu_full, menu_new_user


def has_profile(u) -> bool:
    """
    Возвращает True, если у пользователя заполнен профиль.

    Используем getattr, чтобы функция не падала, если поле отсутствует
    (например, при частично заполненной модели/DTO).
    """
    return bool(getattr(u, "profile_completed", False))


async def show_menu_for_user(
    message: Message,
    session_factory: async_sessionmaker,
    text_msg: str = "Меню 👇",
    *,
    tg_id: int | None = None,
) -> None:
    """
    Показывает пользователю меню (новичок/полное) в зависимости от наличия профиля.

    tg_id:
      - если передан явно — используем его;
      - иначе берём message.from_user.id (и только если это не бот).
    """
    # Определяем фактический tg_id
    actual_tg_id = tg_id
    if actual_tg_id is None and message.from_user and not message.from_user.is_bot:
        actual_tg_id = message.from_user.id

    async with session_factory() as session:
        repo = Repo(session)

        # Создаём пользователя при первом обращении (по tg_id)
        user = await repo.get_or_create_user(actual_tg_id)

        # Выбираем нужную клавиатуру в зависимости от профиля
        keyboard = menu_full() if has_profile(user) else menu_new_user()

    await message.answer(text_msg, reply_markup=keyboard)
