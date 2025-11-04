from __future__ import annotations

import json
from typing import Dict, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import BestPaper
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

logger = get_logger("best_paper_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record best_paper audit", extra={"event": event})


def create_best_paper(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> BestPaper:
    ctx = {"function": "create_best_paper", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="best_paper_utils", action="create_best_paper", actor_id=actor_id):
        logger.info("create_best_paper commit=%s attributes=%s", commit, sanitized)
    best_paper = create_instance(
        BestPaper,
        commit=commit,
        actor_id=actor_id,
        event_name="best_paper.create",
        context=ctx,
        **attributes,
    )
    logger.info(
        "create_best_paper complete id=%s",
        _serialize_value(getattr(best_paper, "id", None)),
    )
    return best_paper


def get_best_paper_by_id(
    best_paper_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[BestPaper]:
    ctx = {"function": "get_best_paper_by_id", **(context or {})}
    with log_context(module="best_paper_utils", action="get_best_paper_by_id", actor_id=actor_id):
        logger.info("get_best_paper_by_id id=%s", _serialize_value(best_paper_id))
    best_paper = get_instance(
        BestPaper,
        best_paper_id,
        actor_id=actor_id,
        event_name="best_paper.get",
        context=ctx,
    )
    logger.info(
        "get_best_paper_by_id resolved id=%s found=%s",
        _serialize_value(best_paper_id),
        best_paper is not None,
    )
    return best_paper


def list_best_papers(
    *,
    filters: Optional[Sequence] = None,
    eager: bool = False,
    order_by=None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[BestPaper]:
    options = (
        [
            joinedload(BestPaper.author),
            joinedload(BestPaper.verifiers),
            joinedload(BestPaper.coordinators),
        ]
        if eager
        else None
    )
    ctx = {
        "function": "list_best_papers",
        "eager": eager,
        "limit": limit,
        "offset": offset,
        **(context or {}),
    }
    best_papers = list_instances(
        BestPaper,
        filters=filters,
        order_by=order_by,
        limit=limit,
        offset=offset,
        query_options=options,
        actor_id=actor_id,
        event_name="best_paper.list",
        context=ctx,
    )
    with log_context(module="best_paper_utils", action="list_best_papers", actor_id=actor_id):
        logger.info("list_best_papers complete eager=%s count=%s", eager, len(best_papers))
    return best_papers


def update_best_paper(
    best_paper: BestPaper,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> BestPaper:
    ctx = {
        "function": "update_best_paper",
        "best_paper_id": _serialize_value(getattr(best_paper, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="best_paper_utils", action="update_best_paper", actor_id=actor_id):
        logger.info(
            "update_best_paper target_id=%s attributes=%s",
            ctx.get("best_paper_id"),
            sanitized,
        )
    updated = update_instance(
        best_paper,
        commit=commit,
        actor_id=actor_id,
        event_name="best_paper.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_best_paper complete target_id=%s", ctx.get("best_paper_id"))
    return updated


def delete_best_paper(
    best_paper_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_best_paper", **(context or {})}
    with log_context(module="best_paper_utils", action="delete_best_paper", actor_id=actor_id):
        logger.info("delete_best_paper target=%s", _serialize_value(best_paper_or_id))
    delete_instance(
        BestPaper,
        best_paper_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="best_paper.delete",
        context=ctx,
    )
    logger.info("delete_best_paper completed target=%s", _serialize_value(best_paper_or_id))


def assign_verifier(
    best_paper: BestPaper,
    verifier: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> BestPaper:
    ctx = {
        "function": "assign_best_paper_verifier",
        "best_paper_id": _serialize_value(getattr(best_paper, "id", None)),
        "verifier_id": _serialize_value(getattr(verifier, "id", None)),
        **(context or {}),
    }
    changed = False
    with log_context(module="best_paper_utils", action="assign_verifier", actor_id=actor_id):
        logger.info(
            "assign_best_paper_verifier best_paper_id=%s verifier_id=%s",
            ctx["best_paper_id"],
            ctx["verifier_id"],
        )
        if verifier not in best_paper.verifiers:
            best_paper.verifiers.append(verifier)
            changed = True
    if changed and commit:
        db.session.commit()
        _audit(
            "best_paper.assign_verifier",
            actor_id,
            {
                "operation": "assign_verifier",
                "best_paper_id": ctx["best_paper_id"],
                "verifier_id": ctx["verifier_id"],
            },
        )
    logger.info(
        "assign_best_paper_verifier completed best_paper_id=%s verifier_id=%s changed=%s",
        ctx["best_paper_id"],
        ctx["verifier_id"],
        changed,
    )
    return best_paper


def assign_coordinator(
    best_paper: BestPaper,
    coordinator: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> BestPaper:
    ctx = {
        "function": "assign_best_paper_coordinator",
        "best_paper_id": _serialize_value(getattr(best_paper, "id", None)),
        "coordinator_id": _serialize_value(getattr(coordinator, "id", None)),
        **(context or {}),
    }
    changed = False
    with log_context(module="best_paper_utils", action="assign_coordinator", actor_id=actor_id):
        logger.info(
            "assign_best_paper_coordinator best_paper_id=%s coordinator_id=%s",
            ctx["best_paper_id"],
            ctx["coordinator_id"],
        )
        if coordinator not in best_paper.coordinators:
            best_paper.coordinators.append(coordinator)
            changed = True
    if changed and commit:
        db.session.commit()
        _audit(
            "best_paper.assign_coordinator",
            actor_id,
            {
                "operation": "assign_coordinator",
                "best_paper_id": ctx["best_paper_id"],
                "coordinator_id": ctx["coordinator_id"],
            },
        )
    logger.info(
        "assign_best_paper_coordinator completed best_paper_id=%s coordinator_id=%s changed=%s",
        ctx["best_paper_id"],
        ctx["coordinator_id"],
        changed,
    )
    return best_paper


def remove_verifier(
    best_paper: BestPaper,
    verifier: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> BestPaper:
    ctx = {
        "function": "remove_best_paper_verifier",
        "best_paper_id": _serialize_value(getattr(best_paper, "id", None)),
        "verifier_id": _serialize_value(getattr(verifier, "id", None)),
        **(context or {}),
    }
    removed = False
    with log_context(module="best_paper_utils", action="remove_verifier", actor_id=actor_id):
        logger.info(
            "remove_best_paper_verifier best_paper_id=%s verifier_id=%s",
            ctx["best_paper_id"],
            ctx["verifier_id"],
        )
        if verifier in best_paper.verifiers:
            best_paper.verifiers.remove(verifier)
            removed = True
    if removed and commit:
        db.session.commit()
        _audit(
            "best_paper.remove_verifier",
            actor_id,
            {
                "operation": "remove_verifier",
                "best_paper_id": ctx["best_paper_id"],
                "verifier_id": ctx["verifier_id"],
            },
        )
    logger.info(
        "remove_best_paper_verifier completed best_paper_id=%s verifier_id=%s removed=%s",
        ctx["best_paper_id"],
        ctx["verifier_id"],
        removed,
    )
    return best_paper


def remove_coordinator(
    best_paper: BestPaper,
    coordinator: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> BestPaper:
    ctx = {
        "function": "remove_best_paper_coordinator",
        "best_paper_id": _serialize_value(getattr(best_paper, "id", None)),
        "coordinator_id": _serialize_value(getattr(coordinator, "id", None)),
        **(context or {}),
    }
    removed = False
    with log_context(module="best_paper_utils", action="remove_coordinator", actor_id=actor_id):
        logger.info(
            "remove_best_paper_coordinator best_paper_id=%s coordinator_id=%s",
            ctx["best_paper_id"],
            ctx["coordinator_id"],
        )
        if coordinator in best_paper.coordinators:
            best_paper.coordinators.remove(coordinator)
            removed = True
    if removed and commit:
        db.session.commit()
        _audit(
            "best_paper.remove_coordinator",
            actor_id,
            {
                "operation": "remove_coordinator",
                "best_paper_id": ctx["best_paper_id"],
                "coordinator_id": ctx["coordinator_id"],
            },
        )
    logger.info(
        "remove_best_paper_coordinator completed best_paper_id=%s coordinator_id=%s removed=%s",
        ctx["best_paper_id"],
        ctx["coordinator_id"],
        removed,
    )
    return best_paper
