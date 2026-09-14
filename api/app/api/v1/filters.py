from typing import Any

from fastapi import Request

from app.repositories.base import ResourceConfig


def _coerce_filter_value(field: str, raw: str) -> Any:
    if field.startswith("is_") or field.endswith("_verified"):
        return raw.lower() in ("1", "true", "yes")
    if field.endswith("_id") or field in ("category_id", "program_id", "difficulty"):
        try:
            return int(raw)
        except ValueError:
            return raw
    return raw


def parse_list_filters(request: Request, config: ResourceConfig) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    for field in config.filterable_fields:
        raw = request.query_params.get(field)
        if raw is not None and raw != "":
            filters[field] = _coerce_filter_value(field, raw)
    return filters
