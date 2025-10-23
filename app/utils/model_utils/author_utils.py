from __future__ import annotations

from typing import Optional, Sequence, Tuple

from sqlalchemy import func

from app.extensions import db
from app.models.Cycle import Author

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)


def create_author(commit: bool = True, **attributes) -> Author:
    return create_instance(Author, commit=commit, **attributes)


def get_author_by_id(author_id) -> Optional[Author]:
    return get_instance(Author, author_id)


def list_authors(*, filters: Optional[Sequence] = None, order_by=None) -> Sequence[Author]:
    return list_instances(Author, filters=filters, order_by=order_by)


def update_author(author: Author, commit: bool = True, **attributes) -> Author:
    return update_instance(author, commit=commit, **attributes)


def delete_author(author_or_id, commit: bool = True) -> None:
    delete_instance(Author, author_or_id, commit=commit)


def get_or_create_author(
    *,
    name: str,
    affiliation: Optional[str] = None,
    email: Optional[str] = None,
    commit_on_create: bool = True,
) -> Tuple[Author, bool]:
    """
    Retrieve an existing author matching the provided identity fields or create
    a new one. Returns a tuple of (author, created_bool).
    """

    query = db.session.query(Author).filter(
        func.lower(Author.name) == func.lower(name.strip()),
    )

    if email:
        query = query.filter(func.lower(Author.email) == func.lower(email.strip()))

    author = query.first()
    created = False

    if author is None:
        author = Author(name=name.strip(), affiliation=affiliation, email=email)
        db.session.add(author)
        created = True
        if commit_on_create:
            db.session.commit()

    return author, created
