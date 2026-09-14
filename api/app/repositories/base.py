from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Type

from sqlalchemy.orm import Session, defer

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import PaginationParams
from app.models.entities import Exercise


@dataclass
class ResourceConfig:
    name: str
    model: Type
    prefix: str
    tag: str
    policy: str
    owner_field: str | None = None
    pk_fields: tuple[str, ...] = ("id",)
    read_only: bool = False
    filterable_fields: tuple[str, ...] = ()
    ownership_hops: tuple[tuple[str, Type], ...] = ()
    parent_owner_field: str = "user_id"
    list_omit_fields: tuple[str, ...] = ()


class BaseRepository:
    def __init__(self, db: Session, config: ResourceConfig) -> None:
        self.db = db
        self.config = config
        self.model = config.model

    def get_or_404(self, pk_values: dict[str, Any]) -> Any:
        query = self.db.query(self.model)
        for key in self.config.pk_fields:
            query = query.filter(getattr(self.model, key) == pk_values[key])
        instance = query.first()
        if not instance:
            keys = ", ".join(f"{k}={v}" for k, v in pk_values.items())
            raise NotFoundError(self.config.name, keys)
        return instance

    def list(
        self,
        pagination: PaginationParams,
        owner_id: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[Any], int]:
        query = self.db.query(self.model)
        if self.config.list_omit_fields:
            query = query.options(
                *(defer(getattr(self.model, field)) for field in self.config.list_omit_fields)
            )

        if owner_id and self.config.owner_field:
            query = query.filter(getattr(self.model, self.config.owner_field) == owner_id)
        elif owner_id and self.config.ownership_hops:
            current_model = self.model
            parent_model = None
            for fk_field, hop_model in self.config.ownership_hops:
                query = query.join(hop_model, getattr(current_model, fk_field) == hop_model.id)
                current_model = hop_model
                parent_model = hop_model
            if parent_model is not None:
                query = query.filter(getattr(parent_model, self.config.parent_owner_field) == owner_id)

        if filters:
            for key, value in filters.items():
                if key in self.config.filterable_fields and value is not None:
                    query = query.filter(getattr(self.model, key) == value)

        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.page_size).all()
        return items, total

    def verify_parent_ownership(self, data: dict[str, Any] | Any, user_id: str, role: str) -> None:
        if role == "admin" or not self.config.ownership_hops:
            return

        hops = self.config.ownership_hops
        fk_field, model = hops[0]
        fk_val = data[fk_field] if isinstance(data, dict) else getattr(data, fk_field)
        current = self.db.query(model).filter(model.id == fk_val).first()
        if not current:
            raise ForbiddenError()

        for fk_field, hop_model in hops[1:]:
            fk_val = getattr(current, fk_field)
            current = self.db.query(hop_model).filter(hop_model.id == fk_val).first()
            if not current:
                raise ForbiddenError()

        if getattr(current, self.config.parent_owner_field, None) != user_id:
            raise ForbiddenError()

    def create(self, data: dict[str, Any]) -> Any:
        data = dict(data)
        if self.model is Exercise:
            from app.services.exercise_catalog_validate import validate_exercise_catalog_fields

            data = validate_exercise_catalog_fields(data)
        data = self._stamp_timestamps(data, is_create=True)
        instance = self.model(**data)
        self.db.add(instance)
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise ConflictError("Không thể lưu dữ liệu (xung đột hoặc ràng buộc).") from exc
        self.db.refresh(instance)
        return instance

    def update(self, pk_values: dict[str, Any], data: dict[str, Any]) -> Any:
        instance = self.get_or_404(pk_values)
        data = dict(data)
        if self.model is Exercise:
            from app.services.exercise_catalog_validate import validate_exercise_catalog_fields

            data = validate_exercise_catalog_fields(data)
        data = self._stamp_timestamps(data, is_create=False)
        for key, value in data.items():
            if value is not None and hasattr(instance, key):
                setattr(instance, key, value)
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise ConflictError("Không thể cập nhật dữ liệu (xung đột hoặc ràng buộc).") from exc
        self.db.refresh(instance)
        return instance

    def delete(self, pk_values: dict[str, Any]) -> None:
        instance = self.get_or_404(pk_values)
        self.db.delete(instance)
        self.db.commit()

    def check_owner(self, instance: Any, user_id: str, role: str) -> bool:
        if role == "admin":
            return True
        if self.config.owner_field:
            return getattr(instance, self.config.owner_field, None) == user_id
        if self.config.ownership_hops:
            try:
                self.verify_parent_ownership(instance, user_id, role)
                return True
            except ForbiddenError:
                return False
        return False

    def _stamp_timestamps(self, data: dict[str, Any], *, is_create: bool) -> dict[str, Any]:
        now = datetime.now(UTC)
        columns = self.model.__mapper__.columns
        if is_create and "created_at" in columns and "created_at" not in data:
            data["created_at"] = now
        if "updated_at" in columns:
            data["updated_at"] = now
        return data
