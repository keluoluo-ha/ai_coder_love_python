from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StartConsultationRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)
    conversation_id: str = Field(alias="conversationId", min_length=1)
    consultation_type: str = Field(default="EMOTIONAL_COMPANIONSHIP", alias="consultationType")

    model_config = ConfigDict(populate_by_name=True)


class CompleteConsultationRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)
    after_emotion_score: int = Field(alias="afterEmotionScore", ge=0, le=100)
    after_emotion_tags: Optional[str] = Field(default=None, alias="afterEmotionTags")
    after_pressure_level: Optional[str] = Field(default=None, alias="afterPressureLevel")
    after_risk_level: Optional[str] = Field(default=None, alias="afterRiskLevel")
    problem_summary: Optional[str] = Field(default=None, alias="problemSummary")
    consultation_summary: Optional[str] = Field(default=None, alias="consultationSummary")
    suggestions: Optional[str] = None
    user_feedback: Optional[str] = Field(default=None, alias="userFeedback")
    preferred_follow_up_at: Optional[datetime] = Field(default=None, alias="preferredFollowUpAt")

    model_config = ConfigDict(populate_by_name=True)


class CompleteFollowUpRequest(BaseModel):
    after_emotion_score: int = Field(alias="afterEmotionScore", ge=0, le=100)
    after_emotion_tags: Optional[str] = Field(default=None, alias="afterEmotionTags")
    risk_level: Optional[str] = Field(default=None, alias="riskLevel")
    user_feedback: Optional[str] = Field(default=None, alias="userFeedback")
    action_plan_status: Optional[str] = Field(default=None, alias="actionPlanStatus")
    conclusion: Optional[str] = None
    continue_follow_up: Optional[bool] = Field(default=None, alias="continueFollowUp")
    next_follow_up_at: Optional[datetime] = Field(default=None, alias="nextFollowUpAt")

    model_config = ConfigDict(populate_by_name=True)


class SkipFollowUpRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)
    reason: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ConsultationDetailVO(BaseModel):
    consultation_id: int = Field(alias="consultationId")
    conversation_id: str = Field(alias="conversationId")
    status: str
    before_emotion_score: Optional[int] = Field(alias="beforeEmotionScore")
    after_emotion_score: Optional[int] = Field(alias="afterEmotionScore")
    improvement_score: Optional[int] = Field(alias="improvementScore")
    effect_level: Optional[str] = Field(alias="effectLevel")
    consultation_summary: Optional[str] = Field(alias="consultationSummary")
    suggestions: Optional[str]
    need_follow_up: bool = Field(alias="needFollowUp")
    next_follow_up_at: Optional[datetime] = Field(alias="nextFollowUpAt")
    started_at: Optional[datetime] = Field(alias="startedAt")
    completed_at: Optional[datetime] = Field(alias="completedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FollowUpVO(BaseModel):
    follow_up_id: int = Field(alias="followUpId")
    consultation_id: int = Field(alias="consultationId")
    follow_up_type: str = Field(alias="followUpType")
    status: str
    planned_at: Optional[datetime] = Field(alias="plannedAt")
    completed_at: Optional[datetime] = Field(alias="completedAt")
    before_emotion_score: Optional[int] = Field(alias="beforeEmotionScore")
    after_emotion_score: Optional[int] = Field(alias="afterEmotionScore")
    conclusion: Optional[str]
    continue_follow_up: bool = Field(alias="continueFollowUp")
    next_follow_up_at: Optional[datetime] = Field(alias="nextFollowUpAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EmotionProfileVO(BaseModel):
    user_id: str = Field(alias="userId")
    current_emotion_score: int = Field(alias="currentEmotionScore")
    emotion_tags: Optional[str] = Field(alias="emotionTags")
    problem_topics: Optional[str] = Field(alias="problemTopics")
    emotion_trend: str = Field(alias="emotionTrend")
    trend_summary: Optional[str] = Field(alias="trendSummary")
    pressure_level: str = Field(alias="pressureLevel")
    risk_level: str = Field(alias="riskLevel")
    consultation_count: int = Field(alias="consultationCount")
    latest_effect_level: Optional[str] = Field(alias="latestEffectLevel")
    last_consultation_at: Optional[datetime] = Field(alias="lastConsultationAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
