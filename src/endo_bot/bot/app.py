from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from endo_bot.bot.formatting import render_result
from endo_bot.content.spec import load_clinical_spec
from endo_bot.engine.rule_engine import RuleEngine
from endo_bot.storage.session_store import CaseSession, FileSessionStore


spec = load_clinical_spec()
engine = RuleEngine(spec)
store = FileSessionStore(Path(__file__).resolve().parents[3] / "data" / "sessions")
dispatcher = Dispatcher()


def main_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=mode["title"], callback_data=f"mode:{mode['id']}")]
        for mode in spec.modes
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def question_keyboard(question: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=option["label"], callback_data=f"answer:{question['id']}:{option['id']}")]
        for option in question["options"]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def next_question(session: CaseSession) -> dict | None:
    if session.mode == "endoscopy_only":
        question_ids = ["endoscopy_available", "endoscopy_finding"]
    else:
        question_ids = spec.question_order
    for question_id in question_ids:
        if question_id in session.answers:
            continue
        question = spec.question_map[question_id]
        show_if = question.get("show_if")
        if show_if and session.answers.get(show_if["question_id"]) != show_if["equals"]:
            continue
        return question
    return None


@dispatcher.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Эндо-Бот помогает пройти детерминированный алгоритм триажа. "
        "Он не заменяет клиническое решение врача.",
        reply_markup=main_menu(),
    )


@dispatcher.callback_query(F.data.startswith("mode:"))
async def choose_mode(callback: CallbackQuery) -> None:
    mode = callback.data.split(":", 1)[1]
    if mode == "quick_reference":
        await callback.message.answer(
            "Краткая логика: сначала экстренность, затем признаки портальной гипертензии, "
            "варикозные и неварикозные признаки, после чего при наличии ЭГДС приоритет "
            "переходит к эндоскопическим находкам."
        )
        await callback.answer()
        return

    if mode == "resume_case":
        session = _load_latest_session(callback.from_user.id)
        if session is None:
            await callback.message.answer("Активный кейс не найден. Запустите новый кейс.")
            await callback.answer()
            return
        _append_audit_event(session, "resume_case", {"mode": mode})
        store.save(session)
        await callback.answer()
        await send_next_question(callback.message, session)
        return

    case_id = str(uuid.uuid4())
    session = CaseSession(
        case_id=case_id,
        user_id=callback.from_user.id,
        algorithm_version=spec.metadata["algorithm_version"],
        mode=mode,
    )
    _append_audit_event(session, "create_case", {"mode": mode})

    if mode == "endoscopy_only":
        session.answers["endoscopy_available"] = "yes"

    store.save(session)
    await callback.answer()
    await send_next_question(callback.message, session)


async def send_next_question(message: Message, session: CaseSession) -> None:
    question = next_question(session)
    if question is None:
        result = engine.evaluate(session.answers)
        session.status = "completed"
        _append_audit_event(
            session,
            "case_completed",
            {
                "path": result.path,
                "urgency_level": result.urgency_level,
                "probable_source": result.probable_source,
            },
        )
        store.save(session)
        await message.answer(render_result(result))
        return

    await message.answer(question["prompt"], reply_markup=question_keyboard(question))


@dispatcher.callback_query(F.data.startswith("answer:"))
async def process_answer(callback: CallbackQuery) -> None:
    _, question_id, option_id = callback.data.split(":")
    session = _load_latest_session(callback.from_user.id)
    if session is None:
        await callback.message.answer("Активный кейс не найден. Используйте /start.")
        await callback.answer()
        return

    session.answers[question_id] = option_id
    _append_audit_event(
        session,
        "answer_recorded",
        {"question_id": question_id, "answer_id": option_id},
    )
    store.save(session)
    await callback.answer()
    await send_next_question(callback.message, session)


def _load_latest_session(user_id: int) -> CaseSession | None:
    latest_session: CaseSession | None = None
    for session in sorted(store.list_sessions(), key=lambda item: item.case_id, reverse=True):
        if session and session.user_id == user_id and session.status == "in_progress":
            latest_session = session
            break
    return latest_session


def _append_audit_event(session: CaseSession, event_type: str, payload: dict) -> None:
    session.audit_log.append(
        {
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


async def run_bot() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    bot = Bot(token=token)
    await dispatcher.start_polling(bot)
