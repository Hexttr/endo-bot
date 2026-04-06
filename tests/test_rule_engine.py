from __future__ import annotations

import json
from pathlib import Path

from endo_bot.content.spec import load_clinical_spec
from endo_bot.engine.rule_engine import RuleEngine


def load_validation_cases() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "data" / "validation_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_validation_cases_match_expected_paths() -> None:
    spec = load_clinical_spec()
    engine = RuleEngine(spec)

    for case in load_validation_cases():
        result = engine.evaluate(case["answers"])
        assert result.path == case["expected_path"], case["id"]


def test_probable_variceal_contains_reasoning() -> None:
    spec = load_clinical_spec()
    engine = RuleEngine(spec)

    answers = {
        "fresh_blood_vomiting": "yes",
        "coffee_ground_vomiting": "no",
        "melena": "yes",
        "hemodynamic_compromise": "no",
        "active_bleeding_now": "no",
        "portal_cavernoma": "yes",
        "portal_hypertension_background": "no",
        "pediatric_patient": "yes",
        "splenomegaly": "yes",
        "thrombocytopenia": "yes",
        "known_varices": "yes",
        "prior_variceal_bleeding": "no",
        "prior_banding_or_sclerotherapy": "no",
        "portosystemic_collaterals": "yes",
        "sudden_onset": "yes",
        "epigastric_pain": "no",
        "nsaids_or_anticoagulants": "no",
        "ulcer_history": "no",
        "retching_before_bleeding": "no",
        "dyspepsia_before_episode": "no",
        "endoscopy_available": "no",
    }

    result = engine.evaluate(answers)
    assert result.path in {"high_probable_variceal", "probable_variceal"}
    assert result.reasoning
    assert "portal_hypertension" in result.triggered_flags
