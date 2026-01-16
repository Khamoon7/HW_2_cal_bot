from __future__ import annotations

import aiohttp
import asyncio


async def get_temperature_c(city: str, api_key: str) -> float | None:
    """
    Получает текущую температуру воздуха в градусах Цельсия для указанного города
    через OpenWeather API.

    Возвращает:
    - float — температура в °C, если запрос успешен;
    - None — если город не задан, API вернул ошибку или произошла сетевая проблема.
    """
    if not city:
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "ru",
    }

    # Таймаут ограничиваем, чтобы бот не зависал
    timeout = aiohttp.ClientTimeout(total=6, connect=3, sock_read=3)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                main = data.get("main", {})
                temp = main.get("temp")

                return float(temp) if temp is not None else None

    except (aiohttp.ClientError, asyncio.TimeoutError):
        # Сеть / таймаут / DNS и т.п.
        return None
    except Exception:
        # Любые неожиданные ошибки не должны ломать основной сценарий
        return None
