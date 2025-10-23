from __future__ import annotations

from typing import Optional, Sequence, Tuple

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import Grading, GradingFor, GradingType

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)


def create_grading_type(commit: bool = True, **attributes) -> GradingType:
    return create_instance(GradingType, commit=commit, **attributes)


def get_grading_type_by_id(grading_type_id) -> Optional[GradingType]:
    return get_instance(GradingType, grading_type_id)


def list_grading_types(*, filters: Optional[Sequence] = None, order_by=None) -> Sequence[GradingType]:
    return list_instances(GradingType, filters=filters, order_by=order_by)


def update_grading_type(grading_type: GradingType, commit: bool = True, **attributes) -> GradingType:
    return update_instance(grading_type, commit=commit, **attributes)


def delete_grading_type(grading_type_or_id, commit: bool = True) -> None:
    delete_instance(GradingType, grading_type_or_id, commit=commit)


def create_grade(commit: bool = True, **attributes) -> Grading:
    """
    Create a grade entry.  The calling code should pass the relevant foreign key
    (`abstract_id`, `award_id`, or `best_paper_id`) and `grading_type_id`.
    """

    return create_instance(Grading, commit=commit, **attributes)


def get_grade_by_id(grade_id) -> Optional[Grading]:
    return get_instance(Grading, grade_id)


def update_grade(grade: Grading, commit: bool = True, **attributes) -> Grading:
    return update_instance(grade, commit=commit, **attributes)


def delete_grade(grade_or_id, commit: bool = True) -> None:
    delete_instance(Grading, grade_or_id, commit=commit)


def list_grades_for_submission(
    *,
    abstract_id=None,
    award_id=None,
    best_paper_id=None,
    eager: bool = False,
) -> Sequence[Grading]:
    filters = []
    if abstract_id:
        filters.append(Grading.abstract_id == abstract_id)
    if award_id:
        filters.append(Grading.award_id == award_id)
    if best_paper_id:
        filters.append(Grading.best_paper_id == best_paper_id)

    query = db.session.query(Grading).filter(*filters)
    if eager:
        query = query.options(
            joinedload(Grading.grading_type),
            joinedload(Grading.graded_by),
        )

    return query.order_by(Grading.verification_level.asc(), Grading.created_at.asc()).all()


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
) -> Grading:
    """
    Convenience helper to record a grade tied to a grading type and submission.
    """

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
    return grade
