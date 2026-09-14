from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import JSON
from sqlalchemy.inspection import inspect as sa_inspect

from app.core.permissions import SENSITIVE_FIELDS, UPDATE_DENYLIST

SERVER_MANAGED_FIELDS = frozenset({"created_at", "updated_at"})


def model_to_dict(instance: Any, *, omit: frozenset[str] | None = None) -> dict[str, Any]:
    skip = omit or frozenset()
    result: dict[str, Any] = {}
    mapper = sa_inspect(instance.__class__)
    for column in mapper.columns:
        name = column.key
        if name in SENSITIVE_FIELDS or name in skip:
            continue
        value = getattr(instance, name)
        if isinstance(value, datetime):
            value = value.isoformat()
        result[name] = value
    return result


def _column_type(column) -> Any:
    if isinstance(column.type, JSON):
        return Any
    try:
        return column.type.python_type
    except NotImplementedError:
        return Any


def _has_default(column) -> bool:
    return column.server_default is not None or column.default is not None


def build_schemas(
    model: type,
    name: str,
    *,
    exclude_create_fields: frozenset[str] | None = None,
) -> tuple[type[BaseModel], type[BaseModel], type[BaseModel]]:
    """Generate Read / Create / Update Pydantic schemas from SQLAlchemy model."""
    exclude_create = (
        SERVER_MANAGED_FIELDS | UPDATE_DENYLIST | (exclude_create_fields or frozenset())
    )
    exclude_update = SERVER_MANAGED_FIELDS | UPDATE_DENYLIST | (exclude_create_fields or frozenset())
    mapper = sa_inspect(model)
    read_fields: dict[str, Any] = {}
    create_fields: dict[str, Any] = {}
    update_fields: dict[str, Any] = {}

    for column in mapper.columns:
        col_name = column.key
        if col_name in SENSITIVE_FIELDS:
            continue

        python_type = _column_type(column)
        if col_name.endswith("_at") or col_name == "updated_at":
            read_fields[col_name] = (datetime | str | None, None)
            continue

        if column.primary_key and column.autoincrement is True:
            read_fields[col_name] = (int | None, None)
            continue
        if column.primary_key:
            read_fields[col_name] = (python_type, ...)
            if col_name not in exclude_create:
                create_fields[col_name] = (python_type, ...)
            continue

        optional_create = column.nullable or _has_default(column) or col_name in exclude_create

        if column.nullable:
            read_fields[col_name] = (python_type | None, None)
            if col_name not in exclude_create:
                create_fields[col_name] = (python_type | None, None)
            if col_name not in exclude_update:
                update_fields[col_name] = (python_type | None, None)
        else:
            read_fields[col_name] = (python_type, ...)
            if col_name not in exclude_update:
                update_fields[col_name] = (python_type | None, None)
            if col_name not in exclude_create:
                if optional_create:
                    create_fields[col_name] = (python_type | None, None)
                else:
                    create_fields[col_name] = (python_type, ...)

    read_schema = create_model(
        f"{name}Read",
        __config__=ConfigDict(from_attributes=True),
        **read_fields,
    )
    create_schema = create_model(f"{name}Create", **create_fields)
    update_schema = create_model(
        f"{name}Update", **{k: (v[0], None) for k, v in update_fields.items()}
    )
    return read_schema, create_schema, update_schema
