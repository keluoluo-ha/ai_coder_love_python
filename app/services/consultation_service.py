from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConsultationRecord
from app.domain.consultation_effect_evaluator import ConsultationEffectEvaluator
from app.schemas_consultation import CompleteConsultationRequest, ConsultationDetailVO, StartConsultationRequest
import logging

from app.mq.publisher import EmotionalCareEventPublisher
from app.services.emotion_profile_service import EmotionProfileService

logger = logging.getLogger(__name__)


class ConsultationService:
    def __init__(self, db: Session):
        self.db = db

    def start(self, request: StartConsultationRequest) -> ConsultationDetailVO:
        profile = EmotionProfileService(self.db).get_or_create(request.user_id)
        existing = self.db.scalar(
            select(ConsultationRecord)
            .where(ConsultationRecord.user_id == request.user_id, ConsultationRecord.status == "IN_PROGRESS")
            .order_by(ConsultationRecord.started_at.desc())
        )
        if existing:
            return self.to_vo(existing)
        record = ConsultationRecord(
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            consultation_type=request.consultation_type or "EMOTIONAL_COMPANIONSHIP",
            status="IN_PROGRESS",
            before_emotion_score=profile.current_emotion_score,
            before_emotion_tags=profile.emotion_tags,
            before_pressure_level=profile.pressure_level,
            before_risk_level=profile.risk_level,
            need_follow_up=0,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self.to_vo(record)

    def complete(self, consultation_id: int, request: CompleteConsultationRequest) -> ConsultationDetailVO:
        record = self._require(consultation_id)
        if record.user_id != request.user_id:
            raise PermissionError("无权操作该咨询记录")
        if record.status != "IN_PROGRESS":
            raise ValueError("只有进行中的咨询可以完成评估")
        now = datetime.utcnow()
        after_risk = ConsultationEffectEvaluator.blank_to_default(request.after_risk_level, record.before_risk_level or "LOW")
        improvement = request.after_emotion_score - (record.before_emotion_score or 50)
        effect = ConsultationEffectEvaluator.effect_level(improvement, after_risk, record.before_risk_level)
        need_follow_up = ConsultationEffectEvaluator.should_follow_up(effect, after_risk)
        follow_up_at = request.preferred_follow_up_at or now + timedelta(days=ConsultationEffectEvaluator.default_follow_up_days(effect, after_risk))
        record.after_emotion_score = request.after_emotion_score
        record.after_emotion_tags = request.after_emotion_tags
        record.after_pressure_level = ConsultationEffectEvaluator.blank_to_default(request.after_pressure_level, record.before_pressure_level or "MEDIUM")
        record.after_risk_level = after_risk
        record.improvement_score = improvement
        record.effect_level = effect
        record.problem_summary = request.problem_summary
        record.consultation_summary = request.consultation_summary
        record.suggestions = request.suggestions
        record.user_feedback = request.user_feedback
        record.need_follow_up = int(need_follow_up)
        record.next_follow_up_at = follow_up_at if need_follow_up else None
        record.completed_at = now
        record.status = "COMPLETED"
        self.db.commit()
        self.db.refresh(record)
        try:
            EmotionalCareEventPublisher().publish_consultation_completed(record.id, record.user_id)
        except Exception:
            logger.exception("consultation completed but emotional care event publish failed id=%s", record.id)
        return self.to_vo(record)

    def detail(self, consultation_id: int, user_id: str) -> ConsultationDetailVO:
        record = self._require(consultation_id)
        if record.user_id != user_id:
            raise PermissionError("无权访问该咨询记录")
        return self.to_vo(record)

    def history(self, user_id: str) -> list[ConsultationDetailVO]:
        rows = self.db.scalars(
            select(ConsultationRecord).where(ConsultationRecord.user_id == user_id).order_by(ConsultationRecord.started_at.desc())
        ).all()
        return [self.to_vo(row) for row in rows]

    def _require(self, consultation_id: int) -> ConsultationRecord:
        row = self.db.get(ConsultationRecord, consultation_id)
        if row is None:
            raise LookupError("咨询记录不存在")
        return row

    @staticmethod
    def to_vo(row: ConsultationRecord) -> ConsultationDetailVO:
        return ConsultationDetailVO(
            consultationId=row.id, conversationId=row.conversation_id, status=row.status,
            beforeEmotionScore=row.before_emotion_score, afterEmotionScore=row.after_emotion_score,
            improvementScore=row.improvement_score, effectLevel=row.effect_level,
            consultationSummary=row.consultation_summary, suggestions=row.suggestions,
            needFollowUp=bool(row.need_follow_up), nextFollowUpAt=row.next_follow_up_at,
            startedAt=row.started_at, completedAt=row.completed_at,
        )
