from typing import Dict, Optional, Tuple
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models.User import User, UserRole
from app.models.Token import Token
from app.models.enumerations import Role
from flask import Blueprint

user_role_bp = Blueprint('user_role_bp', __name__)
from app.schemas.user_role_schema import UserRoleSchema
from app.utils.decorator import require_roles
from app.utils.model_utils import user_utils, audit_log_utils, token_utils


user_role_schema = UserRoleSchema()
user_roles_schema = UserRoleSchema(many=True)


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


@user_role_bp.route('/user_roles', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_user_role():
    """Create a new user role assignment."""
    actor_id, context = _resolve_actor_context("create_user_role")
    
    try:
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="user_role.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Validate required fields
        required_fields = ['user_id', 'role']
        for field in required_fields:
            if field not in payload:
                error_msg = f"Request validation failed: Missing required field '{field}'"
                log_audit_event(
                    event_type="user_role.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "missing_field": field},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 400

        # Validate user exists
        user = user_utils.get_user_by_id(payload['user_id'], actor_id=actor_id, context=context)
        if not user:
            error_msg = f"Validation failed: User with ID {payload['user_id']} does not exist"
            log_audit_event(
                event_type="user_role.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": payload['user_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if role already exists for this user
        existing_user_roles = user_utils.get_user_roles_by_user_id(payload['user_id'], actor_id=actor_id, context=context)
        for role in existing_user_roles:
            if role.role.value == payload['role']:
                error_msg = f"Validation failed: User already has role '{payload['role']}'"
                log_audit_event(
                    event_type="user_role.create.failed",
                    user_id=actor_id,
                    details={
                        "error": error_msg, 
                        "user_id": payload['user_id'], 
                        "role": payload['role']
                    },
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 409

        # Create user role
        user_role = user_utils.create_user_role(
            commit=True,
            actor_id=actor_id,
            context=context,
            **payload
        )

        # Log successful creation
        log_audit_event(
            event_type="user_role.create.success",
            user_id=actor_id,
            details={
                "user_role_id": user_role.id,
                "user_id": user_role.user_id,
                "role": user_role.role.value
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_role_schema.dump(user_role)), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creating user role")
        error_msg = f"System error occurred while creating user role: {str(exc)}"
        log_audit_event(
            event_type="user_role.create.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_role_bp.route('/user_roles/<int:role_id>', methods=['GET'])
@jwt_required()
def get_user_role(role_id):
    """Get a specific user role."""
    actor_id, context = _resolve_actor_context("get_user_role")
    
    try:
        user_role = user_utils.get_user_role_by_id(role_id, actor_id=actor_id, context=context)
        if not user_role:
            error_msg = f"Resource not found: User role with ID {role_id} does not exist"
            log_audit_event(
                event_type="user_role.get.failed",
                user_id=actor_id,
                details={"error": error_msg, "role_id": role_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if the user can access this role record
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="user_role.get.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Allow access if:
        # 1. User is admin/superadmin
        # 2. User is accessing their own role
        if not (current_user.has_role(Role.ADMIN.value) or 
                current_user.has_role(Role.SUPERADMIN.value) or 
                user_role.user_id == actor_id):
            error_msg = f"Authorization failed: You are not authorized to access role ID {role_id}"
            log_audit_event(
                event_type="user_role.get.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "role_id": role_id,
                    "user_id": actor_id,
                    "user_role_user_id": user_role.user_id
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 403

        # Log successful retrieval
        log_audit_event(
            event_type="user_role.get.success",
            user_id=actor_id,
            details={
                "role_id": role_id,
                "user_id": user_role.user_id,
                "role": user_role.role.value
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_role_schema.dump(user_role)), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving user role")
        error_msg = f"System error occurred while retrieving user role: {str(exc)}"
        log_audit_event(
            event_type="user_role.get.failed",
            user_id=actor_id,
            details={"error": error_msg, "role_id": role_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_role_bp.route('/user_roles', methods=['GET'])
@jwt_required()
def get_user_roles():
    """Get all user roles with filtering support."""
    actor_id, context = _resolve_actor_context("get_user_roles")
    
    try:
        # Get filters from query parameters
        user_id = request.args.get('user_id')
        role = request.args.get('role')
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(int(request.args.get('page_size', 20)), 100)

        # Check if user has admin privileges
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="user_role.list.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        filters = []
        if current_user.has_role(Role.ADMIN.value) or current_user.has_role(Role.SUPERADMIN.value):
            # Admins can see all roles
            if user_id:
                filters.append(UserRole.user_id == user_id)
            if role:
                try:
                    from app.models.enumerations import Role as RoleEnum
                    filters.append(UserRole.role == RoleEnum[role.upper()])
                except KeyError:
                    error_msg = f"Validation failed: Invalid role '{role}'. Valid roles are USER, ADMIN, SUPERADMIN, VERIFIER, COORDINATOR"
                    log_audit_event(
                        event_type="user_role.list.failed",
                        user_id=actor_id,
                        details={"error": error_msg, "invalid_role": role},
                        ip_address=request.remote_addr
                    )
                    return jsonify({"error": error_msg}), 400
        else:
            # Regular users can only see their own roles
            filters.append(UserRole.user_id == actor_id)
            if user_id and user_id != str(actor_id):
                error_msg = "Authorization failed: You can only view your own roles"
                log_audit_event(
                    event_type="user_role.list.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "requested_user_id": user_id, "actual_user_id": actor_id},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 403

        # Get user roles
        user_roles = user_utils.list_user_roles(
            filters=filters,
            actor_id=actor_id,
            context={**context, "filters_applied": bool(filters)}
        )

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = user_roles[start:end]

        user_roles_data = user_roles_schema.dump(paginated)
        
        response = {
            'items': user_roles_data,
            'total': len(user_roles),
            'page': page,
            'pages': (len(user_roles) + page_size - 1) // page_size,
            'page_size': page_size
        }

        # Log successful retrieval
        log_audit_event(
            event_type="user_role.list.success",
            user_id=actor_id,
            details={
                "filters_applied": bool(filters),
                "user_id_filter": user_id,
                "role_filter": role,
                "results_count": len(paginated),
                "total_count": len(user_roles),
                "page": page,
                "page_size": page_size
            },
            ip_address=request.remote_addr
        )

        return jsonify(response), 200
    except Exception as exc:
        current_app.logger.exception("Error listing user roles")
        error_msg = f"System error occurred while retrieving user roles: {str(exc)}"
        log_audit_event(
            event_type="user_role.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_role_bp.route('/user_roles/<int:role_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_user_role(role_id):
    """Update a user role."""
    actor_id, context = _resolve_actor_context("update_user_role")
    
    try:
        user_role = user_utils.get_user_role_by_id(role_id, actor_id=actor_id, context=context)
        if not user_role:
            error_msg = f"Resource not found: User role with ID {role_id} does not exist"
            log_audit_event(
                event_type="user_role.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "role_id": role_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="user_role.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "role_id": role_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Update user role
        updated_user_role = user_utils.update_user_role(
            user_role,
            commit=True,
            actor_id=actor_id,
            context=context,
            **payload
        )

        # Log successful update
        log_audit_event(
            event_type="user_role.update.success",
            user_id=actor_id,
            details={
                "role_id": role_id,
                "user_id": updated_user_role.user_id,
                "role": updated_user_role.role.value,
                "updated_fields": list(payload.keys())
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_role_schema.dump(updated_user_role)), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error updating user role")
        error_msg = f"System error occurred while updating user role: {str(exc)}"
        log_audit_event(
            event_type="user_role.update.failed",
            user_id=actor_id,
            details={"error": error_msg, "role_id": role_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_role_bp.route('/user_roles/<int:role_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_user_role(role_id):
    """Delete a user role."""
    actor_id, context = _resolve_actor_context("delete_user_role")
    
    try:
        user_role = user_utils.get_user_role_by_id(role_id, actor_id=actor_id, context=context)
        if not user_role:
            error_msg = f"Resource not found: User role with ID {role_id} does not exist"
            log_audit_event(
                event_type="user_role.delete.failed",
                user_id=actor_id,
                details={"error": error_msg, "role_id": role_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Prevent removing the last admin role if user has only one role
        user_roles = user_utils.get_user_roles_by_user_id(user_role.user_id, actor_id=actor_id, context=context)
        if len(user_roles) <= 1:
            # Check if this is an admin role
            if user_role.role == Role.ADMIN or user_role.role == Role.SUPERADMIN:
                other_admins = []
                all_user_roles = user_utils.list_user_roles(actor_id=actor_id, context=context)
                for ur in all_user_roles:
                    if ur.role in [Role.ADMIN, Role.SUPERADMIN] and ur.id != role_id:
                        other_admins.append(ur.user_id)
                
                if not other_admins:
                    error_msg = "Validation failed: Cannot remove the last admin role from the system"
                    log_audit_event(
                        event_type="user_role.delete.failed",
                        user_id=actor_id,
                        details={"error": error_msg, "role_id": role_id, "user_id": user_role.user_id},
                        ip_address=request.remote_addr
                    )
                    return jsonify({"error": error_msg}), 400

        user_utils.delete_user_role(
            user_role,
            actor_id=actor_id,
            context=context,
        )

        # Log successful deletion
        log_audit_event(
            event_type="user_role.delete.success",
            user_id=actor_id,
            details={
                "role_id": role_id,
                "user_id": user_role.user_id,
                "role": user_role.role.value
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": "User role deleted successfully"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error deleting user role")
        error_msg = f"System error occurred while deleting user role: {str(exc)}"
        log_audit_event(
            event_type="user_role.delete.failed",
            user_id=actor_id,
            details={"error": error_msg, "role_id": role_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@user_role_bp.route('/user_roles/user/<user_id>', methods=['GET'])
@jwt_required()
def get_user_roles_by_user_id(user_id):
    """Get all roles for a specific user."""
    actor_id, context = _resolve_actor_context("get_user_roles_by_user_id")
    
    try:
        # Check if user exists
        user = user_utils.get_user_by_id(user_id, actor_id=actor_id, context=context)
        if not user:
            error_msg = f"Resource not found: User with ID {user_id} does not exist"
            log_audit_event(
                event_type="user_role.by_user.failed",
                user_id=actor_id,
                details={"error": error_msg, "target_user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check authorization
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="user_role.by_user.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Allow access if:
        # 1. User is admin/superadmin
        # 2. User is accessing their own roles
        if not (current_user.has_role(Role.ADMIN.value) or 
                current_user.has_role(Role.SUPERADMIN.value) or 
                user_id == str(actor_id)):
            error_msg = f"Authorization failed: You are not authorized to access roles for user ID {user_id}"
            log_audit_event(
                event_type="user_role.by_user.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "target_user_id": user_id,
                    "requesting_user_id": actor_id
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 403

        # Get user roles
        user_roles = user_utils.get_user_roles_by_user_id(user_id, actor_id=actor_id, context=context)

        user_roles_data = user_roles_schema.dump(user_roles)

        # Log successful retrieval
        log_audit_event(
            event_type="user_role.by_user.success",
            user_id=actor_id,
            details={
                "target_user_id": user_id,
                "roles_count": len(user_roles_data),
                "roles": [ur['role'] for ur in user_roles_data]
            },
            ip_address=request.remote_addr
        )

        return jsonify(user_roles_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving user roles by user ID")
        error_msg = f"System error occurred while retrieving user roles: {str(exc)}"
        log_audit_event(
            event_type="user_role.by_user.failed",
            user_id=actor_id,
            details={"error": error_msg, "target_user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400