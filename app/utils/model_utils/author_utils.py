from __future__ import annotations

import json
from typing import Dict, Optional, Sequence, Tuple

from sqlalchemy import func

from app.extensions import db
from app.models.Cycle import Author
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

logger = get_logger("author_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record author audit", extra={"event": event})


def create_author(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Author:
    ctx = {"function": "create_author", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="author_utils", action="create_author", actor_id=actor_id):
        logger.info("create_author commit=%s attributes=%s", commit, sanitized)
    author = create_instance(
        Author,
        commit=commit,
        actor_id=actor_id,
        event_name="author.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_author complete id=%s", _serialize_value(getattr(author, "id", None)))
    return author


def get_author_by_id(
    author_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Author]:
    ctx = {"function": "get_author_by_id", **(context or {})}
    with log_context(module="author_utils", action="get_author_by_id", actor_id=actor_id):
        logger.info("get_author_by_id id=%s", _serialize_value(author_id))
    author = get_instance(
        Author,
        author_id,
        actor_id=actor_id,
        event_name="author.get",
        context=ctx,
    )
    logger.info(
        "get_author_by_id resolved id=%s found=%s",
        _serialize_value(author_id),
        author is not None,
    )
    return author


def list_authors(
    *,
    filters: Optional[Sequence] = None,
    order_by=None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Author]:
    ctx = {"function": "list_authors", **(context or {})}
    authors = list_instances(
        Author,
        filters=filters,
        order_by=order_by,
        actor_id=actor_id,
        event_name="author.list",
        context=ctx,
    )
    with log_context(module="author_utils", action="list_authors", actor_id=actor_id):
        logger.info("list_authors count=%s", len(authors))
    return authors


def update_author(
    author: Author,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Author:
    ctx = {
        "function": "update_author",
        "author_id": _serialize_value(getattr(author, "id", None)),
        **(context or {}),
    }
    sanitized = _sanitize_payload(attributes)
    with log_context(module="author_utils", action="update_author", actor_id=actor_id):
        logger.info("update_author target_id=%s attributes=%s", ctx.get("author_id"), sanitized)
    updated = update_instance(
        author,
        commit=commit,
        actor_id=actor_id,
        event_name="author.update",
        context=ctx,
        **attributes,
    )
    logger.info("update_author complete target_id=%s", ctx.get("author_id"))
    return updated


def delete_author(
    author_or_id,
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> None:
    ctx = {"function": "delete_author", **(context or {})}
    with log_context(module="author_utils", action="delete_author", actor_id=actor_id):
        logger.info("delete_author target=%s", _serialize_value(author_or_id))
    delete_instance(
        Author,
        author_or_id,
        commit=commit,
        actor_id=actor_id,
        event_name="author.delete",
        context=ctx,
    )
    logger.info("delete_author completed target=%s", _serialize_value(author_or_id))


def get_or_create_author(
    *,
    name: str,
    affiliation: Optional[str] = None,
    email: Optional[str] = None,
    commit_on_create: bool = True,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Tuple[Author, bool]:
    """
    Retrieve an existing author matching the provided identity fields or create
    a new one. Returns a tuple of (author, created_bool).
    """

    normalized_name = name.strip()
    normalized_email = email.strip() if email else None
    ctx = {
        "function": "get_or_create_author",
        "name": normalized_name,
        "email": normalized_email,
        **(context or {}),
    }
    with log_context(module="author_utils", action="get_or_create_author", actor_id=actor_id):
        logger.info(
            "get_or_create_author name=%s email=%s commit_on_create=%s",
            normalized_name,
            normalized_email,
            commit_on_create,
        )

    query = db.session.query(Author).filter(
        func.lower(Author.name) == func.lower(normalized_name),
    )

    if normalized_email:
        query = query.filter(func.lower(Author.email) == func.lower(normalized_email))

    author = query.first()
    created = False

    if author is None:
        author = Author(name=normalized_name, affiliation=affiliation, email=normalized_email)
        db.session.add(author)
        created = True
        if commit_on_create:
            db.session.commit()
            _audit(
                "author.create_or_get.created",
                actor_id,
                {
                    "operation": "create_author",
                    "author_id": _serialize_value(getattr(author, "id", None)),
                    "name": normalized_name,
                    "email": normalized_email,
                },
            )

    _audit(
        "author.create_or_get",
        actor_id,
        {
            "operation": "get_or_create_author",
            "name": normalized_name,
            "email": normalized_email,
            "created": created,
            "author_id": _serialize_value(getattr(author, "id", None)),
        },
    )
    logger.info(
        "get_or_create_author complete author_id=%s created=%s",
        _serialize_value(getattr(author, "id", None)),
        created,
    )
    return author, created
