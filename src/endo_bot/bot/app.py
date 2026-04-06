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


def post_result_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Новый кейс", callback_data="mode:new_case")],
            [InlineKeyboardButton(text="Ввести данные ЭГДС", callback_data="mode:endoscopy_only")],
            [InlineKeyboardButton(text="Краткий алгоритм", callback_data="mode:quick_reference")],
            [InlineKeyboardButton(text="Главное меню", callback_data="nav:menu")],
        ]
    )


def question_keyboard(question: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=option["label"], callback_data=f"answer:{question['id']}:{option['id']}")]
        for option in question["options"]
    ]
    rows.append(
        [
            InlineKeyboardButton(text="Назад", callback_data="nav:back"),
            InlineKeyboardButton(text="В меню", callback_data="nav:menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def visible_question_ids(session: CaseSession) -> list[str]:
    if session.mode == "endoscopy_only":
        question_ids = ["endoscopy_available", "endoscopy_finding"]
    else:
        question_ids = spec.question_order

    visible_ids: list[str] = []
    for question_id in question_ids:
        question = spec.question_map[question_id]
        show_if = question.get("show_if")
        if show_if and session.answers.get(show_if["question_id"]) != show_if["equals"]:
            continue
        visible_ids.append(question_id)
    return visible_ids


def next_question(session: CaseSession) -> dict | None:
    for question_id in visible_question_ids(session):
        if question_id in session.answers:
            continue
        return spec.question_map[question_id]
    return None


@dispatcher.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Эндо-Бот помогает эндоскописту быстро пройти структурированный алгоритм триажа.\n\n"
        "Что умеет бот:\n"
        "• провести по пошаговому сценарию\n"
        "• выделить срочность случая\n"
        "• показать вероятный источник кровотечения\n"
        "• подсказать следующий шаг\n\n"
        "Важно: бот не заменяет клиническое решение врача.",
        reply_markup=main_menu(),
    )


@dispatcher.callback_query(F.data.startswith("mode:"))
async def choose_mode(callback: CallbackQuery) -> None:
    mode = callback.data.split(":", 1)[1]
    if mode == "quick_reference":
        await callback.message.answer(
            "Краткая логика работы бота:\n\n"
            "1. Сначала оценивается экстренность.\n"
            "2. Затем собираются признаки портальной гипертензии.\n"
            "3. После этого бот сопоставляет варикозные и неварикозные признаки.\n"
            "4. Если есть ЭГДС, приоритет переходит к эндоскопическим находкам."
        )
        await callback.message.answer("Выберите следующее действие:", reply_markup=post_result_menu())
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
        await message.answer("Что хотите сделать дальше?", reply_markup=post_result_menu())
        return

    question_ids = visible_question_ids(session)
    current_step = len([question_id for question_id in question_ids if question_id in session.answers]) + 1
    total_steps = len(question_ids)
    progress_line = f"Шаг {current_step} из {total_steps}"
    hint = question.get("hint")
    hint_block = f"\n\nПочему это важно: {hint}" if hint else ""
    text = f"{progress_line}\n\n{question['prompt']}{hint_block}"
    await message.answer(text, reply_markup=question_keyboard(question))


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


@dispatcher.callback_query(F.data == "nav:menu")
async def return_to_menu(callback: CallbackQuery) -> None:
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()


@dispatcher.callback_query(F.data == "nav:back")
async def go_back(callback: CallbackQuery) -> None:
    session = _load_latest_session(callback.from_user.id)
    if session is None:
        await callback.message.answer("Активный кейс не найден. Используйте /start.")
        await callback.answer()
        return

    answered_visible = [question_id for question_id in visible_question_ids(session) if question_id in session.answers]
    if not answered_visible:
        await callback.message.answer("Это начало сценария. Выберите режим в меню.", reply_markup=main_menu())
        await callback.answer()
        return

    last_question_id = answered_visible[-1]
    session.answers.pop(last_question_id, None)
    _append_audit_event(session, "answer_reverted", {"question_id": last_question_id})
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
