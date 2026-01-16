from __future__ import annotations

async def maybe_translate_ru_to_en(text: str, enabled: bool) -> str | None:
    """
    Пытается перевести текст на английский язык.

    Возвращает:
    - переведённую строку (str), если перевод выполнен и отличается от исходного текста;
    - None, если перевод отключён, не нужен или произошла ошибка.

    Используется как fallback, например, при поиске еды в англоязычных API.
    """
    # Перевод глобально выключен через настройки
    if not enabled:
        return None

    try:
        # Ленивая загрузка, чтобы не тащить зависимость без надобности
        from deep_translator import GoogleTranslator

        translated = GoogleTranslator(source="auto", target="en").translate(text)

        # Возвращаем перевод только если он реально отличается от исходного текста
        if translated and translated.strip().lower() != text.strip().lower():
            return translated.strip()

        return None

    except Exception:
        # Любые ошибки перевода не должны ломать основной сценарий
        return None
