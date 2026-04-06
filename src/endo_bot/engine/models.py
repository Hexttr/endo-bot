from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RuleEvaluation:
    rule_id: str
    explanation: str
    applied: bool


@dataclass
class AnswerRecord:
    question_id: str
    answer_id: str


@dataclass
class EngineState:
    answers: dict[str, str] = field(default_factory=dict)
    flags: set[str] = field(default_factory=set)
    scores: dict[str, int] = field(default_factory=dict)
    applied_rules: list[RuleEvaluation] = field(default_factory=list)
    derived_path: str | None = None


@dataclass
class TriageResult:
    urgency_level: str
    probable_source: str
    reasoning: list[str]
    next_step: str
    triggered_flags: list[str]
    scores: dict[str, int]
    path: str
    disclaimer: str
