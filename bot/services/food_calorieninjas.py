from __future__ import annotations

import asyncio
import aiohttp


async def search_calorieninjas(
    query: str,
    api_key: str,
    limit: int = 5,
) -> list[dict]:
    """
    Поиск продукта в CalorieNinjas.

    Возвращает список словарей вида:
      {
        "name": str,
        "kcal_per_100g": float | None,
        "raw": dict,
      }

    CalorieNinjas отдаёт калории на serving_size_g,
    здесь они приводятся к ккал на 100 г.
    """
    # Без API-ключа просто ничего не ищем
    if not api_key:
        return []

    url = "https://api.calorieninjas.com/v1/nutrition"
    headers = {"X-Api-Key": api_key}
    params = {"query": query}

    # Таймауты, чтобы бот не зависал
    timeout = aiohttp.ClientTimeout(total=6, connect=3, sock_read=3)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, params=params) as r:
                if r.status != 200:
                    return []
                data = await r.json()
    except (asyncio.TimeoutError, aiohttp.ClientError):
        # Проблемы с сетью / таймаут - считаем, что данных нет
        return []
    except Exception:
        # Любые неожиданные ошибки не должны ронять хэндлер
        return []

    items = data.get("items", []) or []
    results: list[dict] = []

    for it in items:
        name = it.get("name") or "Без названия"
        calories = it.get("calories")
        serving_g = it.get("serving_size_g") or 0

        kcal_per_100g: float | None = None
        try:
            if calories is not None and serving_g:
                kcal_per_100g = float(calories) / float(serving_g) * 100.0
        except Exception:
            kcal_per_100g = None

        results.append(
            {
                "name": name,
                "kcal_per_100g": kcal_per_100g,
                "raw": it,
            }
        )

    return results[:limit]
