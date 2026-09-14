from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.filters import parse_list_filters
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, get_current_user_optional, require_admin
from app.core.exceptions import ForbiddenError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.core.permissions import AccessPolicy
from app.repositories.base import BaseRepository, ResourceConfig
from app.schemas.dynamic import build_schemas, model_to_dict


def _can_read(policy: AccessPolicy, user: CurrentUser | None) -> bool:
    if policy == AccessPolicy.PUBLIC_READ:
        return True
    if policy == AccessPolicy.ADMIN:
        return user is not None and user.role.value == "admin"
    return user is not None


def _can_write(policy: AccessPolicy, user: CurrentUser | None, admin_required: bool) -> bool:
    if admin_required:
        return user is not None and user.role.value == "admin"
    if policy == AccessPolicy.ADMIN:
        return user is not None and user.role.value == "admin"
    if policy == AccessPolicy.TRAINER:
        return user is not None and user.role.value in ("trainer", "admin")
    if policy in (AccessPolicy.OWNER, AccessPolicy.AUTH_READ):
        return user is not None
    if policy == AccessPolicy.PUBLIC_READ:
        return user is not None and user.role.value == "admin"
    return False


def _owner_id_for_list(policy: AccessPolicy, config: ResourceConfig, user: CurrentUser | None) -> str | None:
    if not user:
        return None
    if policy == AccessPolicy.OWNER:
        return user.id
    if policy == AccessPolicy.TRAINER and config.owner_field:
        return user.id
    if policy == AccessPolicy.AUTH_READ and config.ownership_hops:
        return user.id
    return None


def _assert_access(
    repository: BaseRepository,
    instance: Any,
    user: CurrentUser,
    policy: AccessPolicy,
    config: ResourceConfig,
) -> None:
    if policy == AccessPolicy.ADMIN and user.role.value != "admin":
        raise ForbiddenError()
    if policy == AccessPolicy.OWNER and not repository.check_owner(instance, user.id, user.role.value):
        raise ForbiddenError()
    if policy == AccessPolicy.TRAINER:
        if user.role.value == "admin":
            return
        if user.role.value != "trainer":
            raise ForbiddenError()
        owner_field = config.owner_field
        if owner_field and getattr(instance, owner_field, None) != user.id:
            raise ForbiddenError()
    if policy == AccessPolicy.AUTH_READ and config.ownership_hops:
        repository.verify_parent_ownership(instance, user.id, user.role.value)


