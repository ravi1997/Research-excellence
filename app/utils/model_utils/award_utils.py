from __future__ import annotations

import json
from typing import Dict, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import Awards
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

logger = get_logger("award_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record award audit", extra={"event": event})


def create_award(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Awards:
    ctx = {"function": "create_award", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="award_utils", action="create_award", actor_id=actor_id):
        logger.info("create_award commit=%s attributes=%s", commit, sanitized)
    award = create_instance(
        Awards,
        commit=commit,
        actor_id=actor_id,
        event_name="award.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_award complete id=%s", _serialize_value(getattr(award, "id", None)))
    return award


def get_award_by_id(
    award_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Awards]:
    ctx = {"function": "get_award_by_id", **(context or {})}
    with log_context(module="award_utils", action="get_award_by_id", actor_id=actor_id):
        logger.info("get_award_by_id id=%s", _serialize_value(award_id))
    award = get_instance(
        Awards,
        award_id,
        actor_id=actor_id,
        event_name="award.get",
        context=ctx,
    )
    logger.info(
        "get_award_by_id resolved id=%s found=%s",
        _serialize_value(award_id),
        award is not None,
    )
    return award


def list_awards(
    *,
    filters: Optional[Sequence] = None,
    eager: bool = False,
    order_by=None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Awards]:
    options = (
        [
            joinedload(Awards.author),
            joinedload(Awards.verifiers),
            joinedload(Awards.coordinators),
        ]
        if eager
        else None
    )
    ctx = {
        "function": "list_awards",
        "eager": eager,
        "limit": limit,
        "offset": offset,
        **(context or {}),
    }
    awards = list_instances(
        Awards,
        filters=filters,
        order_by=order_by,
        limit=limit,
        offset=offset,
        query_options=options,
        actor_id=actor_id,
        event_name="award.list",
        context=ctx,
    )
    with log_context(module="award_utils", action="list_awards", actor_id=actor_id):
        logger.info("list_awards complete eager=%s count=%s", eager, len(awards))
    return awards


def update_award(
    award: Awards,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Awards:
    ctx = {
        "function": "update_award",
        "award_id": _serialize_value(getattr(award, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="award_utils", action="update_award", actor_id=actor_id):
        logger.info("update_award target_id=%s attributes=%s", ctx.get("award_id"), sanitized)
    updated = update_instance(
        award,
        commit=commit,
        actor_id=actor_id,
        event_name="award.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_award complete target_id=%s", ctx.get("award_id"))
    return updated


def delete_award(
    award_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_award", **(context or {})}
    with log_context(module="award_utils", action="delete_award", actor_id=actor_id):
        logger.info("delete_award requested target=%s", _serialize_value(award_or_id))
    delete_instance(
        Awards,
        award_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="award.delete",
        context=ctx,
    )
    logger.info("delete_award completed target=%s", _serialize_value(award_or_id))


def assign_verifier(
    award: Awards,
    verifier: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Awards:
    ctx = {
        "function": "assign_award_verifier",
        "award_id": _serialize_value(getattr(award, "id", None)),
        "verifier_id": _serialize_value(getattr(verifier, "id", None)),
        **(context or {}),
    }
    changed = False
    with log_context(module="award_utils", action="assign_verifier", actor_id=actor_id):
        logger.info(
            "assign_award_verifier award_id=%s verifier_id=%s",
            ctx["award_id"],
            ctx["verifier_id"],
        )
        if verifier not in award.verifiers:
            award.verifiers.append(verifier)
            changed = True
    if changed and commit:
        db.session.commit()
        _audit(
            "award.assign_verifier",
            actor_id,
            {
                "operation": "assign_verifier",
                "award_id": ctx["award_id"],
                "verifier_id": ctx["verifier_id"],
            },
        )
    logger.info(
        "assign_award_verifier completed award_id=%s verifier_id=%s changed=%s",
        ctx["award_id"],
        ctx["verifier_id"],
        changed,
    )
    return award


def assign_coordinator(
    award: Awards,
    coordinator: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Awards:
    ctx = {
        "function": "assign_award_coordinator",
        "award_id": _serialize_value(getattr(award, "id", None)),
        "coordinator_id": _serialize_value(getattr(coordinator, "id", None)),
        **(context or {}),
    }
    changed = False
    with log_context(module="award_utils", action="assign_coordinator", actor_id=actor_id):
        logger.info(
            "assign_award_coordinator award_id=%s coordinator_id=%s",
            ctx["award_id"],
            ctx["coordinator_id"],
        )
        if coordinator not in award.coordinators:
            award.coordinators.append(coordinator)
            changed = True
    if changed and commit:
        db.session.commit()
        _audit(
            "award.assign_coordinator",
            actor_id,
            {
                "operation": "assign_coordinator",
                "award_id": ctx["award_id"],
                "coordinator_id": ctx["coordinator_id"],
            },
        )
    logger.info(
        "assign_award_coordinator completed award_id=%s coordinator_id=%s changed=%s",
        ctx["award_id"],
        ctx["coordinator_id"],
        changed,
    )
    return award


def remove_verifier(
    award: Awards,
    verifier: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Awards:
    ctx = {
        "function": "remove_award_verifier",
        "award_id": _serialize_value(getattr(award, "id", None)),
        "verifier_id": _serialize_value(getattr(verifier, "id", None)),
        **(context or {}),
    }
    removed = False
    with log_context(module="award_utils", action="remove_verifier", actor_id=actor_id):
        logger.info(
            "remove_award_verifier award_id=%s verifier_id=%s",
            ctx["award_id"],
            ctx["verifier_id"],
        )
        if verifier in award.verifiers:
            award.verifiers.remove(verifier)
            removed = True
    if removed and commit:
        db.session.commit()
        _audit(
            "award.remove_verifier",
            actor_id,
            {
                "operation": "remove_verifier",
                "award_id": ctx["award_id"],
                "verifier_id": ctx["verifier_id"],
            },
        )
    logger.info(
        "remove_award_verifier completed award_id=%s verifier_id=%s removed=%s",
        ctx["award_id"],
        ctx["verifier_id"],
        removed,
    )
    return award


def remove_coordinator(
    award: Awards,
    coordinator: User,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Awards:
    ctx = {
        "function": "remove_award_coordinator",
        "award_id": _serialize_value(getattr(award, "id", None)),
        "coordinator_id": _serialize_value(getattr(coordinator, "id", None)),
        **(context or {}),
    }
    removed = False
    with log_context(module="award_utils", action="remove_coordinator", actor_id=actor_id):
        logger.info(
            "remove_award_coordinator award_id=%s coordinator_id=%s",
            ctx["award_id"],
            ctx["coordinator_id"],
        )
        if coordinator in award.coordinators:
            award.coordinators.remove(coordinator)
            removed = True
    if removed and commit:
        db.session.commit()
        _audit(
            "award.remove_coordinator",
            actor_id,
            {
                "operation": "remove_coordinator",
                "award_id": ctx["award_id"],
                "coordinator_id": ctx["coordinator_id"],
            },
        )
    logger.info(
        "remove_award_coordinator completed award_id=%s coordinator_id=%s removed=%s",
        ctx["award_id"],
        ctx["coordinator_id"],
        removed,
    )
    return award


def can_advance_to_next_phase(award: Awards, actor_id) -> bool:
    """Check if an award can advance to the next review phase based on grading completeness"""
    from app.models.Cycle import AwardVerifiers, Grading, GradingType
    current_phase = award.review_phase
    
    # Get all verifiers assigned to the current phase
    verifier_assignments = AwardVerifiers.query.filter_by(
        award_id=award.id,
        review_phase=current_phase
    ).all()
    
    if not verifier_assignments:
        # If no verifiers are assigned to this phase, we can advance
        return True
    
    # Get all grading types for awards
    grading_types = GradingType.query.filter_by(grading_for='award').all()
    
    # For each verifier in the current phase, check if they have submitted grades
    for assignment in verifier_assignments:
        verifier_id = assignment.user_id
        if verifier_id != actor_id:
            continue

        # Check if all required grading types have been graded by this verifier in this phase
        for grading_type in grading_types:
            grade_exists = Grading.query.filter_by(
                award_id=award.id,
                grading_type_id=grading_type.id,
                graded_by_id=verifier_id,
                review_phase=current_phase
            ).first()
            
            if not grade_exists:
                print(f"Missing grade for verifier {verifier_id}, grading type {grading_type.id} in phase {current_phase}")
                
                return False
    
    # If all verifiers have submitted all required grades for this phase, we can advance
    print("All required grades submitted for phase", current_phase)
    return True