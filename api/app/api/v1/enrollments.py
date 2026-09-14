from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.dynamic import build_schemas, model_to_dict
from app.models.entities import UserProgramEnrollment, WorkoutSession
from app.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])
_enrollment_read, _, _ = build_schemas(UserProgramEnrollment, "UserProgramEnrollment")
_session_read, _, _ = build_schemas(WorkoutSession, "WorkoutSession")


class EnrollRequest(BaseModel):
    program_id: int


@router.post("", status_code=201)
def enroll(payload: EnrollRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    enrollment = EnrollmentService(db).enroll(user.id, payload.program_id)
    return _enrollment_read.model_validate(model_to_dict(enrollment))


@router.get("/active")
def active_enrollments(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    items = EnrollmentService(db).get_active(user.id)
    return [_enrollment_read.model_validate(model_to_dict(i)) for i in items]


@router.get("/{enrollment_id}/today")
def today(enrollment_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return EnrollmentService(db).get_today(user.id, enrollment_id)


@router.post("/{enrollment_id}/complete-day")
def complete_day(enrollment_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    enrollment = EnrollmentService(db).complete_day(user.id, enrollment_id)
    return _enrollment_read.model_validate(model_to_dict(enrollment))


@router.post("/{enrollment_id}/start-session", status_code=201)
def start_session(enrollment_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    session = EnrollmentService(db).start_workout_session(user.id, enrollment_id)
    return _session_read.model_validate(model_to_dict(session))
