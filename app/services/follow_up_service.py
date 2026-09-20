import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConsultationFollowUp
from app.domain.consultation_effect_evaluator import ConsultationEffectEvaluator
from app.schemas_consultation import CompleteFollowUpRequest, FollowUpVO, SkipFollowUpRequest
from app.mq.publisher import EmotionalCareEventPublisher

logger = logging.getLogger(__name__)


class FollowUpService:
    def __init__(self, db: Session):
        self.db = db

    def pending(self, user_id: str) -> list[FollowUpVO]:
        rows = self.db.scalars(
            select(ConsultationFollowUp)
            .where(ConsultationFollowUp.user_id == user_id, ConsultationFollowUp.status == "PENDING")
            .order_by(ConsultationFollowUp.planned_at.asc())
        ).all()
        return [self.to_vo(row) for row in rows]

    def complete(self, follow_up_id: int, user_id: str, request: CompleteFollowUpRequest) -> FollowUpVO:
        follow_up = self._require_pending(follow_up_id, user_id)
        now = datetime.utcnow()
        risk = ConsultationEffectEvaluator.blank_to_default(request.risk_level, follow_up.risk_level or "LOW")
        continue_follow_up = bool(request.continue_follow_up) or ConsultationEffectEvaluator.is_high_risk(risk)
        follow_up.after_emotion_score = request.after_emotion_score
        follow_up.after_emotion_tags = request.after_emotion_tags
        follow_up.risk_level = risk
        follow_up.user_feedback = request.user_feedback
        follow_up.action_plan_status = request.action_plan_status
        follow_up.conclusion = request.conclusion
        follow_up.continue_follow_up = int(continue_follow_up)
        follow_up.next_follow_up_at = request.next_follow_up_at or (now + timedelta(days=3) if continue_follow_up else None)
        follow_up.completed_at = now
        follow_up.status = "COMPLETED"
        self.db.commit()
        self.db.refresh(follow_up)
        try:
            EmotionalCareEventPublisher().publish_follow_up_completed(
                follow_up.id, follow_up.consultation_id, follow_up.user_id
            )
        except Exception:
            logger.exception("follow-up completed but emotional care event publish failed id=%s", follow_up.id)
        return self.to_vo(follow_up)

    def skip(self, follow_up_id: int, request: SkipFollowUpRequest) -> FollowUpVO:
        follow_up = self._require_pending(follow_up_id, request.user_id)
        follow_up.status = "SKIPPED"
        follow_up.completed_at = datetime.utcnow()
        follow_up.continue_follow_up = 0
        follow_up.conclusion = request.reason or "用户跳过本次跟踪"
        self.db.commit()
        self.db.refresh(follow_up)
        return self.to_vo(follow_up)

    def create_for_consultation(self, user_id: str, consultation_id: int, follow_up_type: str, planned_at: datetime, score: int, tags: str | None, risk: str) -> ConsultationFollowUp:
        row = ConsultationFollowUp(
            user_id=user_id, consultation_id=consultation_id, follow_up_type=follow_up_type,
            status="PENDING", planned_at=planned_at, before_emotion_score=score,
            before_emotion_tags=tags, risk_level=risk,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _require_pending(self, follow_up_id: int, user_id: str) -> ConsultationFollowUp:
        row = self.db.get(ConsultationFollowUp, follow_up_id)
        if row is None:
            raise LookupError("跟踪记录不存在")
        if row.user_id != user_id:
            raise PermissionError("无权操作该跟踪记录")
        if row.status != "PENDING":
            raise ValueError("只有待跟踪记录可以完成或跳过")
        return row

    @staticmethod
    def to_vo(row: ConsultationFollowUp) -> FollowUpVO:
        return FollowUpVO(
            followUpId=row.id, consultationId=row.consultation_id, followUpType=row.follow_up_type,
            status=row.status, plannedAt=row.planned_at, completedAt=row.completed_at,
            beforeEmotionScore=row.before_emotion_score, afterEmotionScore=row.after_emotion_score,
            conclusion=row.conclusion, continueFollowUp=bool(row.continue_follow_up), nextFollowUpAt=row.next_follow_up_at,
        )
