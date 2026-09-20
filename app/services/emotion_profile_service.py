from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EmotionProfile


class EmotionProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: str) -> EmotionProfile:
        if not user_id or not user_id.strip():
            raise ValueError("userId不能为空")
        profile = self.db.scalar(select(EmotionProfile).where(EmotionProfile.user_id == user_id))
        if profile is None:
            profile = EmotionProfile(
                user_id=user_id,
                current_emotion_score=50,
                emotion_trend="STABLE",
                pressure_level="MEDIUM",
                risk_level="LOW",
                consultation_count=0,
            )
            self.db.add(profile)
            self.db.flush()
        return profile

    def refresh_after_consultation(self, profile: EmotionProfile, score: int, tags: str | None, risk: str, pressure: str, effect: str, delta: int, completed_at: datetime) -> EmotionProfile:
        profile.current_emotion_score = score
        profile.emotion_tags = tags
        profile.risk_level = risk
        profile.pressure_level = pressure
        profile.latest_effect_level = effect
        profile.emotion_trend = "RISING" if delta >= 10 else "FALLING" if delta <= -10 else "STABLE"
        profile.trend_summary = "改善" if delta >= 10 else "下降" if delta <= -10 else "基本稳定"
        profile.consultation_count = (profile.consultation_count or 0) + 1
        profile.last_consultation_at = completed_at
        self.db.flush()
        return profile
