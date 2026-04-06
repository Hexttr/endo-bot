from __future__ import annotations

from endo_bot.engine.models import EngineState, TriageResult


class ResultBuilder:
    def __init__(self, templates: dict, disclaimer: str) -> None:
        self._templates = templates
        self._disclaimer = disclaimer

    def build(self, path: str, state: EngineState, reasoning: list[str]) -> TriageResult:
        template = self._templates[path]
        return TriageResult(
            urgency_level=template["urgency_level"],
            probable_source=template["probable_source"],
            reasoning=reasoning,
            next_step=template["next_step"],
            triggered_flags=sorted(state.flags),
            scores=dict(sorted(state.scores.items())),
            path=path,
            disclaimer=self._disclaimer,
        )
