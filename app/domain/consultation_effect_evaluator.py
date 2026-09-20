class ConsultationEffectEvaluator:
    EFFECT_SIGNIFICANT = "明显改善"
    EFFECT_IMPROVED = "有所改善"
    EFFECT_STABLE = "基本稳定"
    EFFECT_LIMITED = "效果有限"
    EFFECT_WORSENED = "情况恶化"

    TREND_RISING = "RISING"
    TREND_FALLING = "FALLING"
    TREND_STABLE = "STABLE"
    FOLLOW_UP_RISK_REVIEW = "RISK_REVIEW"
    FOLLOW_UP_EMOTION_RECHECK = "EMOTION_RECHECK"

    @classmethod
    def effect_level(cls, improvement_score: int, after_risk: str | None, before_risk: str | None) -> str:
        if cls.risk_rank(after_risk) > cls.risk_rank(before_risk) or cls.is_high_risk(after_risk):
            return cls.EFFECT_WORSENED
        if improvement_score >= 25:
            return cls.EFFECT_SIGNIFICANT
        if improvement_score >= 10:
            return cls.EFFECT_IMPROVED
        if improvement_score >= -9:
            return cls.EFFECT_STABLE
        if improvement_score >= -24:
            return cls.EFFECT_LIMITED
        return cls.EFFECT_WORSENED

    @classmethod
    def should_follow_up(cls, effect_level: str, risk_level: str | None) -> bool:
        return cls.is_high_risk(risk_level) or effect_level != cls.EFFECT_SIGNIFICANT

    @classmethod
    def default_follow_up_days(cls, effect_level: str, risk_level: str | None) -> int:
        if cls.is_high_risk(risk_level) or effect_level == cls.EFFECT_WORSENED:
            return 1
        if effect_level == cls.EFFECT_LIMITED:
            return 3
        if effect_level == cls.EFFECT_STABLE:
            return 5
        return 7

    @classmethod
    def follow_up_type(cls, risk_level: str | None) -> str:
        return cls.FOLLOW_UP_RISK_REVIEW if cls.is_high_risk(risk_level) else cls.FOLLOW_UP_EMOTION_RECHECK

    @classmethod
    def trend_by_delta(cls, improvement_score: int) -> str:
        if improvement_score >= 10:
            return cls.TREND_RISING
        if improvement_score <= -10:
            return cls.TREND_FALLING
        return cls.TREND_STABLE

    @staticmethod
    def trend_description(improvement_score: int) -> str:
        if improvement_score >= 10:
            return "改善"
        if improvement_score <= -10:
            return "下降"
        return "基本稳定"

    @classmethod
    def is_high_risk(cls, risk_level: str | None) -> bool:
        return cls.risk_rank(risk_level) >= 2

    @staticmethod
    def risk_rank(risk_level: str | None) -> int:
        return {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1}.get((risk_level or "").upper(), 0)

    @staticmethod
    def blank_to_default(value: str | None, fallback: str) -> str:
        return value.strip() if value and value.strip() else fallback
