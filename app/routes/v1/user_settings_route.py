from typing import Dict, Optional, Tuple
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models.User import User, UserSettings
from app.models.Token import Token
from app.models.enumerations import Role
from flask import Blueprint

user_settings_bp = Blueprint('user_settings_bp', __name__)
from app.schemas.user_settings_schema import UserSettingsSchema
from app.utils.decorator import require_roles
from app.utils.model_utils import user_utils, audit_log_utils, token_utils


user_settings_schema = UserSettingsSchema()
user_settings_schema_many = UserSettingsSchema(many=True)


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


@user_settings_bp.route('/user_settings', methods=['POST'])
@jwt_required()
def create_user_settings():
    """Create user settings for the authenticated user."""
    actor_id, context = _resolve_actor_context("create_user_settings")
    
    try:
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="user_settings.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Validate that the user exists
        user = User.query.get(actor_id)
        if not user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="user_settings.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user settings already exist
        existing_settings = user_utils.get_user_settings_by_user_id(actor_id, actor_id=actor_id, context=context)
        if existing_settings:
            error_msg = "User settings already exist for this user"
            log_audit_event(
                event_type="user_settings.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": actor_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 409

        # Add user_id to payload
        payload['user_id'] = actor_id

        # Create user settings
        user_settings = user_utils.create_user_settings(
            commit=True,
            actor_id=actor_id,
            context=context,
            **payload
        )

        # Log successful creation
        log_audit_event(
            event_type="user_settings.create.success",
            user_id=actor_id,
            details={
                "user_settings_id": user_settings.id,
                "user_id": actor_id
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_settings_schema.dump(user_settings)), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creating user settings")
        error_msg = f"System error occurred while creating user settings: {str(exc)}"
        log_audit_event(
            event_type="user_settings.create.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_settings_bp.route('/user_settings', methods=['GET'])
@jwt_required()
def get_user_settings():
    """Get user settings for the authenticated user."""
    actor_id, context = _resolve_actor_context("get_user_settings")
    
    try:
        user_settings = user_utils.get_user_settings_by_user_id(actor_id, actor_id=actor_id, context=context)
        if not user_settings:
            error_msg = f"Resource not found: User settings for user ID {actor_id} do not exist"
            log_audit_event(
                event_type="user_settings.get.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": actor_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Log successful retrieval
        log_audit_event(
            event_type="user_settings.get.success",
            user_id=actor_id,
            details={
                "user_settings_id": user_settings.id,
                "user_id": actor_id
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_settings_schema.dump(user_settings)), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving user settings")
        error_msg = f"System error occurred while retrieving user settings: {str(exc)}"
        log_audit_event(
            event_type="user_settings.get.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_settings_bp.route('/user_settings', methods=['PUT'])
@jwt_required()
def update_user_settings():
    """Update user settings for the authenticated user."""
    actor_id, context = _resolve_actor_context("update_user_settings")
    
    try:
        user_settings = user_utils.get_user_settings_by_user_id(actor_id, actor_id=actor_id, context=context)
        if not user_settings:
            error_msg = f"Resource not found: User settings for user ID {actor_id} do not exist"
            log_audit_event(
                event_type="user_settings.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": actor_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="user_settings.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": actor_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Update user settings
        updated_user_settings = user_utils.update_user_settings(
            user_settings,
            commit=True,
            actor_id=actor_id,
            context=context,
            **payload
        )

        # Log successful update
        log_audit_event(
            event_type="user_settings.update.success",
            user_id=actor_id,
            details={
                "user_settings_id": user_settings.id,
                "user_id": actor_id,
                "updated_fields": list(payload.keys())
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_settings_schema.dump(updated_user_settings)), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error updating user settings")
        error_msg = f"System error occurred while updating user settings: {str(exc)}"
        log_audit_event(
            event_type="user_settings.update.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_settings_bp.route('/user_settings/admin/<user_id>', methods=['GET'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def get_user_settings_by_user_id(user_id):
    """Get user settings for a specific user (admin access only)."""
    actor_id, context = _resolve_actor_context("get_user_settings_by_user_id")
    
    try:
        user_settings = user_utils.get_user_settings_by_user_id(user_id, actor_id=actor_id, context=context)
        if not user_settings:
            error_msg = f"Resource not found: User settings for user ID {user_id} do not exist"
            log_audit_event(
                event_type="user_settings.admin.get.failed",
                user_id=actor_id,
                details={"error": error_msg, "target_user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Log successful admin access
        log_audit_event(
            event_type="user_settings.admin.get.success",
            user_id=actor_id,
            details={
                "user_settings_id": user_settings.id,
                "target_user_id": user_id,
                "admin_user_id": actor_id
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_settings_schema.dump(user_settings)), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving user settings by user ID")
        error_msg = f"System error occurred while retrieving user settings: {str(exc)}"
        log_audit_event(
            event_type="user_settings.admin.get.failed",
            user_id=actor_id,
            details={"error": error_msg, "target_user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_settings_bp.route('/user_settings/admin/<user_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_user_settings_admin(user_id):
    """Update user settings for a specific user (admin access only)."""
    actor_id, context = _resolve_actor_context("update_user_settings_admin")
    
    try:
        user_settings = user_utils.get_user_settings_by_user_id(user_id, actor_id=actor_id, context=context)
        if not user_settings:
            error_msg = f"Resource not found: User settings for user ID {user_id} do not exist"
            log_audit_event(
                event_type="user_settings.admin.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "target_user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="user_settings.admin.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "target_user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Update user settings
        updated_user_settings = user_utils.update_user_settings(
            user_settings,
            commit=True,
            actor_id=actor_id,
            context=context,
            **payload
        )

        # Log successful admin update
        log_audit_event(
            event_type="user_settings.admin.update.success",
            user_id=actor_id,
            details={
                "user_settings_id": user_settings.id,
                "target_user_id": user_id,
                "admin_user_id": actor_id,
                "updated_fields": list(payload.keys())
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_settings_schema.dump(updated_user_settings)), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error updating user settings by admin")
        error_msg = f"System error occurred while updating user settings: {str(exc)}"
        log_audit_event(
            event_type="user_settings.admin.update.failed",
            user_id=actor_id,
            details={"error": error_msg, "target_user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400