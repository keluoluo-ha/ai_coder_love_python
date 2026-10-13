"""消费端业务逻辑：评估 + 建回访 + 提醒状态推进。

与传输层解耦：handle(event, care_copy) 收的是 Python 对象（EmotionalCareEvent），
不感知 MQ 存在，因此单测可直接构造事件对象喂进来，不需要真连 RabbitMQ。
事务边界：每条事件一个事务，成功 commit / 异常 rollback 并向上抛（由 consumer nack 回队）。
回访状态生命周期：PENDING（建单）-> REMINDED（到点提醒）-> COMPLETED（回访完成）。
"""
import logging

from app.db.models import ConsultationFollowUp, ConsultationRecord
from app.db.session import SessionLocal
from app.domain.consultation_effect_evaluator import ConsultationEffectEvaluator
from app.mq.event import EmotionalCareEvent
from app.mq.publisher import EmotionalCareEventPublisher
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
                elif event.event_type == EmotionalCareEvent.FOLLOW_UP_REMINDER:
                    self._handle_reminder(db, event)
                else:
                    raise ValueError(f"unsupported emotional care event type: {event.event_type}")
                db.commit()  # 单事件一个事务
            except Exception:
                db.rollback()  # 失败回滚，异常上抛 -> consumer nack requeue
                raise

    def _handle_consultation(self, db, event: EmotionalCareEvent, care_copy: str) -> None:
        record = db.get(ConsultationRecord, event.consultation_id)
        if record is None or record.status != "COMPLETED":
            logger.warning("skip missing or incomplete consultation id=%s", event.consultation_id)
            return
        profile_service = EmotionProfileService(db)
        profile = profile_service.get_or_create(record.user_id)
        # 幂等：last_consultation_at 已等于本次 completed_at 说明本事件被重复消费，不重复计数
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
            # 幂等：同一咨询已建过回访就不再建，避免重复消费导致重复建单
            existing = db.query(ConsultationFollowUp).filter_by(consultation_id=record.id).first()
            if existing is None:
                created_follow_up = FollowUpService(db).create_for_consultation(
                    record.user_id,
                    record.id,
                    ConsultationEffectEvaluator.follow_up_type(record.after_risk_level),  # 回访类型按风险等级
                    record.next_follow_up_at,  # 计划到点时间，用于排延迟提醒
                    record.after_emotion_score or 50,
                    record.after_emotion_tags,
                    record.after_risk_level or "LOW",
                )
                created_follow_up.conclusion = care_copy
                self._schedule_reminder(created_follow_up)  # 建单即排延迟提醒

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

        # 闭环：回访完成且需继续跟踪时，自动建下一轮回访并排提醒，事件回流形成闭环
        if follow_up.continue_follow_up:
            # 幂等：已存在更新的回访就不再建下一轮
            existing = db.query(ConsultationFollowUp).filter(
                ConsultationFollowUp.consultation_id == follow_up.consultation_id,
                ConsultationFollowUp.id > follow_up.id,
            ).first()
            if existing is None:
                next_follow_up = FollowUpService(db).create_for_consultation(
                    follow_up.user_id,
                    follow_up.consultation_id,
                    ConsultationEffectEvaluator.follow_up_type(follow_up.risk_level),
                    follow_up.next_follow_up_at,
                    after,
                    follow_up.after_emotion_tags,
                    follow_up.risk_level or "LOW",
                )
                self._schedule_reminder(next_follow_up)  # 下一轮也排延迟提醒

    def _handle_reminder(self, db, event: EmotionalCareEvent) -> None:
        """到点提醒：将回访状态从 PENDING 推进到 REMINDED（实际触达时刻）。"""
        follow_up = db.get(ConsultationFollowUp, event.follow_up_id)
        if follow_up is None:
            logger.warning("skip missing follow-up for reminder id=%s", event.follow_up_id)
            return
        if follow_up.status == "PENDING":
            follow_up.status = "REMINDED"
            logger.info("follow-up %s reminded at %s", follow_up.id, follow_up.planned_at)
        # COMPLETED 状态的回访不再改（已结束），保持幂等
        # TODO: 在此接入真实触达渠道（短信 / 站内信 / push），当前以状态推进作为触达占位

    def _schedule_reminder(self, follow_up: ConsultationFollowUp) -> None:
        """为新建回访排一条延迟提醒；MQ 不可用时降级（不影响回访本身）。

        best-effort：发布失败只记日志不抛，避免 MQ 抖动导致已建的回访单据回滚。
        提醒丢失的代价（用户晚收到提醒）< 回访单据丢失的代价（用户完全没被跟踪）。
        """
        if not follow_up.planned_at:
            logger.warning("follow-up %s has no planned_at, skip reminder", follow_up.id)
            return
        try:
            EmotionalCareEventPublisher().publish_follow_up_reminder(
                follow_up.id,
                follow_up.consultation_id,
                follow_up.user_id,
                follow_up.planned_at,
            )
        except Exception:
            logger.exception("schedule reminder failed follow_up=%s (best-effort)", follow_up.id)


def generate_care_copy(event: EmotionalCareEvent) -> str:
    """根据事件类型生成关怀文案。TODO: 后续可换成 LLM 生成个性化文案。"""
    if event.event_type == EmotionalCareEvent.CONSULTATION_COMPLETED:
        return "感谢你愿意认真面对自己的感受。请按照本次建议循序渐进，也记得给自己留出休息和调整的空间。"
    return "想和你确认一下最近的状态。无论进展快慢，你都可以按自己的节奏继续尝试，也可以随时寻求可信任的人支持。"
