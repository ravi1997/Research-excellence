from __future__ import annotations

import json
from typing import Dict, Optional, Sequence, Tuple

from sqlalchemy import func

from app.extensions import db
from app.models.Cycle import Category, PaperCategory
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

logger = get_logger("category_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record category audit", extra={"event": event})


def create_category(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Category:
    ctx = {"function": "create_category", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="category_utils", action="create_category", actor_id=actor_id):
        logger.info("create_category commit=%s attributes=%s", commit, sanitized)
    category = create_instance(
        Category,
        commit=commit,
        actor_id=actor_id,
        event_name="category.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_category complete id=%s", _serialize_value(getattr(category, "id", None)))
    return category


def get_category_by_id(
    category_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Category]:
    ctx = {"function": "get_category_by_id", **(context or {})}
    with log_context(module="category_utils", action="get_category_by_id", actor_id=actor_id):
        logger.info("get_category_by_id id=%s", _serialize_value(category_id))
    category = get_instance(
        Category,
        category_id,
        actor_id=actor_id,
        event_name="category.get",
        context=ctx,
    )
    logger.info(
        "get_category_by_id resolved id=%s found=%s",
        _serialize_value(category_id),
        category is not None,
    )
    return category


def list_categories(
    *,
    order_by=None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Category]:
    ctx = {"function": "list_categories", **(context or {})}
    categories = list_instances(
        Category,
        order_by=order_by,
        actor_id=actor_id,
        event_name="category.list",
        context=ctx,
    )
    with log_context(module="category_utils", action="list_categories", actor_id=actor_id):
        logger.info("list_categories count=%s", len(categories))
    return categories


def update_category(
    category: Category,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Category:
    ctx = {
        "function": "update_category",
        "category_id": _serialize_value(getattr(category, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="category_utils", action="update_category", actor_id=actor_id):
        logger.info("update_category target_id=%s attributes=%s", ctx.get("category_id"), sanitized)
    updated = update_instance(
        category,
        commit=commit,
        actor_id=actor_id,
        event_name="category.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_category complete target_id=%s", ctx.get("category_id"))
    return updated


def delete_category(
    category_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_category", **(context or {})}
    with log_context(module="category_utils", action="delete_category", actor_id=actor_id):
        logger.info("delete_category target=%s", _serialize_value(category_or_id))
    delete_instance(
        Category,
        category_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="category.delete",
        context=ctx,
    )
    logger.info("delete_category completed target=%s", _serialize_value(category_or_id))


def get_or_create_category(
    *,
    name: str,
    commit_on_create: bool = True,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Tuple[Category, bool]:
    normalized_name = name.strip()
    ctx = {
        "function": "get_or_create_category",
        "name": normalized_name,
        **(context or {}),
    }
    with log_context(module="category_utils", action="get_or_create_category", actor_id=actor_id):
        logger.info(
            "get_or_create_category name=%s commit_on_create=%s",
            normalized_name,
            commit_on_create,
        )
    category = (
        db.session.query(Category)
        .filter(func.lower(Category.name) == func.lower(normalized_name))
        .first()
    )
    created = False
    if category is None:
        category = Category(name=normalized_name)
        db.session.add(category)
        created = True
        if commit_on_create:
            db.session.commit()
            _audit(
                "category.create_or_get.created",
                actor_id,
                {
                    "operation": "create_category",
                    "category_id": _serialize_value(getattr(category, "id", None)),
                    "name": normalized_name,
                },
            )

    _audit(
        "category.create_or_get",
        actor_id,
        {
            "operation": "get_or_create_category",
            "name": normalized_name,
            "created": created,
            "category_id": _serialize_value(getattr(category, "id", None)),
        },
    )
    logger.info(
        "get_or_create_category complete category_id=%s created=%s",
        _serialize_value(getattr(category, "id", None)),
        created,
    )
    return category, created


def create_paper_category(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> PaperCategory:
    ctx = {"function": "create_paper_category", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="category_utils", action="create_paper_category", actor_id=actor_id):
        logger.info("create_paper_category commit=%s attributes=%s", commit, sanitized)
    paper_category = create_instance(
        PaperCategory,
        commit=commit,
        actor_id=actor_id,
        event_name="paper_category.create",
        context=ctx,
        **attributes,
    )
    logger.info(
        "create_paper_category complete id=%s",
        _serialize_value(getattr(paper_category, "id", None)),
    )
    return paper_category


def get_paper_category_by_id(
    category_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[PaperCategory]:
    ctx = {"function": "get_paper_category_by_id", **(context or {})}
    with log_context(module="category_utils", action="get_paper_category_by_id", actor_id=actor_id):
        logger.info("get_paper_category_by_id id=%s", _serialize_value(category_id))
    category = get_instance(
        PaperCategory,
        category_id,
        actor_id=actor_id,
        event_name="paper_category.get",
        context=ctx,
    )
    logger.info(
        "get_paper_category_by_id resolved id=%s found=%s",
        _serialize_value(category_id),
        category is not None,
    )
    return category


def list_paper_categories(
    *,
    order_by=None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[PaperCategory]:
    ctx = {"function": "list_paper_categories", **(context or {})}
    categories = list_instances(
        PaperCategory,
        order_by=order_by,
        actor_id=actor_id,
        event_name="paper_category.list",
        context=ctx,
    )
    with log_context(module="category_utils", action="list_paper_categories", actor_id=actor_id):
        logger.info("list_paper_categories count=%s", len(categories))
    return categories


def update_paper_category(
    category: PaperCategory,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> PaperCategory:
    ctx = {
        "function": "update_paper_category",
        "paper_category_id": _serialize_value(getattr(category, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="category_utils", action="update_paper_category", actor_id=actor_id):
        logger.info(
            "update_paper_category target_id=%s attributes=%s",
            ctx.get("paper_category_id"),
            sanitized,
        )
    updated = update_instance(
        category,
        commit=commit,
        actor_id=actor_id,
        event_name="paper_category.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_paper_category complete target_id=%s", ctx.get("paper_category_id"))
    return updated


def delete_paper_category(
    category_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_paper_category", **(context or {})}
    with log_context(module="category_utils", action="delete_paper_category", actor_id=actor_id):
        logger.info("delete_paper_category target=%s", _serialize_value(category_or_id))
    delete_instance(
        PaperCategory,
        category_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="paper_category.delete",
        context=ctx,
    )
    logger.info("delete_paper_category completed target=%s", _serialize_value(category_or_id))
