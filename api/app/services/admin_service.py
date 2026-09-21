from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import (
    Exercise,
    Food,
    PaymentTransaction,
    Subscription,
    User,
    WorkoutSession,
)


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def stats(self) -> dict:
        return {
            "users": self.db.query(func.count(User.id)).scalar() or 0,
            "exercises": self.db.query(func.count(Exercise.id)).scalar() or 0,
            "foods": self.db.query(func.count(Food.id)).scalar() or 0,
            "workout_sessions": self.db.query(func.count(WorkoutSession.id)).scalar() or 0,
            "active_subscriptions": self.db.query(func.count(Subscription.id))
            .filter(Subscription.status == "active")
            .scalar()
            or 0,
            "payments_completed": self.db.query(func.count(PaymentTransaction.id))
            .filter(PaymentTransaction.status == "completed")
            .scalar()
            or 0,
        }
