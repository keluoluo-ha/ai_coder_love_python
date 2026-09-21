from dataclasses import asdict, dataclass
from typing import Any
import json
import uuid


@dataclass(frozen=True)
class EmotionalCareEvent:
    event_id: str
    event_type: str
    user_id: str
    consultation_id: int | None = None
    follow_up_id: int | None = None

    CONSULTATION_COMPLETED = "CONSULTATION_COMPLETED"
    FOLLOW_UP_COMPLETED = "FOLLOW_UP_COMPLETED"

    @classmethod
    def consultation_completed(cls, consultation_id: int, user_id: str) -> "EmotionalCareEvent":
        return cls(str(uuid.uuid4()), cls.CONSULTATION_COMPLETED, user_id, consultation_id=consultation_id)

    @classmethod
    def follow_up_completed(cls, follow_up_id: int, consultation_id: int, user_id: str) -> "EmotionalCareEvent":
        return cls(str(uuid.uuid4()), cls.FOLLOW_UP_COMPLETED, user_id, consultation_id=consultation_id, follow_up_id=follow_up_id)

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")

    @classmethod
    def from_bytes(cls, body: bytes) -> "EmotionalCareEvent":
        data: dict[str, Any] = json.loads(body.decode("utf-8"))
        return cls(**data)
