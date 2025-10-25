from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Type, TypeVar, Union

from sqlalchemy.orm import Query

from app.extensions import db
from app.security_utils import audit_log
from app.utils.logging_utils import get_logger, log_context

ModelType = TypeVar("ModelType", bound=db.Model)

_SENSITIVE_TOKENS = ("password", "secret", "token", "otp", "key", "passcode", "credential")


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _sanitize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        lower = key.lower()
        if any(token in lower for token in _SENSITIVE_TOKENS):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = _serialize_value(value)
    return sanitized


def _instance_identity(instance: ModelType) -> Optional[str]:
    try:
        state = db.inspect(instance)
        if state.identity:
            return ":".join(_serialize_value(part) for part in state.identity)
    except Exception:
        pass
    for attr in ("id", "uuid", "uid", "pk"):
        if hasattr(instance, attr):
            value = getattr(instance, attr)
            if value is not None:
                return str(value)
    return None


def _emit_audit(event_name: str, actor_id: Optional[str], detail: Dict[str, Any]) -> None:
    try:
        audit_log(
            event_name,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(detail, default=_serialize_value),
        )
    except Exception:
        get_logger("model_utils").exception("Failed to record audit log", extra={"event": event_name})


def _build_context(model_name: str, action: str, actor_id: Optional[str], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    built = {"model": model_name, "action": action}
    if actor_id is not None:
        built["actor_id"] = str(actor_id)
    if context:
        for key, value in context.items():
            built[f"ctx_{key}"] = value
    return built


def create_instance(
    model_cls: Type[ModelType],
    commit: bool = True,
    flush: bool = False,
    *,
    actor_id: Optional[str] = None,
    event_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **attributes: Any,
) -> ModelType:
    """
    Generic helper to create and optionally persist a new model instance.
    """

    logger = get_logger("model_utils")
    action = event_name or f"{model_cls.__name__.lower()}.create"
    sanitized_attrs = _sanitize_payload(attributes)
    with log_context(**_build_context(model_cls.__name__, "create", actor_id, context)):
        logger.info(
            "Creating %s commit=%s flush=%s attributes=%s",
            model_cls.__name__,
            commit,
            flush,
            sanitized_attrs,
        )
        try:
            instance = model_cls(**attributes)
            db.session.add(instance)

            if flush:
                db.session.flush()

            if commit:
                db.session.commit()
                _emit_audit(
                    action,
                    actor_id,
                    {
                        "operation": "create",
                        "model": model_cls.__name__,
                        "target_id": _instance_identity(instance),
                        "attributes": sanitized_attrs,
                    },
                )

            logger.info(
                "Created %s target_id=%s commit=%s",
                model_cls.__name__,
                _instance_identity(instance),
                commit,
            )
            return instance
        except Exception:
            logger.exception("Failed to create %s attributes=%s", model_cls.__name__, sanitized_attrs)
            raise


def get_instance(
    model_cls: Type[ModelType],
    instance_id: Any,
    *,
    actor_id: Optional[str] = None,
    event_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[ModelType]:
    """
    Fetch a single model instance by primary key.
    """

    logger = get_logger("model_utils")
    action = event_name or f"{model_cls.__name__.lower()}.get"
    with log_context(**_build_context(model_cls.__name__, "get", actor_id, context)):
        logger.info("Fetching %s id=%s", model_cls.__name__, instance_id)
        instance = db.session.get(model_cls, instance_id) if instance_id is not None else None
        logger.info(
            "Fetched %s id=%s found=%s",
            model_cls.__name__,
            instance_id,
            instance is not None,
        )
        _emit_audit(
            action,
            actor_id,
            {
                "operation": "get",
                "model": model_cls.__name__,
                "target_id": _serialize_value(instance_id),
                "found": instance is not None,
            },
        )
        return instance


def list_instances(
    model_cls: Type[ModelType],
    *,
    filters: Optional[Sequence[Any]] = None,
    order_by: Optional[Union[Any, Sequence[Any]]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    query_options: Optional[Sequence[Any]] = None,
    actor_id: Optional[str] = None,
    event_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> List[ModelType]:
    """
    List model instances subject to optional filters, ordering, and paging.
    """

    logger = get_logger("model_utils")
    action = event_name or f"{model_cls.__name__.lower()}.list"
    filter_desc = [str(f) for f in filters] if filters else []
    with log_context(**_build_context(model_cls.__name__, "list", actor_id, context)):
        logger.info(
            "Listing %s filters=%s order=%s limit=%s offset=%s options=%s",
            model_cls.__name__,
            filter_desc,
            str(order_by),
            limit,
            offset,
            len(query_options or []),
        )

        query: Query = db.session.query(model_cls)

        if filters:
            for clause in filters:
                query = query.filter(clause)

        if query_options:
            for option in query_options:
                query = query.options(option)

        if order_by is not None:
            if isinstance(order_by, (list, tuple)):
                query = query.order_by(*order_by)
            else:
                query = query.order_by(order_by)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        results = list(query)
        logger.info("Listed %s count=%s", model_cls.__name__, len(results))
        _emit_audit(
            action,
            actor_id,
            {
                "operation": "list",
                "model": model_cls.__name__,
                "filters": filter_desc,
                "limit": limit,
                "offset": offset,
                "query_options": len(query_options or []),
                "count": len(results),
            },
        )
        return results


def update_instance(
    instance: ModelType,
    commit: bool = True,
    flush: bool = False,
    *,
    actor_id: Optional[str] = None,
    event_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **attributes: Any,
) -> ModelType:
    """
    Update attributes on an instance.  Attributes with value ``None`` are
    respected – callers should pre-filter if they need to skip ``None`` values.
    """

    logger = get_logger("model_utils")
    model_name = instance.__class__.__name__
    action = event_name or f"{model_name.lower()}.update"
    before = {key: _serialize_value(getattr(instance, key, None)) for key in attributes}
    sanitized_attrs = _sanitize_payload(attributes)
    with log_context(**_build_context(model_name, "update", actor_id, context)):
        logger.info(
            "Updating %s target_id=%s attributes=%s commit=%s flush=%s",
            model_name,
            _instance_identity(instance),
            sanitized_attrs,
            commit,
            flush,
        )
        try:
            for key, value in attributes.items():
                setattr(instance, key, value)

            if flush:
                db.session.flush()

            if commit:
                db.session.commit()
                _emit_audit(
                    action,
                    actor_id,
                    {
                        "operation": "update",
                        "model": model_name,
                        "target_id": _instance_identity(instance),
                        "before": before,
                        "after": sanitized_attrs,
                    },
                )

            logger.info(
                "Updated %s target_id=%s commit=%s",
                model_name,
                _instance_identity(instance),
                commit,
            )
            return instance
        except Exception:
            logger.exception(
                "Failed to update %s target_id=%s attributes=%s",
                model_name,
                _instance_identity(instance),
                sanitized_attrs,
            )
            raise


def delete_instance(
    model_cls: Type[ModelType],
    instance_or_id: Union[ModelType, Any],
    commit: bool = True,
    flush: bool = False,
    *,
    actor_id: Optional[str] = None,
    event_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Delete a model instance by object or identifier.
    """

    logger = get_logger("model_utils")
    action = event_name or f"{model_cls.__name__.lower()}.delete"
    identity = None

    with log_context(**_build_context(model_cls.__name__, "delete", actor_id, context)):
        try:
            if isinstance(instance_or_id, model_cls):
                instance = instance_or_id
            else:
                instance = get_instance(
                    model_cls,
                    instance_or_id,
                    actor_id=actor_id,
                    event_name=f"{model_cls.__name__.lower()}.resolve",
                    context=context,
                )

            if instance is None:
                logger.warning("Delete skipped for %s; target not found id=%s", model_cls.__name__, instance_or_id)
                return

            identity = _instance_identity(instance)
            snapshot = {
                column.key: _serialize_value(getattr(instance, column.key, None))
                for column in instance.__table__.columns  # type: ignore[attr-defined]
            } if hasattr(instance, "__table__") else {}

            logger.info("Deleting %s target_id=%s", model_cls.__name__, identity)
            db.session.delete(instance)

            if flush:
                db.session.flush()

            if commit:
                db.session.commit()
                _emit_audit(
                    action,
                    actor_id,
                    {
                        "operation": "delete",
                        "model": model_cls.__name__,
                        "target_id": identity,
                        "snapshot": snapshot,
                    },
                )

            logger.info("Deleted %s target_id=%s commit=%s", model_cls.__name__, identity, commit)
        except Exception:
            logger.exception("Failed to delete %s target=%s", model_cls.__name__, identity or instance_or_id)
            raise
