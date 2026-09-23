from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from app.schema import AgentState, Message


@dataclass
class AgentRunState:
    run_id: str
    memory: list[Message] = field(default_factory=list)
    steps: int = 0
    state: AgentState = AgentState.IDLE
    pending_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    chat_id: str | None = None


class AgentRunStateStore(ABC):
    @abstractmethod
    def get(self, run_id: str) -> AgentRunState | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, run_state: AgentRunState) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, run_id: str) -> None:
        raise NotImplementedError


class InMemoryAgentRunStateStore(AgentRunStateStore):
    def __init__(self):
        self._states: dict[str, AgentRunState] = {}
        self._lock = RLock()

    def get(self, run_id: str) -> AgentRunState | None:
        with self._lock:
            return self._states.get(run_id)

    def save(self, run_state: AgentRunState) -> None:
        with self._lock:
            self._states[run_state.run_id] = run_state

    def delete(self, run_id: str) -> None:
        with self._lock:
            self._states.pop(run_id, None)


run_state_store = InMemoryAgentRunStateStore()
