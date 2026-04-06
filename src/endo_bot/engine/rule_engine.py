from __future__ import annotations

from dataclasses import replace
from typing import Any

from endo_bot.content.spec import ClinicalSpec
from endo_bot.engine.models import EngineState, RuleEvaluation, TriageResult
from endo_bot.engine.result_builder import ResultBuilder


class RuleEngine:
    def __init__(self, spec: ClinicalSpec) -> None:
        self.spec = spec
        self._questions = spec.question_map
        self._thresholds = spec.scoring["thresholds"]
        self._derived_rules = spec.scoring["derived_rules"]
        self._builder = ResultBuilder(spec.result_templates, spec.disclaimer)

    def evaluate(self, answers: dict[str, str]) -> TriageResult:
        state = EngineState(answers=dict(answers))
        reasoning: list[str] = []

        for question_id in self.spec.question_order:
            if question_id not in answers:
                continue
            question = self._questions[question_id]
            if not self._should_ask(question, answers):
                continue
            option = self._get_option(question, answers[question_id])
            if option is None:
                continue
            self._apply_option_effects(state, question, option, reasoning)

        self._apply_derived_rules(state, reasoning)
        path = self._determine_path(state, reasoning)
        return self._builder.build(path, state, reasoning[:5])

    def _should_ask(self, question: dict[str, Any], answers: dict[str, str]) -> bool:
        show_if = question.get("show_if")
        if not show_if:
            return True
        return answers.get(show_if["question_id"]) == show_if["equals"]

    def _get_option(self, question: dict[str, Any], answer_id: str) -> dict[str, Any] | None:
        for option in question["options"]:
            if option["id"] == answer_id:
                return option
        return None

    def _apply_option_effects(
        self,
        state: EngineState,
        question: dict[str, Any],
        option: dict[str, Any],
        reasoning: list[str],
    ) -> None:
        effects = option.get("effects", {})
        for flag in effects.get("flags", []):
            state.flags.add(flag)
        for score_name, increment in effects.get("scores", {}).items():
            state.scores[score_name] = state.scores.get(score_name, 0) + increment

        if effects and option["id"] != "unknown":
            reasoning.append(f"{question['prompt']} {option['label']}.")

    def _apply_derived_rules(self, state: EngineState, reasoning: list[str]) -> None:
        for rule in self._derived_rules:
            applies = self._rule_applies(rule, state.flags)
            state.applied_rules.append(
                RuleEvaluation(
                    rule_id=rule["id"],
                    explanation=rule["explanation"],
                    applied=applies,
                )
            )
            if not applies:
                continue
            for score_name, increment in rule.get("add_scores", {}).items():
                state.scores[score_name] = state.scores.get(score_name, 0) + increment
            if "force_path" in rule:
                state.derived_path = rule["force_path"]
            reasoning.append(rule["explanation"])

    def _rule_applies(self, rule: dict[str, Any], flags: set[str]) -> bool:
        required_all = set(rule.get("when_all_flags", []))
        required_any = set(rule.get("when_any_flags", []))
        if required_all and not required_all.issubset(flags):
            return False
        if required_any and flags.isdisjoint(required_any):
            return False
        return True

    def _determine_path(self, state: EngineState, reasoning: list[str]) -> str:
        if "confirmed_variceal_source" in state.flags:
            return "confirmed_variceal"
        if "confirmed_non_variceal_source" in state.flags:
            return "confirmed_non_variceal"
        if state.derived_path == "high_probable_variceal":
            return "high_probable_variceal"

        portal_hypertension_score = state.scores.get("portal_hypertension", 0)
        variceal_score = state.scores.get("variceal", 0)
        non_variceal_score = state.scores.get("non_variceal", 0)
        urgency_score = state.scores.get("urgency", 0)

        has_urgent_path = "urgent_path" in state.flags or urgency_score >= 3
        has_portal_hypertension = (
            "portal_hypertension" in state.flags
            or portal_hypertension_score >= self._thresholds["portal_hypertension_present"]
        )

        if has_portal_hypertension and variceal_score >= self._thresholds["high_variceal"]:
            return "high_probable_variceal"
        if has_portal_hypertension and variceal_score >= self._thresholds["probable_variceal_with_ph"]:
            return "probable_variceal"
        if non_variceal_score >= self._thresholds["probable_non_variceal"] and variceal_score < non_variceal_score:
            return "probable_non_variceal"
        if has_urgent_path and (variceal_score > 0 or non_variceal_score > 0):
            return "mixed_source"
        if variceal_score > non_variceal_score and variceal_score >= 3:
            return "probable_variceal"
        if non_variceal_score > variceal_score and non_variceal_score >= 2:
            return "probable_non_variceal"
        return "mixed_source"


def clone_state(state: EngineState) -> EngineState:
    return replace(state)
