from __future__ import annotations

from typing import Iterable, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import Abstracts
from app.models.User import User

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)


def create_abstract(commit: bool = True, **attributes) -> Abstracts:
    return create_instance(Abstracts, commit=commit, **attributes)


def get_abstract_by_id(abstract_id) -> Optional[Abstracts]:
    return get_instance(Abstracts, abstract_id)


def list_abstracts(
    *,
    filters: Optional[Sequence] = None,
    eager: bool = False,
    order_by=None,
) -> Sequence[Abstracts]:
    query = db.session.query(Abstracts)
    if eager:
        query = query.options(
            joinedload(Abstracts.authors),
            joinedload(Abstracts.verifiers),
            joinedload(Abstracts.coordinators),
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


def update_abstract(abstract: Abstracts, commit: bool = True, **attributes) -> Abstracts:
    return update_instance(abstract, commit=commit, **attributes)


def delete_abstract(abstract_or_id, commit: bool = True) -> None:
    delete_instance(Abstracts, abstract_or_id, commit=commit)


def list_abstracts_by_cycle(cycle_id, *, status=None) -> Sequence[Abstracts]:
    filters = [Abstracts.cycle_id == cycle_id]
    if status is not None:
        filters.append(Abstracts.status == status)
    return list_instances(Abstracts, filters=filters, order_by=(Abstracts.created_at.asc(),))


def assign_verifier(abstract: Abstracts, verifier: User, commit: bool = True) -> Abstracts:
    if verifier not in abstract.verifiers:
        abstract.verifiers.append(verifier)
        if commit:
            db.session.commit()
    return abstract


def assign_coordinator(abstract: Abstracts, coordinator: User, commit: bool = True) -> Abstracts:
    if coordinator not in abstract.coordinators:
        abstract.coordinators.append(coordinator)
        if commit:
            db.session.commit()
    return abstract


def remove_verifier(abstract: Abstracts, verifier: User, commit: bool = True) -> Abstracts:
    if verifier in abstract.verifiers:
        abstract.verifiers.remove(verifier)
        if commit:
            db.session.commit()
    return abstract


def remove_coordinator(abstract: Abstracts, coordinator: User, commit: bool = True) -> Abstracts:
    if coordinator in abstract.coordinators:
        abstract.coordinators.remove(coordinator)
        if commit:
            db.session.commit()
    return abstract
