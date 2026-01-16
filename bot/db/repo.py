from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DayStat, FoodCustom, User


class Repo:
    """
    Репозиторий для доступа к БД через AsyncSession.

    Инкапсулирует типовые операции:
    - get_or_create пользователя
    - get_or_create дневной статистики
    - upsert и поиск кастомных продуктов
    """

    def __init__(self, session: AsyncSession):
        # AsyncSession, передаётся извне (через session_factory)
        self.s = session

    async def get_or_create_user(self, tg_id: int) -> User:
        """
        Возвращает пользователя по tg_id или создаёт нового.
        """
        res = await self.s.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user is not None:
            return user

        # Создание пользователя при первом обращении
        user = User(tg_id=tg_id)
        self.s.add(user)

        await self.s.commit()
        await self.s.refresh(user)
        return user

    async def get_or_create_day(self, user_id: int, day: date) -> DayStat:
        """
        Возвращает агрегированную дневную статистику или создаёт новую.
        """
        res = await self.s.execute(
            select(DayStat).where(DayStat.user_id == user_id, DayStat.day == day)
        )
        stat = res.scalar_one_or_none()
        if stat is not None:
            return stat

        # Создаём запись за день, если её ещё нет
        stat = DayStat(user_id=user_id, day=day)
        self.s.add(stat)

        await self.s.commit()
        await self.s.refresh(stat)
        return stat

    async def upsert_custom_food(self, name: str, kcal_per_100g: float) -> FoodCustom:
        """
        Создаёт кастомный продукт или обновляет kcal_per_100g, если продукт уже есть.
        """
        res = await self.s.execute(select(FoodCustom).where(FoodCustom.name == name))
        item = res.scalar_one_or_none()

        if item is not None:
            # Обновление существующей записи
            item.kcal_per_100g = kcal_per_100g
            await self.s.commit()
            await self.s.refresh(item)
            return item

        # Создание новой записи
        item = FoodCustom(name=name, kcal_per_100g=kcal_per_100g)
        self.s.add(item)

        await self.s.commit()
        await self.s.refresh(item)
        return item

    async def find_custom_food(self, query_str: str, limit: int = 5) -> list[FoodCustom]:
        """
        Ищет кастомные продукты по подстроке в названии.
        """
        res = await self.s.execute(
            select(FoodCustom)
            .where(FoodCustom.name.ilike(f"%{query_str}%"))
            .limit(limit)
        )
        return list(res.scalars().all())
