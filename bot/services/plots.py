from __future__ import annotations

from io import BytesIO
from datetime import date

import matplotlib.pyplot as plt


def plot_week(
    dates: list[date],
    water: list[int],
    cal_in: list[float],
    cal_out: list[float],
) -> bytes:
    """
    Строит графики за 7 дней:
    - вода (мл)
    - калории (потреблено / сожжено)

    Возвращает PNG в bytes (удобно для отправки в Telegram как BufferedInputFile).
    """
    fig = plt.figure(figsize=(10, 7))

    # 1) Вода
    ax1 = fig.add_subplot(2, 1, 1)
    ax1.plot(dates, water)
    ax1.set_title("Вода (мл) — 7 дней")
    ax1.set_xlabel("Дата")
    ax1.set_ylabel("мл")
    ax1.grid(True)

    # 2) Калории
    ax2 = fig.add_subplot(2, 1, 2)
    ax2.plot(dates, cal_in, label="Потреблено")
    ax2.plot(dates, cal_out, label="Сожжено")
    ax2.set_title("Калории — 7 дней")
    ax2.set_xlabel("Дата")
    ax2.set_ylabel("ккал")
    ax2.grid(True)
    ax2.legend()

    # Сохраняем фигуру в память (bytes)
    buf = BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)

    buf.seek(0)
    return buf.getvalue()


def plot_day(progress: dict) -> bytes:
    """
    Строит мини-график за сегодня: две колонки "цель" vs "факт"
    для воды и калорий.

    progress ожидается в формате:
      {
        "water_ml": int,
        "water_goal_ml": int,
        "calories_in": float,
        "calorie_goal": int,
        ...
      }

    Возвращает PNG в bytes.
    """
    water_done = progress["water_ml"]
    water_goal = progress["water_goal_ml"]

    cal_done = progress["calories_in"]
    cal_goal = progress["calorie_goal"]

    fig = plt.figure(figsize=(8, 4))
    ax = fig.add_subplot(1, 1, 1)

    labels = ["Вода (мл)", "Калории (ккал)"]
    done = [water_done, cal_done]
    goal = [water_goal, cal_goal]

    # Рисуем цель как "фон", затем поверх факт
    x = [0, 1]
    ax.bar(x, goal, label="Цель")
    ax.bar(x, done, label="Факт")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_title("Прогресс за сегодня")
    ax.grid(True, axis="y")
    ax.legend()

    # Сохраняем фигуру в память (bytes)
    buf = BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)

    buf.seek(0)
    return buf.getvalue()
