from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import BestPaper
from app.models.User import User

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)


def create_best_paper(commit: bool = True, **attributes) -> BestPaper:
    return create_instance(BestPaper, commit=commit, **attributes)


def get_best_paper_by_id(best_paper_id) -> Optional[BestPaper]:
    return get_instance(BestPaper, best_paper_id)


def list_best_papers(
    *,
    filters: Optional[Sequence] = None,
    eager: bool = False,
    order_by=None,
) -> Sequence[BestPaper]:
    query = db.session.query(BestPaper)
    if eager:
        query = query.options(
            joinedload(BestPaper.author),
            joinedload(BestPaper.verifiers),
            joinedload(BestPaper.coordinators),
        )

    if filters:
        for clause in filters:
            query = query.filter(clause)

    if order_by is not None:
        if isinstance(order_by, (list, tuple)):
            query = query.order_by(*order_by)
        else:
            query = query.order_by(order_by)

    return query.all()


def update_best_paper(best_paper: BestPaper, commit: bool = True, **attributes) -> BestPaper:
    return update_instance(best_paper, commit=commit, **attributes)


def delete_best_paper(best_paper_or_id, commit: bool = True) -> None:
    delete_instance(BestPaper, best_paper_or_id, commit=commit)


def assign_verifier(best_paper: BestPaper, verifier: User, commit: bool = True) -> BestPaper:
    if verifier not in best_paper.verifiers:
        best_paper.verifiers.append(verifier)
        if commit:
            db.session.commit()
    return best_paper


def assign_coordinator(best_paper: BestPaper, coordinator: User, commit: bool = True) -> BestPaper:
    if coordinator not in best_paper.coordinators:
        best_paper.coordinators.append(coordinator)
        if commit:
            db.session.commit()
    return best_paper


def remove_verifier(best_paper: BestPaper, verifier: User, commit: bool = True) -> BestPaper:
    if verifier in best_paper.verifiers:
        best_paper.verifiers.remove(verifier)
        if commit:
            db.session.commit()
    return best_paper


def remove_coordinator(best_paper: BestPaper, coordinator: User, commit: bool = True) -> BestPaper:
    if coordinator in best_paper.coordinators:
        best_paper.coordinators.remove(coordinator)
        if commit:
            db.session.commit()
    return best_paper
