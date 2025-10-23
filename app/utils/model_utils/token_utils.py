from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence, Tuple

from sqlalchemy import and_

from app.extensions import db
from app.models.Token import Token

from .base import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
)


def create_token(commit: bool = True, **attributes) -> Token:
    return create_instance(Token, commit=commit, **attributes)


def get_token_by_id(token_id) -> Optional[Token]:
    return get_instance(Token, token_id)


def list_tokens(*, filters: Optional[Sequence] = None, order_by=None) -> Sequence[Token]:
    return list_instances(Token, filters=filters, order_by=order_by)


def revoke_token(token: Token, commit: bool = True, replaced_by: Optional[Token] = None) -> Token:
    token.revoke(replaced_by=replaced_by)
    if commit:
        db.session.commit()
    return token


def purge_expired_tokens(reference: Optional[datetime] = None) -> int:
    """
    Delete expired tokens in bulk. Returns the count of deleted rows.  The
    reference time defaults to ``datetime.now(timezone.utc)``.
    """

    if reference is None:
        reference = datetime.now(timezone.utc)

    delete_q = Token.__table__.delete().where(Token.expires_at < reference)
    result = db.session.execute(delete_q)
    db.session.commit()
    return result.rowcount or 0


def create_refresh_token_for_user(
    user_id,
    *,
    ttl: timedelta,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    commit: bool = True,
) -> Tuple[Token, str]:
    token, plain = Token.create_refresh_for_user(
        user_id,
        ttl,
        user_agent=user_agent,
        ip=ip_address,
    )
    if commit:
        db.session.commit()
    return token, plain


def find_active_refresh_token(user_id, token_hash: str) -> Optional[Token]:
    """
    Locate an active refresh token for the given user/token hash pair.
    """

    now = datetime.now(timezone.utc)
    return (
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
