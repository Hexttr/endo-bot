from __future__ import annotations

from endo_bot.engine.models import TriageResult


def _urgency_badge(urgency_level: str) -> str:
    mapping = {
        "экстренно": "🔴 Экстренно",
        "срочно": "🟠 Срочно",
        "планово": "🟢 Планово",
    }
    return mapping.get(urgency_level, urgency_level)


def render_result(result: TriageResult) -> str:
    reasoning_lines = (
        "\n".join(f"• {item}" for item in result.reasoning)
        if result.reasoning
        else "• Недостаточно данных для объяснения."
    )
    return (
        "━━━━━━━━━━\n"
        "🧾 Результат сценария\n"
        "━━━━━━━━━━\n\n"
        f"🚦 Срочность\n{_urgency_badge(result.urgency_level)}\n\n"
        f"🩸 Вероятный источник\n{result.probable_source}\n\n"
        f"🧠 Почему бот так решил\n{reasoning_lines}\n\n"
        f"➡️ Следующий шаг\n{result.next_step}\n\n"
        f"⚠️ Ограничения\n{result.disclaimer}"
    )