def create_crud_router(config: ResourceConfig) -> APIRouter:
    exclude_create = frozenset({config.owner_field}) if config.owner_field else frozenset()
    read_schema, create_schema, update_schema = build_schemas(
        config.model,
        config.name,
        exclude_create_fields=exclude_create,
    )
    router = APIRouter(prefix=f"/{config.prefix}", tags=[config.tag])
    policy = AccessPolicy(config.policy)

    pk_names = config.pk_fields

    if len(pk_names) == 1:
        pk_name = pk_names[0]

        @router.get("", response_model=PaginatedResponse[read_schema])  # type: ignore[valid-type]
        def list_items(
            request: Request,
            pagination: Annotated[PaginationParams, Depends()],
            db: Session = Depends(get_db),
            user: CurrentUser | None = Depends(get_current_user_optional),
        ):
            if not _can_read(policy, user):
                raise ForbiddenError()
            repository = BaseRepository(db, config)
            owner_id = _owner_id_for_list(policy, config, user)
            filters = parse_list_filters(request, config)
            items, total = repository.list(pagination, owner_id, filters)
            omit = frozenset(config.list_omit_fields)
            payload = []
            for item in items:
                data = model_to_dict(item, omit=omit)
                for field in omit:
                    data.setdefault(field, "")
                payload.append(read_schema.model_validate(data))
            return PaginatedResponse.create(
                payload,
                total,
                pagination.page,
                pagination.page_size,
            )

        @router.get(f"/{{{pk_name}}}", response_model=read_schema)  # type: ignore[valid-type]
        def get_item(
            request: Request,
            db: Session = Depends(get_db),
            user: CurrentUser | None = Depends(get_current_user_optional),
        ):
            if not _can_read(policy, user):
                raise ForbiddenError()
            pk_value = request.path_params[pk_name]
            repository = BaseRepository(db, config)
            instance = repository.get_or_404({pk_name: _cast_pk(pk_value, config.model, pk_name)})
            if user and policy in (
                AccessPolicy.OWNER,
                AccessPolicy.TRAINER,
                AccessPolicy.AUTH_READ,
                AccessPolicy.ADMIN,
            ):
                _assert_access(repository, instance, user, policy, config)
            return read_schema.model_validate(model_to_dict(instance))

        if not config.read_only:

            @router.post("", response_model=read_schema, status_code=201)  # type: ignore[valid-type]
            def create_item(
                payload: create_schema,  # type: ignore[valid-type]
                db: Session = Depends(get_db),
                user: CurrentUser = Depends(get_current_user),
            ):
                admin_only = policy == AccessPolicy.PUBLIC_READ
                if not _can_write(policy, user, admin_only):
                    raise ForbiddenError()
                repository = BaseRepository(db, config)
                data = payload.model_dump(exclude_unset=True)
                if config.owner_field and policy == AccessPolicy.OWNER:
                    data[config.owner_field] = user.id
                if policy == AccessPolicy.TRAINER and config.owner_field:
                    data[config.owner_field] = user.id
                if policy == AccessPolicy.AUTH_READ and config.ownership_hops:
                    repository.verify_parent_ownership(data, user.id, user.role.value)
                instance = repository.create(data)
                return read_schema.model_validate(model_to_dict(instance))

            @router.patch(f"/{{{pk_name}}}", response_model=read_schema)  # type: ignore[valid-type]
            def update_item(
                request: Request,
                payload: update_schema,  # type: ignore[valid-type]
                db: Session = Depends(get_db),
                user: CurrentUser = Depends(get_current_user),
            ):
                admin_only = policy == AccessPolicy.PUBLIC_READ
                if not _can_write(policy, user, admin_only):
                    raise ForbiddenError()
                pk_value = request.path_params[pk_name]
                repository = BaseRepository(db, config)
                pk = {pk_name: _cast_pk(pk_value, config.model, pk_name)}
                instance = repository.get_or_404(pk)
                _assert_access(repository, instance, user, policy, config)
                data = payload.model_dump(exclude_unset=True)
                if config.owner_field:
                    data.pop(config.owner_field, None)
                instance = repository.update(pk, data)
                return read_schema.model_validate(model_to_dict(instance))

            @router.delete(f"/{{{pk_name}}}", status_code=204)
            def delete_item(
                request: Request,
                db: Session = Depends(get_db),
                user: CurrentUser = Depends(get_current_user),
            ):
                admin_only = policy == AccessPolicy.PUBLIC_READ
                if not _can_write(policy, user, admin_only):
                    raise ForbiddenError()
                pk_value = request.path_params[pk_name]
                repository = BaseRepository(db, config)
                pk = {pk_name: _cast_pk(pk_value, config.model, pk_name)}
                instance = repository.get_or_404(pk)
                _assert_access(repository, instance, user, policy, config)
                repository.delete(pk)

    else:
        pk1, pk2 = pk_names

        @router.get("", response_model=PaginatedResponse[read_schema])  # type: ignore[valid-type]
        def list_items(
            pagination: Annotated[PaginationParams, Depends()],
            db: Session = Depends(get_db),
            user: CurrentUser | None = Depends(get_current_user_optional),
        ):
            if not _can_read(policy, user):
                raise ForbiddenError()
            repository = BaseRepository(db, config)
            items, total = repository.list(pagination)
            return PaginatedResponse.create(
                [read_schema.model_validate(model_to_dict(i)) for i in items],
                total,
                pagination.page,
                pagination.page_size,
            )

        @router.get(f"/{{{pk1}}}/{{{pk2}}}", response_model=read_schema)  # type: ignore[valid-type]
        def get_item(
            request: Request,
            db: Session = Depends(get_db),
            user: CurrentUser | None = Depends(get_current_user_optional),
        ):
            if not _can_read(policy, user):
                raise ForbiddenError()
            repository = BaseRepository(db, config)
            pk = {
                pk1: _cast_pk(request.path_params[pk1], config.model, pk1),
                pk2: _cast_pk(request.path_params[pk2], config.model, pk2),
            }
            instance = repository.get_or_404(pk)
            return read_schema.model_validate(model_to_dict(instance))

        if not config.read_only:

            @router.post("", response_model=read_schema, status_code=201)  # type: ignore[valid-type]
            def create_item(
                payload: create_schema,  # type: ignore[valid-type]
                db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_admin),
            ):
                repository = BaseRepository(db, config)
                instance = repository.create(payload.model_dump(exclude_unset=True))
                return read_schema.model_validate(model_to_dict(instance))

            @router.delete(f"/{{{pk1}}}/{{{pk2}}}", status_code=204)
            def delete_item(
                request: Request,
                db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_admin),
            ):
                repository = BaseRepository(db, config)
                pk = {
                    pk1: _cast_pk(request.path_params[pk1], config.model, pk1),
                    pk2: _cast_pk(request.path_params[pk2], config.model, pk2),
                }
                repository.delete(pk)

    return router


def _cast_pk(value: str, model: type, field: str) -> Any:
    from sqlalchemy import Integer

    col = getattr(model, field).property.columns[0]
    if isinstance(col.type, Integer):
        return int(value)
    return value
