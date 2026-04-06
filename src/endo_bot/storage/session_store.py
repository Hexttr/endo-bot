from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CaseSession:
    case_id: str
    user_id: int
    algorithm_version: str
    mode: str = "new_case"
    answers: dict[str, str] = field(default_factory=dict)
    status: str = "in_progress"
    audit_log: list[dict[str, Any]] = field(default_factory=list)


class FileSessionStore:
    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, session: CaseSession) -> None:
        path = self.base_path / f"{session.case_id}.json"
        path.write_text(json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, case_id: str) -> CaseSession | None:
        path = self.base_path / f"{case_id}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CaseSession(**payload)

    def list_sessions(self) -> list[CaseSession]:
        sessions: list[CaseSession] = []
        for path in sorted(self.base_path.glob("*.json")):
            session = self.load(path.stem)
            if session:
                sessions.append(session)
        return sessions
