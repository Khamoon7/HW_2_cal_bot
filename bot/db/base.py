from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Базовый класс для всех ORM-моделей SQLAlchemy.

    Используется для объявления таблиц через declarative mapping.
    """
    pass
