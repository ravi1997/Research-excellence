from typing import Dict, Optional, Tuple
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models.AuditLog import AuditLog
from app.models.Token import Token
from app.models.User import User
from app.models.enumerations import Role
from flask import Blueprint

audit_log_bp = Blueprint('audit_log_bp', __name__)
from app.schemas.audit_log_schema import AuditLogSchema
from app.utils.decorator import require_roles
from app.utils.model_utils import audit_log_utils, token_utils


audit_log_schema = AuditLogSchema()
audit_logs_schema = AuditLogSchema(many=True)


def log_audit_event(event_type, user_id, details, ip_address=None, target_user_id=None):
    """Helper function to create audit logs with proper transaction handling"""
    try:
        # Create audit log without committing to avoid transaction issues
        audit_log_utils.create_audit_log(
            event=event_type,
            user_id=user_id,
            target_user_id=target_user_id,
            ip=ip_address,
            detail=json.dumps(details) if isinstance(details, dict) else details,
            actor_id=user_id,
            commit=False  # Don't commit here to avoid transaction issues
        )
        db.session.commit() # Commit only this specific operation
    except Exception as e:
        current_app.logger.error(f"Failed to create audit log: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass  # Ignore rollback errors in error handling


def _resolve_actor_context(action: str) -> Tuple[Optional[str], Dict[str, object]]:
    """
    Resolve the acting user and build a context payload that reuses the shared
    token utilities so every route benefits from consistent logging.
    """

    actor_identity = get_jwt_identity()
    actor_id = str(actor_identity) if actor_identity is not None else None
    jwt_payload = get_jwt()
    token_jti: Optional[str] = jwt_payload.get("jti") if jwt_payload else None

    filters = [Token.jti == token_jti] if token_jti else [Token.id == 0]
    tokens = token_utils.list_tokens(
        filters=filters,
        actor_id=actor_id,
        context={"route": action, "token_jti": token_jti or "none"},
    )

    context: Dict[str, object] = {"route": action}
    if actor_id:
        context["actor_id"] = actor_id
    if token_jti:
        context["token_jti"] = token_jti
    if tokens:
        context["token_record_id"] = tokens[0].id

    return actor_id, context


@audit_log_bp.route('/audit_logs', methods=['GET'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def get_audit_logs():
    """Get all audit logs with filtering support."""
    actor_id, context = _resolve_actor_context("get_audit_logs")
    
    try:
        # Get filters from query parameters
        user_id = request.args.get('user_id')
        event = request.args.get('event')
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(int(request.args.get('page_size', 20)), 100)
        sort_by = request.args.get('sort', 'id')
        sort_dir = request.args.get('dir', 'desc').lower()

        filters = []
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if event:
            filters.append(AuditLog.event == event)

        # Get audit logs
        audit_logs = audit_log_utils.list_audit_logs(
            filters=filters,
            actor_id=actor_id,
            context={**context, "filters_applied": bool(filters)}
        )

        # Apply sorting
        if sort_by == 'timestamp':
            if sort_dir == 'asc':
                audit_logs.sort(key=lambda x: x.timestamp)
            else:
                audit_logs.sort(key=lambda x: x.timestamp, reverse=True)
        elif sort_by == 'id':
            if sort_dir == 'asc':
                audit_logs.sort(key=lambda x: x.id)
            else:
                audit_logs.sort(key=lambda x: x.id, reverse=True)
        # Add more sorting options if needed

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = audit_logs[start:end]

        audit_logs_data = audit_logs_schema.dump(paginated)
        
        response = {
            'items': audit_logs_data,
            'total': len(audit_logs),
            'page': page,
            'pages': (len(audit_logs) + page_size - 1) // page_size,
            'page_size': page_size
        }

        # Log this operation for tracking
        log_audit_event(
            event_type="audit_log.access",
            user_id=actor_id,
            details={
                "operation": "list",
                "filters_applied": bool(filters),
                "user_id_filter": user_id,
                "event_filter": event,
                "results_count": len(paginated),
                "total_count": len(audit_logs),
                "page": page,
                "page_size": page_size,
                "sort_by": sort_by,
                "sort_dir": sort_dir
            },
            ip_address=request.remote_addr
        )

        return jsonify(response), 200
    except Exception as exc:
        current_app.logger.exception("Error listing audit logs")
        error_msg = f"System error occurred while retrieving audit logs: {str(exc)}"
        log_audit_event(
            event_type="audit_log.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@audit_log_bp.route('/audit_logs/<int:log_id>', methods=['GET'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def get_audit_log(log_id):
    """Get a specific audit log."""
    actor_id, context = _resolve_actor_context("get_audit_log")
    
    try:
        audit_log_entry = audit_log_utils.get_audit_log_by_id(log_id, actor_id=actor_id, context=context)
        if not audit_log_entry:
            error_msg = f"Resource not found: Audit log with ID {log_id} does not exist"
            log_audit_event(
                event_type="audit_log.get.failed",
                user_id=actor_id,
                details={"error": error_msg, "log_id": log_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Log this operation for tracking
        log_audit_event(
            event_type="audit_log.access",
            user_id=actor_id,
            details={
                "operation": "get",
                "log_id": log_id,
                "event": audit_log_entry.event,
                "user_id": audit_log_entry.user_id
            },
            ip_address=request.remote_addr
        )

        return jsonify(audit_log_schema.dump(audit_log_entry)), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving audit log")
        error_msg = f"System error occurred while retrieving audit log: {str(exc)}"
        log_audit_event(
            event_type="audit_log.get.failed",
            user_id=actor_id,
            details={"error": error_msg, "log_id": log_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400