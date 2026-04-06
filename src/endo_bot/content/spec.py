from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ClinicalSpec:
    raw: dict[str, Any]

    @property
    def metadata(self) -> dict[str, Any]:
        return self.raw["metadata"]

    @property
    def modes(self) -> list[dict[str, Any]]:
        return self.raw["modes"]

    @property
    def question_order(self) -> list[str]:
        return self.raw["question_order"]

    @property
    def questions(self) -> list[dict[str, Any]]:
        return self.raw["questions"]

    @property
    def question_map(self) -> dict[str, dict[str, Any]]:
        return {question["id"]: question for question in self.questions}

    @property
    def scoring(self) -> dict[str, Any]:
        return self.raw["scoring"]

    @property
    def result_templates(self) -> dict[str, Any]:
        return self.raw["result_templates"]

    @property
    def disclaimer(self) -> str:
        return self.raw["disclaimer"]


def load_clinical_spec(path: str | Path | None = None) -> ClinicalSpec:
    base_dir = Path(__file__).resolve().parents[3]
    spec_path = Path(path) if path else base_dir / "data" / "clinical_spec.json"
    with spec_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return ClinicalSpec(raw=raw)
