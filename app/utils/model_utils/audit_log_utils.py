from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Sequence

from sqlalchemy import desc

from app.extensions import db
from app.models.AuditLog import AuditLog
from app.utils.logging_utils import get_logger, log_context

from .base import (
    _sanitize_payload,
    _serialize_value,
    create_instance,
    get_instance,
    list_instances,
)

logger = get_logger("audit_log_utils")


def create_audit_log(
    commit: bool = True,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
    **attributes,
) -> AuditLog:
    ctx = {"function": "create_audit_log", **(context or {})}
    sanitized = _sanitize_payload(attributes)
    with log_context(module="audit_log_utils", action="create_audit_log", actor_id=actor_id):
        logger.info("create_audit_log commit=%s attributes=%s", commit, sanitized)
    # If detail is provided in attributes, validate and format it
    if 'detail' in attributes:
        attributes = attributes.copy()  # Don't modify the original
        attributes['detail'] = AuditLog.validate_detail_format(attributes['detail'])
    
    log_entry = create_instance(
        AuditLog,
        commit=commit,
        actor_id=actor_id,
        event_name="audit_log.create",
        context=ctx,
        **attributes,
    )
    logger.info("create_audit_log complete id=%s", _serialize_value(getattr(log_entry, "id", None)))
    return log_entry


def record_event(
    *,
    event: str,
    user_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    ip: Optional[str] = None,
    detail: Optional[str] = None,
    commit: bool = True,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> AuditLog:
    ctx = {
        "function": "record_event",
        "event": event,
        "user_id": _serialize_value(user_id),
        "target_user_id": _serialize_value(target_user_id),
        "ip": ip,
        **(context or {}),
    }
    payload = {
        "event": event,
        "user_id": user_id,
        "target_user_id": target_user_id,
        "ip": ip,
        "detail": detail,
    }
    sanitized = _sanitize_payload(payload)

    with log_context(module="audit_log_utils", action="record_event", actor_id=actor_id):
        logger.info("record_event payload=%s commit=%s", sanitized, commit)

    # Validate and format the detail field to ensure it's properly formatted for JSON
    validated_detail = AuditLog.validate_detail_format(detail)
    
    log_entry = AuditLog(
        event=event,
        user_id=user_id,
        target_user_id=target_user_id,
        ip=ip,
        detail=validated_detail,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(log_entry)
    if commit:
        db.session.commit()

    logger.info("record_event logged id=%s", _serialize_value(getattr(log_entry, "id", None)))
    return log_entry


def get_audit_log_by_id(
    log_id,
    *,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Optional[AuditLog]:
    ctx = {"function": "get_audit_log_by_id", **(context or {})}
    with log_context(module="audit_log_utils", action="get_audit_log_by_id", actor_id=actor_id):
        logger.info("get_audit_log_by_id id=%s", _serialize_value(log_id))
    log_entry = get_instance(
        AuditLog,
        log_id,
        actor_id=actor_id,
        event_name="audit_log.get",
        context=ctx,
    )
    logger.info(
        "get_audit_log_by_id resolved id=%s found=%s",
        _serialize_value(log_id),
        log_entry is not None,
    )
    return log_entry


def list_audit_logs(
    *,
    filters: Optional[Sequence] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    actor_id: Optional[str] = None,
    context: Optional[Dict[str, object]] = None,
) -> Sequence[AuditLog]:
    ctx = {"function": "list_audit_logs", **(context or {})}
    logs = list_instances(
        AuditLog,
        filters=filters,
        order_by=desc(AuditLog.created_at),
        limit=limit,
        offset=offset,
        actor_id=actor_id,
        event_name="audit_log.list",
        context=ctx,
    )
    with log_context(module="audit_log_utils", action="list_audit_logs", actor_id=actor_id):
        logger.info(
            "list_audit_logs count=%s limit=%s offset=%s",
            len(logs),
            limit,
            offset,
        )
    return logs
