from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.Cycle import Awards
from app.models.User import User

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)


def create_award(commit: bool = True, **attributes) -> Awards:
    return create_instance(Awards, commit=commit, **attributes)


def get_award_by_id(award_id) -> Optional[Awards]:
    return get_instance(Awards, award_id)


def list_awards(
    *,
    filters: Optional[Sequence] = None,
    eager: bool = False,
    order_by=None,
) -> Sequence[Awards]:
    query = db.session.query(Awards)
    if eager:
        query = query.options(
            joinedload(Awards.author),
            joinedload(Awards.verifiers),
            joinedload(Awards.coordinators),
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


def update_award(award: Awards, commit: bool = True, **attributes) -> Awards:
    return update_instance(award, commit=commit, **attributes)


def delete_award(award_or_id, commit: bool = True) -> None:
    delete_instance(Awards, award_or_id, commit=commit)


def assign_verifier(award: Awards, verifier: User, commit: bool = True) -> Awards:
    if verifier not in award.verifiers:
        award.verifiers.append(verifier)
        if commit:
            db.session.commit()
    return award


def assign_coordinator(award: Awards, coordinator: User, commit: bool = True) -> Awards:
    if coordinator not in award.coordinators:
        award.coordinators.append(coordinator)
        if commit:
            db.session.commit()
    return award


def remove_verifier(award: Awards, verifier: User, commit: bool = True) -> Awards:
    if verifier in award.verifiers:
        award.verifiers.remove(verifier)
        if commit:
            db.session.commit()
    return award


def remove_coordinator(award: Awards, coordinator: User, commit: bool = True) -> Awards:
    if coordinator in award.coordinators:
        award.coordinators.remove(coordinator)
        if commit:
            db.session.commit()
    return award
