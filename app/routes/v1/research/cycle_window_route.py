from typing import Dict, Optional, Tuple
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models.Cycle import CycleWindow, Cycle
from app.models.Token import Token
from app.models.User import User
from app.models.enumerations import Role, CyclePhase
from app.routes.v1.research import research_bp
from app.schemas.cycle_schema import CycleWindowSchema
from app.utils.decorator import require_roles
from app.utils.model_utils import cycle_utils, audit_log_utils, token_utils


cycle_window_schema = CycleWindowSchema()
cycle_windows_schema = CycleWindowSchema(many=True)


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


@research_bp.route('/cycle_windows', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_cycle_window():
    """Create a new cycle window."""
    actor_id, context = _resolve_actor_context("create_cycle_window")
    
    try:
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="cycle_window.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Validate required fields
        required_fields = ['cycle_id', 'phase', 'start_date', 'end_date']
        for field in required_fields:
            if field not in payload:
                error_msg = f"Request validation failed: Missing required field '{field}'"
                log_audit_event(
                    event_type="cycle_window.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "missing_field": field},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 400

        # Validate cycle exists
        cycle = cycle_utils.get_cycle_by_id(payload['cycle_id'], actor_id=actor_id, context=context)
        if not cycle:
            error_msg = f"Validation failed: Cycle with ID {payload['cycle_id']} does not exist"
            log_audit_event(
                event_type="cycle_window.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "cycle_id": payload['cycle_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Create cycle window
        cycle_window = cycle_utils.create_cycle_window(
            commit=True,
            actor_id=actor_id,
            context=context,
            **payload
        )

        # Log successful creation
        log_audit_event(
            event_type="cycle_window.create.success",
            user_id=actor_id,
            details={
                "cycle_window_id": cycle_window.id,
                "cycle_id": cycle_window.cycle_id,
                "phase": cycle_window.phase.value,
                "start_date": str(cycle_window.start_date),
                "end_date": str(cycle_window.end_date)
            },
            ip_address=request.remote_addr
        )

        return jsonify(cycle_window_schema.dump(cycle_window)), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creating cycle window")
        error_msg = f"System error occurred while creating cycle window: {str(exc)}"
        log_audit_event(
            event_type="cycle_window.create.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/cycle_windows/<int:window_id>', methods=['GET'])
@jwt_required()
def get_cycle_window(window_id):
    """Get a specific cycle window."""
    actor_id, context = _resolve_actor_context("get_cycle_window")
    
    try:
        cycle_window = cycle_utils.get_cycle_window_by_id(window_id, actor_id=actor_id, context=context)
        if not cycle_window:
            error_msg = f"Resource not found: Cycle window with ID {window_id} does not exist"
            log_audit_event(
                event_type="cycle_window.get.failed",
                user_id=actor_id,
                details={"error": error_msg, "window_id": window_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Log successful retrieval
        log_audit_event(
            event_type="cycle_window.get.success",
            user_id=actor_id,
            details={
                "window_id": window_id,
                "cycle_id": cycle_window.cycle_id,
                "phase": cycle_window.phase.value
            },
            ip_address=request.remote_addr
        )

        return jsonify(cycle_window_schema.dump(cycle_window)), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving cycle window")
        error_msg = f"System error occurred while retrieving cycle window: {str(exc)}"
        log_audit_event(
            event_type="cycle_window.get.failed",
            user_id=actor_id,
            details={"error": error_msg, "window_id": window_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/cycle_windows', methods=['GET'])
@jwt_required()
def get_cycle_windows():
    """Get all cycle windows with filtering support."""
    actor_id, context = _resolve_actor_context("get_cycle_windows")
    
    try:
        # Get filters from query parameters
        cycle_id = request.args.get('cycle_id')
        phase = request.args.get('phase')
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(int(request.args.get('page_size', 20)), 100)

        filters = []
        if cycle_id:
            filters.append(CycleWindow.cycle_id == int(cycle_id))
        if phase:
            try:
                filters.append(CycleWindow.phase == CyclePhase[phase.upper()])
            except KeyError:
                error_msg = f"Validation failed: Invalid phase '{phase}'. Valid phases are SUBMISSION, REVIEW, EVALUATION"
                log_audit_event(
                    event_type="cycle_window.list.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "invalid_phase": phase},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 400

        # Get cycle windows
        cycle_windows = cycle_utils.list_cycle_windows(
            filters=filters,
            actor_id=actor_id,
            context={**context, "filters_applied": bool(filters)}
        )

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = cycle_windows[start:end]

        cycle_windows_data = cycle_windows_schema.dump(paginated)
        
        response = {
            'items': cycle_windows_data,
            'total': len(cycle_windows),
            'page': page,
            'pages': (len(cycle_windows) + page_size - 1) // page_size,
            'page_size': page_size
        }

        # Log successful retrieval
        log_audit_event(
            event_type="cycle_window.list.success",
            user_id=actor_id,
            details={
                "filters_applied": bool(filters),
                "cycle_id_filter": cycle_id,
                "phase_filter": phase,
                "results_count": len(paginated),
                "total_count": len(cycle_windows),
                "page": page,
                "page_size": page_size
            },
            ip_address=request.remote_addr
        )

        return jsonify(response), 200
    except Exception as exc:
        current_app.logger.exception("Error listing cycle windows")
        error_msg = f"System error occurred while retrieving cycle windows: {str(exc)}"
        log_audit_event(
            event_type="cycle_window.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/cycle_windows/<int:window_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_cycle_window(window_id):
    """Update a cycle window."""
    actor_id, context = _resolve_actor_context("update_cycle_window")
    
    try:
        cycle_window = cycle_utils.get_cycle_window_by_id(window_id, actor_id=actor_id, context=context)
        if not cycle_window:
            error_msg = f"Resource not found: Cycle window with ID {window_id} does not exist"
            log_audit_event(
                event_type="cycle_window.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "window_id": window_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="cycle_window.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "window_id": window_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Check if cycle exists if being updated
        if 'cycle_id' in payload:
            cycle = cycle_utils.get_cycle_by_id(payload['cycle_id'], actor_id=actor_id, context=context)
            if not cycle:
                error_msg = f"Validation failed: Cycle with ID {payload['cycle_id']} does not exist"
                log_audit_event(
                    event_type="cycle_window.update.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "window_id": window_id, "cycle_id": payload['cycle_id']},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 404

        # Update cycle window
        updated_cycle_window = cycle_utils.update_cycle_window(
            cycle_window,
            commit=True,
            actor_id=actor_id,
            context=context,
            **payload
        )

        # Log successful update
        log_audit_event(
            event_type="cycle_window.update.success",
            user_id=actor_id,
            details={
                "window_id": window_id,
                "cycle_id": updated_cycle_window.cycle_id,
                "phase": updated_cycle_window.phase.value,
                "start_date": str(updated_cycle_window.start_date),
                "end_date": str(updated_cycle_window.end_date),
                "updated_fields": list(payload.keys())
            },
            ip_address=request.remote_addr
        )

        return jsonify(cycle_window_schema.dump(updated_cycle_window)), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error updating cycle window")
        error_msg = f"System error occurred while updating cycle window: {str(exc)}"
        log_audit_event(
            event_type="cycle_window.update.failed",
            user_id=actor_id,
            details={"error": error_msg, "window_id": window_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/cycle_windows/<int:window_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_cycle_window(window_id):
    """Delete a cycle window."""
    actor_id, context = _resolve_actor_context("delete_cycle_window")
    
    try:
        cycle_window = cycle_utils.get_cycle_window_by_id(window_id, actor_id=actor_id, context=context)
        if not cycle_window:
            error_msg = f"Resource not found: Cycle window with ID {window_id} does not exist"
            log_audit_event(
                event_type="cycle_window.delete.failed",
                user_id=actor_id,
                details={"error": error_msg, "window_id": window_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        cycle_utils.delete_cycle_window(
            cycle_window,
            actor_id=actor_id,
            context=context,
        )

        # Log successful deletion
        log_audit_event(
            event_type="cycle_window.delete.success",
            user_id=actor_id,
            details={
                "window_id": window_id,
                "cycle_id": cycle_window.cycle_id,
                "phase": cycle_window.phase.value
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": "Cycle window deleted successfully"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error deleting cycle window")
        error_msg = f"System error occurred while deleting cycle window: {str(exc)}"
        log_audit_event(
            event_type="cycle_window.delete.failed",
            user_id=actor_id,
            details={"error": error_msg, "window_id": window_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400