from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import desc

from app.extensions import db
from app.models.AuditLog import AuditLog

from .base import (
    create_instance,
    get_instance,
    list_instances,
)


def create_audit_log(commit: bool = True, **attributes) -> AuditLog:
    return create_instance(AuditLog, commit=commit, **attributes)


def record_event(
    *,
    event: str,
    user_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    ip: Optional[str] = None,
    detail: Optional[str] = None,
    commit: bool = True,
) -> AuditLog:
    log = AuditLog(
        event=event,
        user_id=user_id,
        target_user_id=target_user_id,
        ip=ip,
        detail=detail,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(log)
    if commit:
        db.session.commit()
    return log


def get_audit_log_by_id(log_id) -> Optional[AuditLog]:
    return get_instance(AuditLog, log_id)


def list_audit_logs(
    *,
    filters: Optional[Sequence] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Sequence[AuditLog]:
    return list_instances(
        AuditLog,
        filters=filters,
        order_by=desc(AuditLog.created_at),
        limit=limit,
        offset=offset,
    )
