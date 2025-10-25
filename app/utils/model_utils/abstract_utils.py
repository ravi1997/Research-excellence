from __future__ import annotations

import json
from typing import Dict, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import Abstracts
from app.models.User import User
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

logger = get_logger("abstract_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record abstract audit", extra={"event": event})


def create_abstract(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Abstracts:
    ctx = {"function": "create_abstract", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="abstract_utils", action="create_abstract", actor_id=actor_id):
        logger.info("create_abstract commit=%s attributes=%s", commit, sanitized)
    abstract = create_instance(
        Abstracts,
        commit=commit,
        actor_id=actor_id,
        event_name="abstract.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_abstract complete id=%s", _serialize_value(getattr(abstract, "id", None)))
    return abstract


def get_abstract_by_id(
    abstract_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Abstracts]:
    ctx = {"function": "get_abstract_by_id", **(context or {})}
    with log_context(module="abstract_utils", action="get_abstract_by_id", actor_id=actor_id):
        logger.info("get_abstract_by_id id=%s", _serialize_value(abstract_id))
    abstract = get_instance(
        Abstracts,
        abstract_id,
        actor_id=actor_id,
        event_name="abstract.get",
        context=ctx,
    )
    logger.info(
        "get_abstract_by_id resolved id=%s found=%s",
        _serialize_value(abstract_id),
        abstract is not None,
    )
    return abstract


def list_abstracts(
    *,
    filters: Optional[Sequence] = None,
    eager: bool = False,
    order_by=None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Abstracts]:
    options = (
        [
            joinedload(Abstracts.authors),
            joinedload(Abstracts.verifiers),
            joinedload(Abstracts.coordinators),
        ]
        if eager
        else None
    )
    ctx = {
        "function": "list_abstracts",
        "eager": eager,
        **(context or {}),
    }
    abstracts = list_instances(
        Abstracts,
        filters=filters,
        order_by=order_by,
        query_options=options,
        actor_id=actor_id,
        event_name="abstract.list",
        context=ctx,
    )
    with log_context(module="abstract_utils", action="list_abstracts", actor_id=actor_id):
        logger.info("list_abstracts complete eager=%s count=%s", eager, len(abstracts))
    return abstracts


def update_abstract(
    abstract: Abstracts,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Abstracts:
    ctx = {
        "function": "update_abstract",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="abstract_utils", action="update_abstract", actor_id=actor_id):
        logger.info("update_abstract target_id=%s attributes=%s", ctx.get("abstract_id"), sanitized)
    updated = update_instance(
        abstract,
        commit=commit,
        actor_id=actor_id,
        event_name="abstract.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_abstract complete target_id=%s", ctx.get("abstract_id"))
    return updated


def delete_abstract(
    abstract_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_abstract", **(context or {})}
    with log_context(module="abstract_utils", action="delete_abstract", actor_id=actor_id):
        logger.info("delete_abstract requested target=%s", _serialize_value(abstract_or_id))
    delete_instance(
        Abstracts,
        abstract_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="abstract.delete",
        context=ctx,
    )
    logger.info("delete_abstract completed target=%s", _serialize_value(abstract_or_id))


def list_abstracts_by_cycle(
    cycle_id,
    *,
    status=None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Abstracts]:
    filters = [Abstracts.cycle_id == cycle_id]
    if status is not None:
        filters.append(Abstracts.status == status)
    ctx = {
        "function": "list_abstracts_by_cycle",
        "cycle_id": _serialize_value(cycle_id),
        "status": _serialize_value(status),
        **(context or {}),
    }
    abstracts = list_instances(
        Abstracts,
        filters=filters,
        order_by=(Abstracts.created_at.asc(),),
        actor_id=actor_id,
        event_name="abstract.list_by_cycle",
        context=ctx,
    )
    with log_context(module="abstract_utils", action="list_abstracts_by_cycle", actor_id=actor_id):
        logger.info(
            "list_abstracts_by_cycle cycle_id=%s status=%s count=%s",
            _serialize_value(cycle_id),
            status,
            len(abstracts),
        )
    return abstracts


def assign_verifier(
    abstract: Abstracts,
    verifier: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Abstracts:
    ctx = {
        "function": "assign_verifier",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "verifier_id": _serialize_value(getattr(verifier, "id", None)),
        **(context or {}),
    }
    changed = False
    with log_context(module="abstract_utils", action="assign_verifier", actor_id=actor_id):
        logger.info(
            "assign_verifier abstract_id=%s verifier_id=%s",
            ctx["abstract_id"],
            ctx["verifier_id"],
        )
        if verifier not in abstract.verifiers:
            abstract.verifiers.append(verifier)
            changed = True
    if changed and commit:
        db.session.commit()
        _audit(
            "abstract.assign_verifier",
            actor_id,
            {
                "operation": "assign_verifier",
                "abstract_id": ctx["abstract_id"],
                "verifier_id": ctx["verifier_id"],
            },
        )
    logger.info(
        "assign_verifier completed abstract_id=%s verifier_id=%s changed=%s",
        ctx["abstract_id"],
        ctx["verifier_id"],
        changed,
    )
    return abstract


def assign_coordinator(
    abstract: Abstracts,
    coordinator: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Abstracts:
    ctx = {
        "function": "assign_coordinator",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "coordinator_id": _serialize_value(getattr(coordinator, "id", None)),
        **(context or {}),
    }
    changed = False
    with log_context(module="abstract_utils", action="assign_coordinator", actor_id=actor_id):
        logger.info(
            "assign_coordinator abstract_id=%s coordinator_id=%s",
            ctx["abstract_id"],
            ctx["coordinator_id"],
        )
        if coordinator not in abstract.coordinators:
            abstract.coordinators.append(coordinator)
            changed = True
    if changed and commit:
        db.session.commit()
        _audit(
            "abstract.assign_coordinator",
            actor_id,
            {
                "operation": "assign_coordinator",
                "abstract_id": ctx["abstract_id"],
                "coordinator_id": ctx["coordinator_id"],
            },
        )
    logger.info(
        "assign_coordinator completed abstract_id=%s coordinator_id=%s changed=%s",
        ctx["abstract_id"],
        ctx["coordinator_id"],
        changed,
    )
    return abstract


def remove_verifier(
    abstract: Abstracts,
    verifier: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Abstracts:
    ctx = {
        "function": "remove_verifier",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "verifier_id": _serialize_value(getattr(verifier, "id", None)),
        **(context or {}),
    }
    removed = False
    with log_context(module="abstract_utils", action="remove_verifier", actor_id=actor_id):
        logger.info(
            "remove_verifier abstract_id=%s verifier_id=%s",
            ctx["abstract_id"],
            ctx["verifier_id"],
        )
        if verifier in abstract.verifiers:
            abstract.verifiers.remove(verifier)
            removed = True
    if removed and commit:
        db.session.commit()
        _audit(
            "abstract.remove_verifier",
            actor_id,
            {
                "operation": "remove_verifier",
                "abstract_id": ctx["abstract_id"],
                "verifier_id": ctx["verifier_id"],
            },
        )
    logger.info(
        "remove_verifier completed abstract_id=%s verifier_id=%s removed=%s",
        ctx["abstract_id"],
        ctx["verifier_id"],
        removed,
    )
    return abstract


def remove_coordinator(
    abstract: Abstracts,
    coordinator: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Abstracts:
    ctx = {
        "function": "remove_coordinator",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "coordinator_id": _serialize_value(getattr(coordinator, "id", None)),
        **(context or {}),
    }
    removed = False
    with log_context(module="abstract_utils", action="remove_coordinator", actor_id=actor_id):
        logger.info(
            "remove_coordinator abstract_id=%s coordinator_id=%s",
            ctx["abstract_id"],
            ctx["coordinator_id"],
        )
        if coordinator in abstract.coordinators:
            abstract.coordinators.remove(coordinator)
            removed = True
    if removed and commit:
        db.session.commit()
        _audit(
            "abstract.remove_coordinator",
            actor_id,
            {
                "operation": "remove_coordinator",
                "abstract_id": ctx["abstract_id"],
                "coordinator_id": ctx["coordinator_id"],
            },
        )
    logger.info(
        "remove_coordinator complete abstract_id=%s coordinator_id=%s removed=%s",
        ctx["abstract_id"],
        ctx["coordinator_id"],
        removed,
    )
    return abstract
