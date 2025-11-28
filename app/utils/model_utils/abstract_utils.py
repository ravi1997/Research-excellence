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
    review_phase: int = 1,
) -> Abstracts:
    ctx = {
        "function": "assign_verifier",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "verifier_id": _serialize_value(getattr(verifier, "id", None)),
        "review_phase": review_phase,
        **(context or {}),
    }
    changed = False
    with log_context(module="abstract_utils", action="assign_verifier", actor_id=actor_id):
        logger.info(
            "assign_verifier abstract_id=%s verifier_id=%s review_phase=%s",
            ctx["abstract_id"],
            ctx["verifier_id"],
            review_phase,
        )
        from app.models.Cycle import AbstractVerifiers
        existing_assignment = (
            AbstractVerifiers.query.filter_by(
                abstract_id=abstract.id,
                user_id=verifier.id,
            )
            .with_for_update(of=AbstractVerifiers)
            .first()
        )

        if existing_assignment:
            if existing_assignment.review_phase != review_phase:
                existing_assignment.review_phase = review_phase
                changed = True
        else:
            assignment = AbstractVerifiers(
                abstract_id=abstract.id,
                user_id=verifier.id,
                review_phase=review_phase,
            )
            db.session.add(assignment)
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
                "review_phase": review_phase,
            },
        )
    logger.info(
        "assign_verifier completed abstract_id=%s verifier_id=%s review_phase=%s changed=%s",
        ctx["abstract_id"],
        ctx["verifier_id"],
        review_phase,
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
    review_phase: Optional[int] = None,
) -> Abstracts:
    ctx = {
        "function": "remove_verifier",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "verifier_id": _serialize_value(getattr(verifier, "id", None)),
        "review_phase": review_phase,
        **(context or {}),
    }
    removed = False
    with log_context(module="abstract_utils", action="remove_verifier", actor_id=actor_id):
        logger.info(
            "remove_verifier abstract_id=%s verifier_id=%s review_phase=%s",
            ctx["abstract_id"],
            ctx["verifier_id"],
            review_phase,
        )
        
        if review_phase is not None:
            # Remove verifier from specific review phase
            from app.models.Cycle import AbstractVerifiers
            assignment = AbstractVerifiers.query.filter_by(
                abstract_id=abstract.id,
                user_id=verifier.id,
                review_phase=review_phase
            ).first()
            
            if assignment:
                db.session.delete(assignment)
                # Only remove from the abstract's verifiers if this was the only phase assignment
                other_assignments = AbstractVerifiers.query.filter_by(
                    abstract_id=abstract.id,
                    user_id=verifier.id
                ).count()
                
                if other_assignments <= 1:
                    if verifier in abstract.verifiers:
                        abstract.verifiers.remove(verifier)
                removed = True
        else:
            # Remove verifier from all review phases
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
                "review_phase": review_phase,
            },
        )
    logger.info(
        "remove_verifier completed abstract_id=%s verifier_id=%s review_phase=%s removed=%s",
        ctx["abstract_id"],
        ctx["verifier_id"],
        review_phase,
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


def get_grades_by_phase(abstract: Abstracts, phase: int) -> Sequence:
    """Get all grades for a specific review phase"""
    from app.models.Cycle import Grading
    return Grading.query.filter_by(
        abstract_id=abstract.id,
        review_phase=phase
    ).all()


def get_all_grades_by_phase(abstract: Abstracts) -> Dict[int, Sequence]:
    """Get all grades organized by review phase"""
    from app.models.Cycle import Grading
    grades = Grading.query.filter_by(abstract_id=abstract.id).all()
    
    grades_by_phase = {}
    for grade in grades:
        phase = grade.review_phase
        if phase not in grades_by_phase:
            grades_by_phase[phase] = []
        grades_by_phase[phase].append(grade)
    
    return grades_by_phase


def advance_to_next_phase(abstract: Abstracts, actor_id: Optional[str] = None) -> Abstracts:
    """Advance an abstract to the next review phase"""
    ctx = {
        "function": "advance_to_next_phase",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "current_phase": abstract.review_phase,
        **({"actor_id": actor_id} if actor_id else {}),
    }
    
    with log_context(module="abstract_utils", action="advance_to_next_phase", actor_id=actor_id):
        logger.info(
            "advance_to_next_phase abstract_id=%s current_phase=%s",
            ctx["abstract_id"],
            abstract.review_phase,
        )
        
        # Update the review phase
        abstract.review_phase += 1
        abstract.status = "UNDER_REVIEW"  # Reset to under review for the next phase
        
        db.session.commit()
        
        _audit(
            "abstract.advance_to_next_phase",
            actor_id,
            {
                "operation": "advance_to_next_phase",
                "abstract_id": ctx["abstract_id"],
                "new_phase": abstract.review_phase,
            },
        )
        
        logger.info(
            "advance_to_next_phase completed abstract_id=%s new_phase=%s",
            ctx["abstract_id"],
            abstract.review_phase,
        )
        
    return abstract


def get_current_phase_verifiers(abstract: Abstracts) -> Sequence[User]:
    """Get verifiers assigned to the current review phase"""
    from app.models.Cycle import AbstractVerifiers
    current_phase = abstract.review_phase
    
    # Get user IDs for verifiers assigned to the current phase
    verifier_assignments = AbstractVerifiers.query.filter_by(
        abstract_id=abstract.id,
        review_phase=current_phase
    ).all()
    
    verifier_ids = [assignment.user_id for assignment in verifier_assignments]
    
    # Get the actual user objects
    if verifier_ids:
        from app.models.User import User
        return User.query.filter(User.id.in_(verifier_ids)).all()
    else:
        return []


def can_advance_to_next_phase(abstract: Abstracts,actor_id) -> bool:
    """Check if an abstract can advance to the next review phase based on grading completeness"""
    from app.models.Cycle import AbstractVerifiers, Grading, GradingType
    current_phase = abstract.review_phase
    
    # Get all verifiers assigned to the current phase
    verifier_assignments = AbstractVerifiers.query.filter_by(
        abstract_id=abstract.id,
        review_phase=current_phase
    ).all()
    
    if not verifier_assignments:
        # If no verifiers are assigned to this phase, we can advance
        return True
    
    # Get all grading types for abstracts
    grading_types = GradingType.query.filter_by(grading_for='abstract').all()
    
    # For each verifier in the current phase, check if they have submitted grades
    for assignment in verifier_assignments:
        verifier_id = assignment.user_id

        # Check if all required grading types have been graded by this verifier in this phase
        for grading_type in grading_types:
            grade_exists = Grading.query.filter_by(
                abstract_id=abstract.id,
                grading_type_id=grading_type.id,
                graded_by_id=verifier_id,
                review_phase=current_phase
            ).first()
            
            if not grade_exists:
                # Not all grades have been submitted by all verifiers for this phase
                return False
    
    # If all verifiers have submitted all required grades for this phase, we can advance
    return True


def submit_abstract_for_review(abstract: Abstracts, actor_id: Optional[str] = None) -> Abstracts:
    """Submit an abstract for review"""
    ctx = {
        "function": "submit_abstract_for_review",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "current_status": abstract.status.name,
        **({"actor_id": actor_id} if actor_id else {}),
    }
    
    with log_context(module="abstract_utils", action="submit_abstract_for_review", actor_id=actor_id):
        logger.info(
            "submit_abstract_for_review abstract_id=%s current_status=%s",
            ctx["abstract_id"],
            abstract.status.name,
        )
        
        # Only allow submission if the abstract is in PENDING status and phase 1
        if abstract.status.name != 'PENDING' or abstract.review_phase != 1:
            raise ValueError(f"Cannot submit abstract: Abstract must be in PENDING status and phase 1 to be submitted for review. Current status: {abstract.status.name}, Current phase: {abstract.review_phase}")
        
        # Update the status to UNDER_REVIEW
        abstract.status = "UNDER_REVIEW"
        
        db.session.commit()
        
        _audit(
            "abstract.submit_for_review",
            actor_id,
            {
                "operation": "submit_for_review",
                "abstract_id": ctx["abstract_id"],
                "new_status": "UNDER_REVIEW",
            },
        )
        
        logger.info(
            "submit_abstract_for_review completed abstract_id=%s new_status=UNDER_REVIEW",
            ctx["abstract_id"],
        )
        
    return abstract


def accept_abstract(abstract: Abstracts, actor_id: Optional[str] = None) -> Abstracts:
    """Accept an abstract after review"""
    ctx = {
        "function": "accept_abstract",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "current_status": abstract.status.name,
        **({"actor_id": actor_id} if actor_id else {}),
    }
    
    with log_context(module="abstract_utils", action="accept_abstract", actor_id=actor_id):
        logger.info(
            "accept_abstract abstract_id=%s current_status=%s",
            ctx["abstract_id"],
            abstract.status.name,
        )
        
        # Check if all required grades have been submitted for the current phase
        if not can_advance_to_next_phase(abstract):
            raise ValueError(f"Cannot accept abstract: Not all required grades have been submitted for phase {abstract.review_phase}")
        
        # Update the status to ACCEPTED
        abstract.status = "ACCEPTED"
        
        db.session.commit()
        
        _audit(
            "abstract.accept",
            actor_id,
            {
                "operation": "accept",
                "abstract_id": ctx["abstract_id"],
                "new_status": "ACCEPTED",
            },
        )
        
        logger.info(
            "accept_abstract completed abstract_id=%s new_status=ACCEPTED",
            ctx["abstract_id"],
        )
        
    return abstract


def reject_abstract(abstract: Abstracts, actor_id: Optional[str] = None) -> Abstracts:
    """Reject an abstract after review"""
    ctx = {
        "function": "reject_abstract",
        "abstract_id": _serialize_value(getattr(abstract, "id", None)),
        "current_status": abstract.status.name,
        **({"actor_id": actor_id} if actor_id else {}),
    }
    
    with log_context(module="abstract_utils", action="reject_abstract", actor_id=actor_id):
        logger.info(
            "reject_abstract abstract_id=%s current_status=%s",
            ctx["abstract_id"],
            abstract.status.name,
        )
        
        # Update the status to REJECTED
        abstract.status = "REJECTED"
        
        db.session.commit()
        
        _audit(
            "abstract.reject",
            actor_id,
            {
                "operation": "reject",
                "abstract_id": ctx["abstract_id"],
                "new_status": "REJECTED",
            },
        )
        
        logger.info(
            "reject_abstract completed abstract_id=%s new_status=REJECTED",
            ctx["abstract_id"],
        )
        
    return abstract
