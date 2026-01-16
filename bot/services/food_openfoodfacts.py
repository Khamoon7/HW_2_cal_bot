from __future__ import annotations

import asyncio
import aiohttp


async def search_openfoodfacts(query: str, limit: int = 5) -> list[dict]:
    """
    Поиск продукта в OpenFoodFacts.

    Возвращает список словарей вида:
      {
        "name": str,
        "kcal_per_100g": float | None,
      }

    Если API не отвечает или данных нет - возвращает пустой список.
    """
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "action": "process",
        "search_terms": query,
        "json": "true",
        "page_size": str(limit),
    }

    # Таймауты, чтобы бот не зависал
    timeout = aiohttp.ClientTimeout(total=6, connect=3, sock_read=3)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as r:
                if r.status != 200:
                    return []
                data = await r.json()
    except (asyncio.TimeoutError, aiohttp.ClientError):
        # Проблемы с сетью / таймаут
        return []
    except Exception:
        # Любые неожиданные ошибки не должны ронять хэндлер
        return []

    products = data.get("products", []) or []
    results: list[dict] = []

    for p in products[:limit]:
        name = p.get("product_name") or p.get("generic_name") or "Без названия"
        nutr = p.get("nutriments", {}) or {}
        kcal100 = nutr.get("energy-kcal_100g")

        try:
            kcal100 = float(kcal100) if kcal100 is not None else None
        except Exception:
            kcal100 = None

        results.append(
            {
                "name": name,
                "kcal_per_100g": kcal100,
            }
        )

    return results
