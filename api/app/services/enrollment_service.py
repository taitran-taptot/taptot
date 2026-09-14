from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.entities import Program, ProgramDay, UserProgramEnrollment, WorkoutSession


class EnrollmentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def enroll(self, user_id: str, program_id: int) -> UserProgramEnrollment:
        program = self.db.get(Program, program_id)
        if not program or not program.is_published:
            raise NotFoundError("Program", program_id)

        existing = (
            self.db.query(UserProgramEnrollment)
            .filter(
                UserProgramEnrollment.user_id == user_id,
                UserProgramEnrollment.program_id == program_id,
                UserProgramEnrollment.status == "active",
            )
            .first()
        )
        if existing:
            raise ConflictError("Already enrolled in this program")

        enrollment = UserProgramEnrollment(
            user_id=user_id,
            program_id=program_id,
            started_at=date.today(),
            current_day=1,
            status="active",
        )
        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def get_active(self, user_id: str) -> list[UserProgramEnrollment]:
        return (
            self.db.query(UserProgramEnrollment)
            .filter(
                UserProgramEnrollment.user_id == user_id,
                UserProgramEnrollment.status == "active",
            )
            .all()
        )

    def complete_day(self, user_id: str, enrollment_id: int) -> UserProgramEnrollment:
        enrollment = self._get_owned(user_id, enrollment_id)
        program = self.db.get(Program, enrollment.program_id)
        if not program:
            raise NotFoundError("Program", enrollment.program_id)

        if enrollment.current_day >= program.duration_days:
            enrollment.status = "completed"
            enrollment.completed_at = date.today()
        else:
            enrollment.current_day += 1

        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def get_today(self, user_id: str, enrollment_id: int) -> dict:
        enrollment = self._get_owned(user_id, enrollment_id)
        day = (
            self.db.query(ProgramDay)
            .filter(
                ProgramDay.program_id == enrollment.program_id,
                ProgramDay.day_number == enrollment.current_day,
            )
            .first()
        )
        if not day:
            raise NotFoundError("ProgramDay", enrollment.current_day)

        from app.services.search_service import SearchService

        detail = SearchService(self.db).get_program_detail(enrollment.program_id)
        today = next((d for d in detail["days"] if d["day_number"] == enrollment.current_day), None)
        return {
            "enrollment_id": enrollment.id,
            "current_day": enrollment.current_day,
            "status": enrollment.status,
            "program": {
                "id": detail["id"],
                "title_vi": detail["title_vi"],
                "slug": detail["slug"],
            },
            "today": today,
        }

    def start_workout_session(self, user_id: str, enrollment_id: int) -> WorkoutSession:
        enrollment = self._get_owned(user_id, enrollment_id)
        day = (
            self.db.query(ProgramDay)
            .filter(
                ProgramDay.program_id == enrollment.program_id,
                ProgramDay.day_number == enrollment.current_day,
            )
            .first()
        )
        if not day:
            raise BadRequestError("No workout day for current progress")

        session = WorkoutSession(
            user_id=user_id,
            program_day_id=day.id,
            enrollment_id=enrollment.id,
            title_vi=day.title_vi or f"Ngày {day.day_number}",
            started_at=datetime.now(UTC),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def _get_owned(self, user_id: str, enrollment_id: int) -> UserProgramEnrollment:
        enrollment = self.db.get(UserProgramEnrollment, enrollment_id)
        if not enrollment or str(enrollment.user_id) != user_id:
            raise NotFoundError("Enrollment", enrollment_id)
        return enrollment
