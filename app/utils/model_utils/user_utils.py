from __future__ import annotations

from typing import Iterable, Optional, Sequence

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.User import Role, User, UserRole

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)


def create_user(commit: bool = True, **attributes) -> User:
    return create_instance(User, commit=commit, **attributes)


def get_user_by_id(user_id) -> Optional[User]:
    return get_instance(User, user_id)


def list_users(*, filters: Optional[Sequence] = None, eager: bool = False, order_by=None) -> Sequence[User]:
    query = db.session.query(User)
    if eager:
        query = query.options(
            joinedload(User.role_associations),
            joinedload(User.department),
            joinedload(User.category),
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


def update_user(user: User, commit: bool = True, **attributes) -> User:
    return update_instance(user, commit=commit, **attributes)


def delete_user(user_or_id, commit: bool = True) -> None:
    delete_instance(User, user_or_id, commit=commit)


def set_user_roles(user: User, roles: Iterable[Role], commit: bool = True) -> User:
    current_roles = {association.role for association in user.role_associations}
    desired_roles = set(roles)

    # Remove roles that are not desired anymore.
    for association in list(user.role_associations):
        if association.role not in desired_roles:
            user.role_associations.remove(association)

    # Add new roles.
    for role in desired_roles:
        if role not in current_roles:
            user.role_associations.append(UserRole(role=role))

    if commit:
        db.session.commit()

    return user


def deactivate_user(user: User, commit: bool = True) -> User:
    user.is_active = False
    if commit:
        db.session.commit()
    return user


def activate_user(user: User, commit: bool = True) -> User:
    user.is_active = True
    if commit:
        db.session.commit()
    return user
