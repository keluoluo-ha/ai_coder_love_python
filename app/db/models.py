from typing import Optional
import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class ChatMessage(Base):
    __tablename__ = 'chat_message'
    __table_args__ = (
        Index('idx_chat_session_id', 'session_id'),
        {'comment': 'AI对话历史记录表'}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, comment='会话唯一ID，区分不同用户对话')
    message: Mapped[str] = mapped_column(Text, nullable=False, comment='LangChain消息JSON字符串')
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='消息创建时间')


class ConsultationRecord(Base):
    __tablename__ = 'consultation_record'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='IN_PROGRESS')
    consultation_type: Mapped[str] = mapped_column(String(64), nullable=False, default='EMOTIONAL_COMPANIONSHIP')
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    before_emotion_score: Mapped[Optional[int]] = mapped_column(Integer)
    before_emotion_tags: Mapped[Optional[str]] = mapped_column(Text)
    before_pressure_level: Mapped[Optional[str]] = mapped_column(String(32))
    before_risk_level: Mapped[Optional[str]] = mapped_column(String(32))
    after_emotion_score: Mapped[Optional[int]] = mapped_column(Integer)
    after_emotion_tags: Mapped[Optional[str]] = mapped_column(Text)
    after_pressure_level: Mapped[Optional[str]] = mapped_column(String(32))
    after_risk_level: Mapped[Optional[str]] = mapped_column(String(32))
    improvement_score: Mapped[Optional[int]] = mapped_column(Integer)
    effect_level: Mapped[Optional[str]] = mapped_column(String(32))
    problem_summary: Mapped[Optional[str]] = mapped_column(Text)
    consultation_summary: Mapped[Optional[str]] = mapped_column(Text)
    suggestions: Mapped[Optional[str]] = mapped_column(Text)
    user_feedback: Mapped[Optional[str]] = mapped_column(Text)
    need_follow_up: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_follow_up_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.datetime.utcnow)


class ConsultationFollowUp(Base):
    __tablename__ = 'consultation_follow_up'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    consultation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    follow_up_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='PENDING')
    planned_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    before_emotion_score: Mapped[Optional[int]] = mapped_column(Integer)
    after_emotion_score: Mapped[Optional[int]] = mapped_column(Integer)
    before_emotion_tags: Mapped[Optional[str]] = mapped_column(Text)
    after_emotion_tags: Mapped[Optional[str]] = mapped_column(Text)
    risk_level: Mapped[Optional[str]] = mapped_column(String(32))
    user_feedback: Mapped[Optional[str]] = mapped_column(Text)
    action_plan_status: Mapped[Optional[str]] = mapped_column(String(64))
    conclusion: Mapped[Optional[str]] = mapped_column(Text)
    continue_follow_up: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_follow_up_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.datetime.utcnow)


class EmotionProfile(Base):
    __tablename__ = 'emotion_profile'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    current_emotion_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    emotion_tags: Mapped[Optional[str]] = mapped_column(Text)
    problem_topics: Mapped[Optional[str]] = mapped_column(Text)
    emotion_trend: Mapped[str] = mapped_column(String(32), nullable=False, default='STABLE')
    trend_summary: Mapped[Optional[str]] = mapped_column(Text)
    pressure_level: Mapped[str] = mapped_column(String(32), nullable=False, default='MEDIUM')
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default='LOW')
    consultation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_effect_level: Mapped[Optional[str]] = mapped_column(String(32))
    last_consultation_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=datetime.datetime.utcnow)


class ProcessedEventLog(Base):
    """已处理事件日志：消费端用 event_id 幂等，重复投递直接跳过。

    与业务键查重(consultation_id)是两层防线：业务键防"同一咨询重复建单"，
    event_id 防"同一条事件重复消费整段逻辑"(含 profile 更新)。
    """
    __tablename__ = 'processed_event_log'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment='MQ事件幂等键')
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, comment='事件类型')
    processed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='处理完成时间')
