import logging

from app.db.models import ConsultationFollowUp, ConsultationRecord
from app.db.session import SessionLocal
from app.domain.consultation_effect_evaluator import ConsultationEffectEvaluator
from app.mq.event import EmotionalCareEvent
from app.services.emotion_profile_service import EmotionProfileService
from app.services.follow_up_service import FollowUpService

logger = logging.getLogger(__name__)


class EmotionalCarePostProcessService:
    def handle(self, event: EmotionalCareEvent, care_copy: str) -> None:
        with SessionLocal() as db:
            try:
                if event.event_type == EmotionalCareEvent.CONSULTATION_COMPLETED:
                    self._handle_consultation(db, event, care_copy)
                elif event.event_type == EmotionalCareEvent.FOLLOW_UP_COMPLETED:
                    self._handle_follow_up(db, event, care_copy)
                else:
                    raise ValueError(f"unsupported emotional care event type: {event.event_type}")
                db.commit()
            except Exception:
                db.rollback()
                raise

    def _handle_consultation(self, db, event: EmotionalCareEvent, care_copy: str) -> None:
        record = db.get(ConsultationRecord, event.consultation_id)
        if record is None or record.status != "COMPLETED":
            logger.warning("skip missing or incomplete consultation id=%s", event.consultation_id)
            return
        profile_service = EmotionProfileService(db)
        profile = profile_service.get_or_create(record.user_id)
        already_applied = profile.last_consultation_at == record.completed_at
        profile.current_emotion_score = record.after_emotion_score or profile.current_emotion_score
        profile.emotion_tags = record.after_emotion_tags
        profile.pressure_level = record.after_pressure_level or profile.pressure_level
        profile.risk_level = record.after_risk_level or profile.risk_level
        profile.latest_effect_level = record.effect_level
        profile.last_consultation_at = record.completed_at
        profile.emotion_trend = ConsultationEffectEvaluator.trend_by_delta(record.improvement_score or 0)
        profile.trend_summary = (
            care_copy
            + "\n最近一次咨询情绪状态"
            + ConsultationEffectEvaluator.trend_description(record.improvement_score or 0)
            + f"，效果：{record.effect_level or '未知'}"
        )
        if record.problem_summary:
            profile.problem_topics = record.problem_summary
        if not already_applied:
            profile.consultation_count = (profile.consultation_count or 0) + 1

        if record.need_follow_up:
            existing = db.query(ConsultationFollowUp).filter_by(consultation_id=record.id).first()
            if existing is None:
                created_follow_up = FollowUpService(db).create_for_consultation(
                    record.user_id,
                    record.id,
                    ConsultationEffectEvaluator.follow_up_type(record.after_risk_level),
                    record.next_follow_up_at,
                    record.after_emotion_score or 50,
                    record.after_emotion_tags,
                    record.after_risk_level or "LOW",
                )
                created_follow_up.conclusion = care_copy

    def _handle_follow_up(self, db, event: EmotionalCareEvent, care_copy: str) -> None:
        follow_up = db.get(ConsultationFollowUp, event.follow_up_id)
        if follow_up is None or follow_up.status != "COMPLETED":
            logger.warning("skip missing or incomplete follow-up id=%s", event.follow_up_id)
            return
        profile = EmotionProfileService(db).get_or_create(follow_up.user_id)
        before = follow_up.before_emotion_score or profile.current_emotion_score
        after = follow_up.after_emotion_score if follow_up.after_emotion_score is not None else before
        delta = after - before
        profile.current_emotion_score = after
        profile.emotion_tags = follow_up.after_emotion_tags
        profile.risk_level = follow_up.risk_level or profile.risk_level
        profile.emotion_trend = ConsultationEffectEvaluator.trend_by_delta(delta)
        profile.trend_summary = care_copy + "\n最近一次跟踪情绪状态" + ConsultationEffectEvaluator.trend_description(delta)
        follow_up.conclusion = care_copy if not follow_up.conclusion else follow_up.conclusion + "\n" + care_copy

        if follow_up.continue_follow_up:
            existing = db.query(ConsultationFollowUp).filter(
                ConsultationFollowUp.consultation_id == follow_up.consultation_id,
                ConsultationFollowUp.id > follow_up.id,
            ).first()
            if existing is None:
                FollowUpService(db).create_for_consultation(
                    follow_up.user_id,
                    follow_up.consultation_id,
                    ConsultationEffectEvaluator.follow_up_type(follow_up.risk_level),
                    follow_up.next_follow_up_at,
                    after,
                    follow_up.after_emotion_tags,
                    follow_up.risk_level or "LOW",
                )


def generate_care_copy(event: EmotionalCareEvent) -> str:
    if event.event_type == EmotionalCareEvent.CONSULTATION_COMPLETED:
        return "感谢你愿意认真面对自己的感受。请按照本次建议循序渐进，也记得给自己留出休息和调整的空间。"
    return "想和你确认一下最近的状态。无论进展快慢，你都可以按自己的节奏继续尝试，也可以随时寻求可信任的人支持。"
