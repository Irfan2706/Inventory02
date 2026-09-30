from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ChatSession:
    session_id: str
    history: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content, "timestamp": datetime.now(timezone.utc).isoformat()})
        del self.history[:-10]

    def get_history_for_llm(self) -> list[dict[str, str]]:
        return self.history[-10:]


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}

    def get(self, session_id: str) -> ChatSession:
        return self._sessions.setdefault(session_id, ChatSession(session_id))
