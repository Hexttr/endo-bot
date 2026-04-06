from __future__ import annotations

from endo_bot.engine.models import TriageResult


def render_result(result: TriageResult) -> str:
    reasoning_lines = (
        "\n".join(f"• {item}" for item in result.reasoning)
        if result.reasoning
        else "• Недостаточно данных для объяснения."
    )
    return (
        "Результат сценария\n\n"
        f"Срочность: {result.urgency_level}\n"
        f"Вероятный источник: {result.probable_source}\n\n"
        f"Почему бот так решил:\n{reasoning_lines}\n\n"
        f"Рекомендуемый следующий шаг:\n{result.next_step}\n\n"
        f"Ограничения:\n{result.disclaimer}"
    )
