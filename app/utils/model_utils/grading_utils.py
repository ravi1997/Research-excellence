from __future__ import annotations

import json
from typing import Dict, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import Grading, GradingFor, GradingType
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

logger = get_logger("grading_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record grading audit", extra={"event": event})


def create_grading_type(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> GradingType:
    ctx = {"function": "create_grading_type", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="grading_utils", action="create_grading_type", actor_id=actor_id):
        logger.info("create_grading_type commit=%s attributes=%s", commit, sanitized)
    grading_type = create_instance(
        GradingType,
        commit=commit,
        actor_id=actor_id,
        event_name="grading_type.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_grading_type complete id=%s", _serialize_value(getattr(grading_type, "id", None)))
    return grading_type


def get_grading_type_by_id(
    grading_type_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[GradingType]:
    ctx = {"function": "get_grading_type_by_id", **(context or {})}
    with log_context(module="grading_utils", action="get_grading_type_by_id", actor_id=actor_id):
        logger.info("get_grading_type_by_id id=%s", _serialize_value(grading_type_id))
    grading_type = get_instance(
        GradingType,
        grading_type_id,
        actor_id=actor_id,
        event_name="grading_type.get",
        context=ctx,
    )
    logger.info(
        "get_grading_type_by_id resolved id=%s found=%s",
        _serialize_value(grading_type_id),
        grading_type is not None,
    )
    return grading_type


def list_grading_types(
    *,
    filters: Optional[Sequence] = None,
    order_by=None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[GradingType]:
    ctx = {"function": "list_grading_types", **(context or {})}
    grading_types = list_instances(
        GradingType,
        filters=filters,
        order_by=order_by,
        actor_id=actor_id,
        event_name="grading_type.list",
        context=ctx,
    )
    with log_context(module="grading_utils", action="list_grading_types", actor_id=actor_id):
        logger.info("list_grading_types count=%s", len(grading_types))
    return grading_types


def update_grading_type(
    grading_type: GradingType,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> GradingType:
    ctx = {
        "function": "update_grading_type",
        "grading_type_id": _serialize_value(getattr(grading_type, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="grading_utils", action="update_grading_type", actor_id=actor_id):
        logger.info(
            "update_grading_type target_id=%s attributes=%s",
            ctx.get("grading_type_id"),
            sanitized,
        )
    updated = update_instance(
        grading_type,
        commit=commit,
        actor_id=actor_id,
        event_name="grading_type.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_grading_type complete target_id=%s", ctx.get("grading_type_id"))
    return updated


def delete_grading_type(
    grading_type_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_grading_type", **(context or {})}
    with log_context(module="grading_utils", action="delete_grading_type", actor_id=actor_id):
        logger.info("delete_grading_type target=%s", _serialize_value(grading_type_or_id))
    delete_instance(
        GradingType,
        grading_type_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="grading_type.delete",
        context=ctx,
    )
    logger.info("delete_grading_type completed target=%s", _serialize_value(grading_type_or_id))


def create_grade(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Grading:
    ctx = {"function": "create_grade", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="grading_utils", action="create_grade", actor_id=actor_id):
        logger.info("create_grade commit=%s attributes=%s", commit, sanitized)
    grade = create_instance(
        Grading,
        commit=commit,
        actor_id=actor_id,
        event_name="grade.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_grade complete id=%s", _serialize_value(getattr(grade, "id", None)))
    return grade


def get_grade_by_id(
    grade_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Grading]:
    ctx = {"function": "get_grade_by_id", **(context or {})}
    with log_context(module="grading_utils", action="get_grade_by_id", actor_id=actor_id):
        logger.info("get_grade_by_id id=%s", _serialize_value(grade_id))
    grade = get_instance(
        Grading,
        grade_id,
        actor_id=actor_id,
        event_name="grade.get",
        context=ctx,
    )
    logger.info(
        "get_grade_by_id resolved id=%s found=%s",
        _serialize_value(grade_id),
        grade is not None,
    )
    return grade


def update_grade(
    grade: Grading,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Grading:
    ctx = {
        "function": "update_grade",
        "grade_id": _serialize_value(getattr(grade, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="grading_utils", action="update_grade", actor_id=actor_id):
        logger.info("update_grade target_id=%s attributes=%s", ctx.get("grade_id"), sanitized)
    updated = update_instance(
        grade,
        commit=commit,
        actor_id=actor_id,
        event_name="grade.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_grade complete target_id=%s", ctx.get("grade_id"))
    return updated


def delete_grade(
    grade_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_grade", **(context or {})}
    with log_context(module="grading_utils", action="delete_grade", actor_id=actor_id):
        logger.info("delete_grade target=%s", _serialize_value(grade_or_id))
    delete_instance(
        Grading,
        grade_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="grade.delete",
        context=ctx,
    )
    logger.info("delete_grade completed target=%s", _serialize_value(grade_or_id))


def list_grading_types_by_target(
    grading_for: GradingFor,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[GradingType]:
    filters = [GradingType.grading_for == grading_for]
    ctx = {
        "function": "list_grading_types_by_target",
        "grading_for": grading_for.value if isinstance(grading_for, GradingFor) else grading_for,
        **(context or {}),
    }
    grading_types = list_instances(
        GradingType,
        filters=filters,
        actor_id=actor_id,
        event_name="grading_type.list_by_target",
        context=ctx,
    )
    with log_context(module="grading_utils", action="list_grading_types_by_target", actor_id=actor_id):
        logger.info(
            "list_grading_types_by_target grading_for=%s count=%s",
            grading_for,
            len(grading_types),
        )
    return grading_types


def list_grades_for_submission(
    *,
    abstract_id=None,
    award_id=None,
    best_paper_id=None,
    eager: bool = False,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Grading]:
    filters = []
    if abstract_id:
        filters.append(Grading.abstract_id == abstract_id)
    if award_id:
        filters.append(Grading.award_id == award_id)
    if best_paper_id:
        filters.append(Grading.best_paper_id == best_paper_id)

    options = (
        [
            joinedload(Grading.grading_type),
            joinedload(Grading.graded_by),
        ]
        if eager
        else None
    )
    ctx = {
        "function": "list_grades_for_submission",
        "abstract_id": _serialize_value(abstract_id),
        "award_id": _serialize_value(award_id),
        "best_paper_id": _serialize_value(best_paper_id),
        "eager": eager,
        **(context or {}),
    }
    grades = list_instances(
        Grading,
        filters=filters,
        order_by=(Grading.verification_level.asc(), Grading.created_at.asc()),
        query_options=options,
        actor_id=actor_id,
        event_name="grade.list_for_submission",
        context=ctx,
    )
    with log_context(module="grading_utils", action="list_grades_for_submission", actor_id=actor_id):
        logger.info(
            "list_grades_for_submission abstract_id=%s award_id=%s best_paper_id=%s count=%s",
            _serialize_value(abstract_id),
            _serialize_value(award_id),
            _serialize_value(best_paper_id),
            len(grades),
        )
    return grades


def record_grade(
    *,
    grading_type: GradingType,
    graded_by_id,
    score: int,
    comments: Optional[str] = None,
    abstract_id=None,
    award_id=None,
    best_paper_id=None,
    commit: bool = True,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Grading:
    """
    Convenience helper to record a grade tied to a grading type and submission.
    """

    ctx = {
        "function": "record_grade",
        "grading_type_id": _serialize_value(getattr(grading_type, "id", None)),
        "graded_by_id": _serialize_value(graded_by_id),
        "abstract_id": _serialize_value(abstract_id),
        "award_id": _serialize_value(award_id),
        "best_paper_id": _serialize_value(best_paper_id),
        **(context or {}),
    }
    payload = {
        "score": score,
        "comments": comments,
    }
    sanitized = _sanitize_payload(payload)

    with log_context(module="grading_utils", action="record_grade", actor_id=actor_id):
        logger.info(
            "record_grade grading_type_id=%s graded_by_id=%s payload=%s commit=%s",
            ctx["grading_type_id"],
            ctx["graded_by_id"],
            sanitized,
            commit,
        )

    grade = Grading(
        grading_type_id=grading_type.id,
        graded_by_id=graded_by_id,
        score=score,
        comments=comments,
        verification_level=grading_type.verification_level,
        abstract_id=abstract_id,
        award_id=award_id,
        best_paper_id=best_paper_id,
    )
    db.session.add(grade)
    if commit:
        db.session.commit()
        _audit(
            "grade.record",
            actor_id,
            {
                "operation": "record_grade",
                "grading_type_id": ctx["grading_type_id"],
                "graded_by_id": ctx["graded_by_id"],
                "abstract_id": ctx["abstract_id"],
                "award_id": ctx["award_id"],
                "best_paper_id": ctx["best_paper_id"],
                "payload": sanitized,
                "grade_id": _serialize_value(getattr(grade, "id", None)),
            },
        )
    logger.info(
        "record_grade completed grade_id=%s",
        _serialize_value(getattr(grade, "id", None)),
    )
    return grade
