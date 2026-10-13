"""情感关怀事件契约：MQ 消息体定义。

事件是 frozen dataclass——不可变，保证序列化后内容稳定，可作为消息契约跨进程传递。
三类事件构成闭环：咨询完成 -> 建回访 -> 回访完成 -> (可能)再建下一轮回访。
event_id 用 uuid4，作为幂等键：同一条事件被重复消费时，下游可凭它查重，避免重复建单。
"""
from dataclasses import asdict, dataclass
from typing import Any
import json
import uuid


@dataclass(frozen=True)
class EmotionalCareEvent:
    event_id: str          # 幂等键：重复投递时下游凭此去重
    event_type: str
    user_id: str
    consultation_id: int | None = None
    follow_up_id: int | None = None

    # 三类事件对应闭环的三个节点
    CONSULTATION_COMPLETED = "CONSULTATION_COMPLETED"
    FOLLOW_UP_COMPLETED = "FOLLOW_UP_COMPLETED"
    FOLLOW_UP_REMINDER = "FOLLOW_UP_REMINDER"

    @classmethod
    def consultation_completed(cls, consultation_id: int, user_id: str) -> "EmotionalCareEvent":
        return cls(str(uuid.uuid4()), cls.CONSULTATION_COMPLETED, user_id, consultation_id=consultation_id)

    @classmethod
    def follow_up_completed(cls, follow_up_id: int, consultation_id: int, user_id: str) -> "EmotionalCareEvent":
        return cls(str(uuid.uuid4()), cls.FOLLOW_UP_COMPLETED, user_id, consultation_id=consultation_id, follow_up_id=follow_up_id)

    @classmethod
    def follow_up_reminder(cls, follow_up_id: int, consultation_id: int, user_id: str) -> "EmotionalCareEvent":
        return cls(str(uuid.uuid4()), cls.FOLLOW_UP_REMINDER, user_id, consultation_id=consultation_id, follow_up_id=follow_up_id)

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")

    @classmethod
    def from_bytes(cls, body: bytes) -> "EmotionalCareEvent":
        data: dict[str, Any] = json.loads(body.decode("utf-8"))
        return cls(**data)
