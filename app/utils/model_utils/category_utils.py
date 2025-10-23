from __future__ import annotations

from typing import Optional, Sequence, Tuple

from sqlalchemy import func

from app.extensions import db
from app.models.Cycle import Category, PaperCategory

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    update_instance,
)


def create_category(commit: bool = True, **attributes) -> Category:
    return create_instance(Category, commit=commit, **attributes)


def get_category_by_id(category_id) -> Optional[Category]:
    return get_instance(Category, category_id)


def list_categories(*, order_by=None) -> Sequence[Category]:
    return list_instances(Category, order_by=order_by)


def update_category(category: Category, commit: bool = True, **attributes) -> Category:
    return update_instance(category, commit=commit, **attributes)


def delete_category(category_or_id, commit: bool = True) -> None:
    delete_instance(Category, category_or_id, commit=commit)


def get_or_create_category(*, name: str, commit_on_create: bool = True) -> Tuple[Category, bool]:
    category = (
        db.session.query(Category)
        .filter(func.lower(Category.name) == func.lower(name.strip()))
        .first()
    )
    created = False
    if category is None:
        category = Category(name=name.strip())
        db.session.add(category)
        created = True
        if commit_on_create:
            db.session.commit()
    return category, created


def create_paper_category(commit: bool = True, **attributes) -> PaperCategory:
    return create_instance(PaperCategory, commit=commit, **attributes)


def get_paper_category_by_id(category_id) -> Optional[PaperCategory]:
    return get_instance(PaperCategory, category_id)


def list_paper_categories(*, order_by=None) -> Sequence[PaperCategory]:
    return list_instances(PaperCategory, order_by=order_by)


def update_paper_category(
    category: PaperCategory,
    commit: bool = True,
    **attributes,
) -> PaperCategory:
    return update_instance(category, commit=commit, **attributes)


def delete_paper_category(category_or_id, commit: bool = True) -> None:
    delete_instance(PaperCategory, category_or_id, commit=commit)
