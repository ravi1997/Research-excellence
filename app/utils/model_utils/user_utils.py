from __future__ import annotations

import json
from typing import Dict, Iterable, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.User import Role, User, UserRole, UserSettings
from app.security_utils import audit_log
from app.utils.logging_utils import get_logger, log_context

from .base import (
    _sanitize_payload,
    _serialize_value,
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)

logger = get_logger("user_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record user audit", extra={"event": event})


def _normalize_role(role: Role | str) -> Role:
    if isinstance(role, Role):
        return role
    if isinstance(role, str):
        return Role(role)
    raise ValueError(f"Unsupported role value: {role!r}")


def create_user(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> User:
    ctx = {"function": "create_user", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="user_utils", action="create_user", actor_id=actor_id):
        logger.info("create_user commit=%s attributes=%s", commit, sanitized)
    user = create_instance(
        User,
        commit=commit,
        actor_id=actor_id,
        event_name="user.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_user complete id=%s", _serialize_value(getattr(user, "id", None)))
    return user


def get_user_by_id(
    user_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[User]:
    ctx = {"function": "get_user_by_id", **(context or {})}
    with log_context(module="user_utils", action="get_user_by_id", actor_id=actor_id):
        logger.info("get_user_by_id id=%s", _serialize_value(user_id))
    user = get_instance(
        User,
        user_id,
        actor_id=actor_id,
        event_name="user.get",
        context=ctx,
    )
    logger.info("get_user_by_id resolved id=%s found=%s", _serialize_value(user_id), user is not None)
    return user


def list_users(
    *,
    filters: Optional[Sequence] = None,
    eager: bool = False,
    order_by=None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[User]:
    options = (
        [
            joinedload(User.role_associations),
            joinedload(User.department),
            joinedload(User.category),
        ]
        if eager
        else None
    )
    ctx = {
        "function": "list_users",
        "eager": eager,
        "limit": limit,
        "offset": offset,
        **(context or {}),
    }
    users = list_instances(
        User,
        filters=filters,
        order_by=order_by,
        query_options=options,
        limit=limit,
        offset=offset,
        actor_id=actor_id,
        event_name="user.list",
        context=ctx,
    )
    with log_context(module="user_utils", action="list_users", actor_id=actor_id):
        logger.info(
            "list_users complete eager=%s limit=%s offset=%s count=%s",
            eager,
            limit,
            offset,
            len(users),
        )
    return users


def update_user(
    user: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> User:
    ctx = {
        "function": "update_user",
        "user_id": _serialize_value(getattr(user, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="user_utils", action="update_user", actor_id=actor_id):
        logger.info("update_user target_id=%s attributes=%s", ctx.get("user_id"), sanitized)
    updated = update_instance(
        user,
        commit=commit,
        actor_id=actor_id,
        event_name="user.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_user complete target_id=%s", ctx.get("user_id"))
    return updated


def delete_user(
    user_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_user", **(context or {})}
    with log_context(module="user_utils", action="delete_user", actor_id=actor_id):
        logger.info("delete_user target=%s", _serialize_value(user_or_id))
    delete_instance(
        User,
        user_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="user.delete",
        context=ctx,
    )
    logger.info("delete_user completed target=%s", _serialize_value(user_or_id))


def set_user_roles(
    user: User,
    roles: Iterable[Role],
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> User:
    desired_roles = {_normalize_role(role) for role in roles}
    current_roles = {association.role for association in user.role_associations}

    ctx = {
        "function": "set_user_roles",
        "user_id": _serialize_value(getattr(user, "id", None)),
        "desired_roles": [role.value if isinstance(role, Role) else str(role) for role in desired_roles],
        **(context or {}),
    }
    removed_roles = []
    added_roles = []

    with log_context(module="user_utils", action="set_user_roles", actor_id=actor_id):
        logger.info(
            "set_user_roles user_id=%s desired=%s current=%s",
            ctx["user_id"],
            ctx["desired_roles"],
            [role.value for role in current_roles],
        )

        for association in list(user.role_associations):
            if association.role not in desired_roles:
                removed_roles.append(association.role.value)
                user.role_associations.remove(association)

        for role in desired_roles:
            if role not in current_roles:
                user.role_associations.append(UserRole(role=role))
                added_roles.append(role.value)

    if commit:
        db.session.commit()
        _audit(
            "user.roles.update",
            actor_id,
            {
                "operation": "set_user_roles",
                "user_id": ctx["user_id"],
                "desired_roles": ctx["desired_roles"],
                "added_roles": added_roles,
                "removed_roles": removed_roles,
            },
        )

    logger.info(
        "set_user_roles completed user_id=%s added=%s removed=%s",
        ctx["user_id"],
        added_roles,
        removed_roles,
    )
    return user


def deactivate_user(
    user: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> User:
    ctx = {
        "function": "deactivate_user",
        "user_id": _serialize_value(getattr(user, "id", None)),
        **(context or {}),
    }
    with log_context(module="user_utils", action="deactivate_user", actor_id=actor_id):
        logger.info("deactivate_user target_id=%s", ctx.get("user_id"))
        user.is_active = False
    if commit:
        db.session.commit()
        _audit(
            "user.deactivate",
            actor_id,
            {
                "operation": "deactivate_user",
                "user_id": ctx["user_id"],
            },
        )
    logger.info("deactivate_user complete target_id=%s", ctx.get("user_id"))
    return user


def activate_user(
    user: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> User:
    ctx = {
        "function": "activate_user",
        "user_id": _serialize_value(getattr(user, "id", None)),
        **(context or {}),
    }
    with log_context(module="user_utils", action="activate_user", actor_id=actor_id):
        logger.info("activate_user target_id=%s", ctx.get("user_id"))
        user.is_active = True
    if commit:
        db.session.commit()
        _audit(
            "user.activate",
            actor_id,
            {
                "operation": "activate_user",
                "user_id": ctx["user_id"],
            },
        )
    logger.info("activate_user complete target_id=%s", ctx.get("user_id"))
    return user


def create_user_settings(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> UserSettings:
    ctx = {"function": "create_user_settings", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="user_utils", action="create_user_settings", actor_id=actor_id):
        logger.info("create_user_settings commit=%s attributes=%s", commit, sanitized)
    user_settings = create_instance(
        UserSettings,
        commit=commit,
        actor_id=actor_id,
        event_name="user_settings.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_user_settings complete id=%s", _serialize_value(getattr(user_settings, "id", None)))
    return user_settings


def get_user_settings_by_id(
    settings_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[UserSettings]:
    ctx = {"function": "get_user_settings_by_id", **(context or {})}
    with log_context(module="user_utils", action="get_user_settings_by_id", actor_id=actor_id):
        logger.info("get_user_settings_by_id id=%s", _serialize_value(settings_id))
    user_settings = get_instance(
        UserSettings,
        settings_id,
        actor_id=actor_id,
        event_name="user_settings.get",
        context=ctx,
    )
    logger.info("get_user_settings_by_id resolved id=%s found=%s", _serialize_value(settings_id), user_settings is not None)
    return user_settings


def get_user_settings_by_user_id(
    user_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[UserSettings]:
    ctx = {"function": "get_user_settings_by_user_id", "user_id": _serialize_value(user_id), **(context or {})}
    with log_context(module="user_utils", action="get_user_settings_by_user_id", actor_id=actor_id):
        logger.info("get_user_settings_by_user_id user_id=%s", _serialize_value(user_id))
    user_settings = db.session.query(UserSettings).filter_by(user_id=user_id).first()
    logger.info("get_user_settings_by_user_id resolved user_id=%s found=%s", _serialize_value(user_id), user_settings is not None)
    if user_settings:
        _audit(
            "user_settings.get",
            actor_id,
            {
                "operation": "get_user_settings_by_user_id",
                "user_id": _serialize_value(user_id),
                "settings_id": _serialize_value(getattr(user_settings, "id", None)),
            },
        )
    return user_settings


def list_user_settings(
    *,
    filters: Optional[Sequence] = None,
    order_by=None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[UserSettings]:
    ctx = {
        "function": "list_user_settings",
        "limit": limit,
        "offset": offset,
        **(context or {}),
    }
    user_settings_list = list_instances(
        UserSettings,
        filters=filters,
        order_by=order_by,
        limit=limit,
        offset=offset,
        actor_id=actor_id,
        event_name="user_settings.list",
        context=ctx,
    )
    with log_context(module="user_utils", action="list_user_settings", actor_id=actor_id):
        logger.info(
            "list_user_settings complete limit=%s offset=%s count=%s",
            limit,
            offset,
            len(user_settings_list),
        )
    return user_settings_list


def update_user_settings(
    user_settings: UserSettings,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> UserSettings:
    ctx = {
        "function": "update_user_settings",
        "settings_id": _serialize_value(getattr(user_settings, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="user_utils", action="update_user_settings", actor_id=actor_id):
        logger.info("update_user_settings target_id=%s attributes=%s", ctx.get("settings_id"), sanitized)
    updated = update_instance(
        user_settings,
        commit=commit,
        actor_id=actor_id,
        event_name="user_settings.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_user_settings complete target_id=%s", ctx.get("settings_id"))
    return updated


def delete_user_settings(
    user_settings_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_user_settings", **(context or {})}
    with log_context(module="user_utils", action="delete_user_settings", actor_id=actor_id):
        logger.info("delete_user_settings target=%s", _serialize_value(user_settings_or_id))
    delete_instance(
        UserSettings,
        user_settings_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="user_settings.delete",
        context=ctx,
    )
    logger.info("delete_user_settings completed target=%s", _serialize_value(user_settings_or_id))


def create_user_role(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> UserRole:
    ctx = {"function": "create_user_role", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="user_utils", action="create_user_role", actor_id=actor_id):
        logger.info("create_user_role commit=%s attributes=%s", commit, sanitized)
    user_role = create_instance(
        UserRole,
        commit=commit,
        actor_id=actor_id,
        event_name="user_role.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_user_role complete id=%s", _serialize_value(getattr(user_role, "id", None)))
    return user_role


def get_user_role_by_id(
    role_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[UserRole]:
    ctx = {"function": "get_user_role_by_id", **(context or {})}
    with log_context(module="user_utils", action="get_user_role_by_id", actor_id=actor_id):
        logger.info("get_user_role_by_id id=%s", _serialize_value(role_id))
    user_role = get_instance(
        UserRole,
        role_id,
        actor_id=actor_id,
        event_name="user_role.get",
        context=ctx,
    )
    logger.info("get_user_role_by_id resolved id=%s found=%s", _serialize_value(role_id), user_role is not None)
    return user_role


def get_user_roles_by_user_id(
    user_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[UserRole]:
    ctx = {"function": "get_user_roles_by_user_id", "user_id": _serialize_value(user_id), **(context or {})}
    with log_context(module="user_utils", action="get_user_roles_by_user_id", actor_id=actor_id):
        logger.info("get_user_roles_by_user_id user_id=%s", _serialize_value(user_id))
    
    user_roles = db.session.query(UserRole).filter_by(user_id=user_id).all()
    logger.info("get_user_roles_by_user_id found %d roles for user_id=%s", len(user_roles), _serialize_value(user_id))
    
    if user_roles:
        _audit(
            "user_role.get_for_user",
            actor_id,
            {
                "operation": "get_user_roles_by_user_id",
                "user_id": _serialize_value(user_id),
                "role_count": len(user_roles),
                "role_values": [ur.role.value for ur in user_roles]
            },
        )
    return user_roles


def list_user_roles(
    *,
    filters: Optional[Sequence] = None,
    order_by=None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[UserRole]:
    ctx = {
        "function": "list_user_roles",
        "limit": limit,
        "offset": offset,
        **(context or {}),
    }
    user_roles_list = list_instances(
        UserRole,
        filters=filters,
        order_by=order_by,
        limit=limit,
        offset=offset,
        actor_id=actor_id,
        event_name="user_role.list",
        context=ctx,
    )
    with log_context(module="user_utils", action="list_user_roles", actor_id=actor_id):
        logger.info(
            "list_user_roles complete limit=%s offset=%s count=%s",
            limit,
            offset,
            len(user_roles_list),
        )
    return user_roles_list


def update_user_role(
    user_role: UserRole,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> UserRole:
    ctx = {
        "function": "update_user_role",
        "role_id": _serialize_value(getattr(user_role, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="user_utils", action="update_user_role", actor_id=actor_id):
        logger.info("update_user_role target_id=%s attributes=%s", ctx.get("role_id"), sanitized)
    updated = update_instance(
        user_role,
        commit=commit,
        actor_id=actor_id,
        event_name="user_role.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_user_role complete target_id=%s", ctx.get("role_id"))
    return updated


def delete_user_role(
    user_role_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_user_role", **(context or {})}
    with log_context(module="user_utils", action="delete_user_role", actor_id=actor_id):
        logger.info("delete_user_role target=%s", _serialize_value(user_role_or_id))
    delete_instance(
        UserRole,
        user_role_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="user_role.delete",
        context=ctx,
    )
    logger.info("delete_user_role completed target=%s", _serialize_value(user_role_or_id))
