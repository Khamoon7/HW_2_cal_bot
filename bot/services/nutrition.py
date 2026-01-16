from __future__ import annotations


def bmr_mifflin(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """
    Расчёт базового обмена (BMR) по формуле Mifflin–St Jeor.

    sex:
      - "male"   → +5
      - "female" → -161
    """
    s = 5 if sex == "male" else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + s


def tdee_from_bmr(bmr: float, activity_level: str) -> float:
    """
    Расчёт суточной нормы калорий (TDEE) на основе BMR и уровня активности.

    activity_level:
      - low → сидячий образ жизни
      - medium → умеренная активность
      - high → высокая активность
    """
    mapping = {
        "low": 1.2, # сидячий
        "medium": 1.375, # умеренный
        "high": 1.55, # высокий
    }
    return bmr * mapping.get(activity_level, 1.2)


def apply_goal(tdee: float, goal: str) -> int:
    """
    Корректировка TDEE под цель пользователя.

    goal:
      - lose  → дефицит ~15%
      - gain  → профицит ~10%
      - иначе → поддержание
    """
    if goal == "lose":
        return int(round(tdee * 0.85))
    if goal == "gain":
        return int(round(tdee * 1.10))
    return int(round(tdee))


def water_goal_ml(weight_kg: float, activity_min: int, temp_c: float | None) -> int:
    """
    Расчёт суточной цели по воде (мл).

    База: 30 мл на кг веса
    +500 мл за каждые 30 минут активности
    +500–1000 мл при высокой температуре воздуха
    """
    base = weight_kg * 30.0
    add_activity = (activity_min // 30) * 500

    add_temp = 0
    if temp_c is not None:
        if temp_c > 30:
            add_temp = 1000
        elif temp_c > 25:
            add_temp = 500

    return int(round(base + add_activity + add_temp))


def workout_extra_water(minutes: int) -> int:
    """
    Дополнительная вода после тренировки (мл).
    """
    return (minutes // 30) * 200


def workout_kcal(
    workout_type: str,
    minutes: int,
    intensity: str,
    weight_kg: float,
) -> float:
    """
    Расчёт сожжённых калорий по MET-модели.

    Формула:
      kcal = MET * 3.5 * weight(kg) / 200 * minutes

    MET зависит от типа тренировки и интенсивности.
    """
    # MET по типу тренировки
    base_met = {
        "бег": 9.8,
        "ходьба": 3.5,
        "велосипед": 7.5,
        "силовая": 6.0,
        "плавание": 8.0,
        "йога": 3.0,
    }.get(workout_type.lower(), 5.0)

    # Модификатор интенсивности
    mult = {
        "low": 0.85,
        "medium": 1.0,
        "high": 1.15,
    }.get(intensity, 1.0)

    met = base_met * mult
    return float(met * 3.5 * weight_kg / 200.0 * minutes)
