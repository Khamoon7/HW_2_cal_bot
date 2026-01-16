import os

from dotenv import load_dotenv
from pydantic import BaseModel

# Загрузка переменных окружения из .env
load_dotenv()


class Settings(BaseModel):
    """
    Конфигурация приложения, загружаемая из переменных окружения.
    """
    # Telegram
    bot_token: str = os.getenv("BOT_TOKEN", "")

    # Внешние API
    openweather_api_key: str = os.getenv("OPENWEATHER_API_KEY", "")
    calorieninjas_api_key: str = os.getenv("CALORIENINJAS_API_KEY", "")

    # Приложение
    db_path: str = os.getenv("DB_PATH", "bot.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Фичефлаг автоперевода (0 / 1)
    translate_enabled: bool = os.getenv("TRANSLATE_ENABLED", "0") == "1"


# Singleton с настройками приложения
settings = Settings()

# Защита от запуска без токена бота
if not settings.bot_token:
    raise RuntimeError("BOT_TOKEN is empty. Put it into .env")
