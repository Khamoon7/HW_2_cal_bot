from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# Enums (справочники)
class Sex(str, enum.Enum):
    """Пол пользователя."""
    male = "male"
    female = "female"


class Goal(str, enum.Enum):
    """Цель пользователя по питанию/весу."""
    lose = "lose" # похудение
    maintain = "maintain" # поддержание
    gain = "gain" # набор


class Intensity(str, enum.Enum):
    """Интенсивность тренировки."""
    low = "low"
    medium = "medium"
    high = "high"


# Таблицы БД
class User(Base):
    """
    Пользователь Telegram.

    tg_id - Telegram user id (уникальный).
    profile_completed - признак заполненного профиля, чтобы показывать полное меню.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Telegram id пользователя (важно: именно user.id, не bot.id)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    # Параметры профиля (могут быть пустыми до заполнения)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activity_min_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)

    goal: Mapped[str | None] = mapped_column(String(16), nullable=True)
    calorie_goal_manual: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Флаг того, что профиль заполнен и можно показывать полное меню
    profile_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Дата создания пользователя в БД
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь: агрегаты по дням (вода/калории)
    days: Mapped[list["DayStat"]] = relationship(back_populates="user")


class DayStat(Base):
    """
    Агрегированная статистика пользователя за день.

    Уникальность: один user_id + один day.
    """
    __tablename__ = "day_stats"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)

    water_ml: Mapped[int] = mapped_column(Integer, default=0)
    calories_in: Mapped[float] = mapped_column(Float, default=0.0)
    calories_out: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped["User"] = relationship(back_populates="days")


class FoodCustom(Base):
    """
    Кастомные продукты (fallback, когда внешние API не помогли).

    kcal_per_100g — обязательное поле.
    """
    __tablename__ = "food_custom"
    __table_args__ = (UniqueConstraint("name", name="uq_food_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256))
    kcal_per_100g: Mapped[float] = mapped_column(Float)


class FoodLog(Base):
    """
    Лог приёмов пищи (события), которые затем суммируются в DayStat.calories_in.
    """
    __tablename__ = "food_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)

    name: Mapped[str] = mapped_column(String(256))
    grams: Mapped[float] = mapped_column(Float)
    kcal: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkoutLog(Base):
    """
    Лог тренировок (события), которые затем суммируются в DayStat.calories_out.
    """
    __tablename__ = "workout_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)

    workout_type: Mapped[str] = mapped_column(String(64))
    minutes: Mapped[int] = mapped_column(Integer)
    intensity: Mapped[str] = mapped_column(String(16))
    kcal_burned: Mapped[float] = mapped_column(Float)
    extra_water_ml: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
