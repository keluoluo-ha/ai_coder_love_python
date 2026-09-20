from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas_consultation import (
    CompleteConsultationRequest,
    CompleteFollowUpRequest,
    ConsultationDetailVO,
    EmotionProfileVO,
    FollowUpVO,
    SkipFollowUpRequest,
    StartConsultationRequest,
)
from app.services.consultation_service import ConsultationService
from app.services.emotion_profile_service import EmotionProfileService
from app.services.follow_up_service import FollowUpService

router = APIRouter(prefix="/emotional-care", tags=["emotional-care"])


def _service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, (ValueError, TypeError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="情感咨询服务处理失败")


@router.get("/users/{user_id}/emotion-profile", response_model=EmotionProfileVO)
def profile(user_id: str, db: Session = Depends(get_db)):
    try:
        return EmotionProfileService(db).get_or_create(user_id)
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/consultations", response_model=ConsultationDetailVO)
def start(request: StartConsultationRequest, db: Session = Depends(get_db)):
    try:
        return ConsultationService(db).start(request)
    except Exception as exc:
        db.rollback()
        raise _service_error(exc) from exc


@router.post("/consultations/{consultation_id}/complete", response_model=ConsultationDetailVO)
def complete(consultation_id: int, request: CompleteConsultationRequest, db: Session = Depends(get_db)):
    try:
        return ConsultationService(db).complete(consultation_id, request)
    except Exception as exc:
        db.rollback()
        raise _service_error(exc) from exc


@router.get("/consultations/{consultation_id}", response_model=ConsultationDetailVO)
def detail(consultation_id: int, user_id: str = Query(alias="userId"), db: Session = Depends(get_db)):
    try:
        return ConsultationService(db).detail(consultation_id, user_id)
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/users/{user_id}/consultations", response_model=list[ConsultationDetailVO])
def history(user_id: str, db: Session = Depends(get_db)):
    try:
        return ConsultationService(db).history(user_id)
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/users/{user_id}/follow-ups/pending", response_model=list[FollowUpVO])
def pending_follow_ups(user_id: str, db: Session = Depends(get_db)):
    try:
        return FollowUpService(db).pending(user_id)
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/follow-ups/{follow_up_id}/complete", response_model=FollowUpVO)
def complete_follow_up(
    follow_up_id: int,
    request: CompleteFollowUpRequest,
    user_id: str = Query(alias="userId"),
    db: Session = Depends(get_db),
):
    try:
        return FollowUpService(db).complete(follow_up_id, user_id, request)
    except Exception as exc:
        db.rollback()
        raise _service_error(exc) from exc


@router.post("/follow-ups/{follow_up_id}/skip", response_model=FollowUpVO)
def skip_follow_up(follow_up_id: int, request: SkipFollowUpRequest, db: Session = Depends(get_db)):
    try:
        return FollowUpService(db).skip(follow_up_id, request)
    except Exception as exc:
        db.rollback()
        raise _service_error(exc) from exc
