# Endo Bot

Deterministic Telegram bot for upper GI bleeding triage in difficult endoscopy cases.

## What is implemented

- Declarative `clinical-spec` based on the three source materials.
- Deterministic rule engine with:
  - emergency override logic;
  - portal hypertension and variceal/non-variceal scoring;
  - endoscopic confirmation priority;
  - explainable reasoning output.
- Telegram bot flow with modes:
  - `Новый кейс`
  - `Продолжить кейс` placeholder via latest in-progress session
  - `Ввести данные ЭГДС`
  - `Посмотреть краткий алгоритм`
- File-based session persistence for local development.
- SQL schema for persistent storage and audit trail.
- Validation dataset and automated tests.

## Project structure

- `data/clinical_spec.json` - machine-readable clinical algorithm
- `data/validation_cases.json` - validation scenarios
- `src/endo_bot/engine/` - deterministic rule engine
- `src/endo_bot/bot/` - Telegram interface
- `src/endo_bot/storage/` - session storage
- `sql/schema.sql` - database schema
- `tests/` - regression checks

## Run locally

```bash
python -m pip install -e .
set TELEGRAM_BOT_TOKEN=your_token_here
python -m endo_bot.main
```

## Run tests

```bash
python -m pytest
```

## Clinical note

The bot does not replace clinician judgment, does not prescribe therapy on its own, and is designed to support structured triage and documentation.
