from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Sequence, Tuple

from app.extensions import db
from app.models.Token import Token
from app.security_utils import audit_log
from app.utils.logging_utils import get_logger, log_context

from .base import (
    _sanitize_payload,
    _serialize_value,
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
)

logger = get_logger("token_utils")


def _audit(event: str, actor_id: Optional[str], payload: Dict[str, object]) -> None:
    try:
        audit_log(
            event,
            user_id=str(actor_id) if actor_id is not None else None,
            detail=json.dumps(payload, default=_serialize_value),
        )
    except Exception:
        logger.exception("Failed to record token audit", extra={"event": event})


def create_token(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> Token:
    ctx = {"function": "create_token", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="token_utils", action="create_token", actor_id=actor_id):
        logger.info("create_token commit=%s attributes=%s", commit, sanitized)
    token = create_instance(
        Token,
        commit=commit,
        actor_id=actor_id,
        event_name="token.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_token complete id=%s", _serialize_value(getattr(token, "id", None)))
    return token


def get_token_by_id(
    token_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Token]:
    ctx = {"function": "get_token_by_id", **(context or {})}
    with log_context(module="token_utils", action="get_token_by_id", actor_id=actor_id):
        logger.info("get_token_by_id id=%s", _serialize_value(token_id))
    token = get_instance(
        Token,
        token_id,
        actor_id=actor_id,
        event_name="token.get",
        context=ctx,
    )
    logger.info(
        "get_token_by_id resolved id=%s found=%s",
        _serialize_value(token_id),
        token is not None,
    )
    return token


def get_refresh_token_by_hash(
    token_hash: str,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Token]:
    ctx = {"function": "get_refresh_token_by_hash", **(context or {})}
    tokens = list_instances(
        Token,
        filters=[
            Token.token_hash == token_hash,
            Token.token_type == "refresh",
        ],
        limit=1,
        actor_id=actor_id,
        event_name="token.refresh.lookup",
        context=ctx,
    )
    return tokens[0] if tokens else None


def list_tokens(
    *,
    filters: Optional[Sequence] = None,
    order_by=None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[Token]:
    ctx = {"function": "list_tokens", **(context or {})}
    tokens = list_instances(
        Token,
        filters=filters,
        order_by=order_by,
        actor_id=actor_id,
        event_name="token.list",
        context=ctx,
    )
    with log_context(module="token_utils", action="list_tokens", actor_id=actor_id):
        logger.info("list_tokens count=%s", len(tokens))
    return tokens


def revoke_token(
    token: Token,
    commit: bool = True,
    *,
    replaced_by: Optional[Token] = None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Token:
    ctx = {
        "function": "revoke_token",
        "token_id": _serialize_value(getattr(token, "id", None)),
        "user_id": _serialize_value(getattr(token, "user_id", None)),
        "replaced_by_id": _serialize_value(getattr(replaced_by, "id", None) if replaced_by else None),
        **(context or {}),
    }
    with log_context(module="token_utils", action="revoke_token", actor_id=actor_id):
        logger.info(
            "revoke_token token_id=%s replaced_by_id=%s commit=%s",
            ctx["token_id"],
            ctx["replaced_by_id"],
            commit,
        )
        token.revoke(replaced_by=replaced_by)
    if commit:
        db.session.commit()
        _audit(
            "token.revoke",
            actor_id,
            {
                "operation": "revoke_token",
                "token_id": ctx["token_id"],
                "user_id": ctx["user_id"],
                "replaced_by_id": ctx["replaced_by_id"],
            },
        )
    logger.info("revoke_token complete token_id=%s", ctx["token_id"])
    return token


def purge_expired_tokens(
    reference: Optional[datetime] = None,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> int:
    """
    Delete expired tokens in bulk. Returns the count of deleted rows.
    """

    if reference is None:
        reference = datetime.now(timezone.utc)

    ctx = {
        "function": "purge_expired_tokens",
        "reference": reference.isoformat(),
        **(context or {}),
    }
    with log_context(module="token_utils", action="purge_expired_tokens", actor_id=actor_id):
        logger.info("purge_expired_tokens reference=%s", reference.isoformat())
        delete_q = Token.__table__.delete().where(Token.expires_at < reference)
        result = db.session.execute(delete_q)
        db.session.commit()
        count = result.rowcount or 0
    _audit(
        "token.purge_expired",
        actor_id,
        {
            "operation": "purge_expired_tokens",
            "reference": reference.isoformat(),
            "deleted_count": count,
        },
    )
    logger.info("purge_expired_tokens complete reference=%s deleted=%s", reference.isoformat(), count)
    return count


def create_refresh_token_for_user(
    user_id,
    *,
    ttl: timedelta,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    commit: bool = True,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Tuple[Token, str]:
    ctx = {
        "function": "create_refresh_token_for_user",
        "user_id": _serialize_value(user_id),
        "ttl_seconds": int(ttl.total_seconds()),
        "user_agent": user_agent,
        "ip_address": ip_address,
        **(context or {}),
    }
    with log_context(module="token_utils", action="create_refresh_token_for_user", actor_id=actor_id):
        logger.info(
            "create_refresh_token_for_user user_id=%s ttl=%s ua=%s ip=%s commit=%s",
            ctx["user_id"],
            ttl,
            user_agent,
            ip_address,
            commit,
        )

    token, plain = Token.create_refresh_for_user(
        user_id,
        ttl,
        user_agent=user_agent,
        ip=ip_address,
    )
    if commit:
        db.session.commit()
        _audit(
            "token.refresh.create",
            actor_id,
            {
                "operation": "create_refresh_token_for_user",
                "token_id": _serialize_value(getattr(token, "id", None)),
                "user_id": ctx["user_id"],
                "ttl_seconds": ctx["ttl_seconds"],
                "user_agent": user_agent,
                "ip_address": ip_address,
            },
        )
    logger.info(
        "create_refresh_token_for_user complete token_id=%s",
        _serialize_value(getattr(token, "id", None)),
    )
    return token, plain


def find_active_refresh_token(
    user_id,
    token_hash: str,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[Token]:
    """
    Locate an active refresh token for the given user/token hash pair.
    """

    now = datetime.now(timezone.utc)
    ctx = {
        "function": "find_active_refresh_token",
        "user_id": _serialize_value(user_id),
        "token_hash": token_hash[:8] + "..." if token_hash else None,
        **(context or {}),
    }
    with log_context(module="token_utils", action="find_active_refresh_token", actor_id=actor_id):
        logger.info(
            "find_active_refresh_token user_id=%s hash_prefix=%s",
            ctx["user_id"],
            ctx["token_hash"],
        )
        token = (
            db.session.query(Token)
            .filter(
                Token.token_type == "refresh",
                Token.user_id == user_id,
                Token.token_hash == token_hash,
                Token.revoked.is_(False),
                Token.expires_at > now,
            )
            .first()
        )
    logger.info(
        "find_active_refresh_token result_found=%s user_id=%s",
        token is not None,
        ctx["user_id"],
    )
    return token
