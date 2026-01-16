import time
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger("bot")


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования времени обработки каждого апдейта Telegram.
    """

    async def __call__(self, handler, event: TelegramObject, data: dict):
        """
        Оборачивает обработчик события и логирует latency выполнения.
        """
        start_ts = time.time()

        try:
            return await handler(event, data)
        finally:
            latency_ms = (time.time() - start_ts) * 1000.0

            # Тип апдейта (Message, CallbackQuery и т.п.)
            update = data.get("event_update")
            update_type = type(update).__name__ if update else "unknown"

            logger.info(
                "update=%s latency_ms=%.1f",
                update_type,
                latency_ms,
            )