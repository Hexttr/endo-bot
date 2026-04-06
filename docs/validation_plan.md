# Validation Plan

## Goal

Validate that the deterministic triage engine produces clinically sensible and reproducible outputs before broader deployment.

## Scope

- Variceal bleeding scenarios with portal hypertension background.
- Non-variceal bleeding scenarios with ulcer-like features.
- Mixed and uncertain presentations.
- Scenarios with endoscopic confirmation overriding the clinical score.

## Validation workflow

1. Build a starter set of 15-30 synthetic or retrospective anonymized cases.
2. For each case, record:
   - input answers,
   - expected urgency,
   - expected probable source,
   - whether endoscopy is available,
   - expected next step category.
3. Run the cases through the engine.
4. Compare engine output with expert assessment.
5. Review mismatches and refine:
   - question wording,
   - rule thresholds,
   - derived rules,
   - mixed-source fallback logic.

## Minimum acceptance criteria

- No false low-priority output in obviously urgent bleeding scenarios.
- Endoscopic confirmation always has priority over pure clinical scoring.
- Known high-risk EHPVO / portal cavernoma patterns are classified as variceal-focused.
- Mixed or weak evidence scenarios remain non-categorical.

## Suggested expert review questions

- Was the urgency level clinically acceptable?
- Was the probable source classification reasonable?
- Did the explanation highlight the right clinical features?
- Was the next step too weak, too strong, or appropriate?
- Did the algorithm ask unnecessary questions?

## Regression assets already included

- `data/validation_cases.json`
- `tests/test_rule_engine.py`

These should be expanded whenever the clinical algorithm changes.
