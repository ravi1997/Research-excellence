from typing import Dict, Optional, Tuple
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models.Cycle import Awards, AwardVerifiers, AwardCoordinators
from app.models.User import User
from app.models.Token import Token
from app.models.enumerations import Role
from app.routes.v1.research import research_bp
from app.utils.decorator import require_roles
from app.utils.model_utils import award_utils, user_utils, audit_log_utils, token_utils


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


# Award Verifiers Routes
@research_bp.route('/award_verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_award_verifier():
    """Assign a verifier to an award."""
    actor_id, context = _resolve_actor_context("create_award_verifier")
    
    try:
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="award_verifier.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Validate required fields
        required_fields = ['award_id', 'user_id']
        for field in required_fields:
            if field not in payload:
                error_msg = f"Request validation failed: Missing required field '{field}'"
                log_audit_event(
                    event_type="award_verifier.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "missing_field": field},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 400

        # Validate award exists
        award = award_utils.get_award_by_id(payload['award_id'], actor_id=actor_id, context=context)
        if not award:
            error_msg = f"Validation failed: Award with ID {payload['award_id']} does not exist"
            log_audit_event(
                event_type="award_verifier.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "award_id": payload['award_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Validate user exists
        user = user_utils.get_user_by_id(payload['user_id'], actor_id=actor_id, context=context)
        if not user:
            error_msg = f"Validation failed: User with ID {payload['user_id']} does not exist"
            log_audit_event(
                event_type="award_verifier.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": payload['user_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user is a verifier
        if not user.has_role(Role.VERIFIER.value):
            error_msg = f"Validation failed: User with ID {payload['user_id']} is not a verifier"
            log_audit_event(
                event_type="award_verifier.create.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "award_id": payload['award_id'], 
                    "user_id": payload['user_id'],
                    "user_role": user.role_associations[0].role.value if user.role_associations else "no_role"
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Check if association already exists
        existing_assoc = AwardVerifiers.query.filter_by(
            award_id=payload['award_id'],
            user_id=payload['user_id']
        ).first()
        if existing_assoc:
            error_msg = "Verifier is already assigned to this award"
            log_audit_event(
                event_type="award_verifier.create.failed",
                user_id=actor_id,
                details={
                    "error": error_msg,
                    "award_id": payload['award_id'],
                    "user_id": payload['user_id']
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 409

        # Create the association
        award_verifier = AwardVerifiers(
            award_id=payload['award_id'],
            user_id=payload['user_id']
        )
        db.session.add(award_verifier)
        db.session.commit()

        # Log successful creation
        log_audit_event(
            event_type="award_verifier.create.success",
            user_id=actor_id,
            details={
                "award_id": payload['award_id'],
                "user_id": payload['user_id']
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            "message": "Verifier assigned to award successfully",
            "award_id": payload['award_id'],
            "user_id": payload['user_id']
        }), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creating award verifier association")
        error_msg = f"System error occurred while creating award verifier association: {str(exc)}"
        log_audit_event(
            event_type="award_verifier.create.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/award_verifiers/<award_id>/<user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_award_verifier(award_id, user_id):
    """Remove a verifier from an award."""
    actor_id, context = _resolve_actor_context("delete_award_verifier")
    
    try:
        # Find the specific association
        award_verifier = AwardVerifiers.query.filter_by(
            award_id=award_id,
            user_id=user_id
        ).first()
        
        if not award_verifier:
            error_msg = f"Resource not found: Association between award ID {award_id} and user ID {user_id} does not exist"
            log_audit_event(
                event_type="award_verifier.delete.failed",
                user_id=actor_id,
                details={"error": error_msg, "award_id": award_id, "user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Remove the association
        db.session.delete(award_verifier)
        db.session.commit()

        # Log successful deletion
        log_audit_event(
            event_type="award_verifier.delete.success",
            user_id=actor_id,
            details={
                "award_id": award_id,
                "user_id": user_id
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": "Verifier removed from award successfully"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error deleting award verifier association")
        error_msg = f"System error occurred while deleting award verifier association: {str(exc)}"
        log_audit_event(
            event_type="award_verifier.delete.failed",
            user_id=actor_id,
            details={"error": error_msg, "award_id": award_id, "user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/award_coordinators', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_award_coordinator():
    """Assign a coordinator to an award."""
    actor_id, context = _resolve_actor_context("create_award_coordinator")
    
    try:
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="award_coordinator.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Validate required fields
        required_fields = ['award_id', 'user_id']
        for field in required_fields:
            if field not in payload:
                error_msg = f"Request validation failed: Missing required field '{field}'"
                log_audit_event(
                    event_type="award_coordinator.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "missing_field": field},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 400

        # Validate award exists
        award = award_utils.get_award_by_id(payload['award_id'], actor_id=actor_id, context=context)
        if not award:
            error_msg = f"Validation failed: Award with ID {payload['award_id']} does not exist"
            log_audit_event(
                event_type="award_coordinator.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "award_id": payload['award_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Validate user exists
        user = user_utils.get_user_by_id(payload['user_id'], actor_id=actor_id, context=context)
        if not user:
            error_msg = f"Validation failed: User with ID {payload['user_id']} does not exist"
            log_audit_event(
                event_type="award_coordinator.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": payload['user_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user is a coordinator
        if not user.has_role(Role.COORDINATOR.value):
            error_msg = f"Validation failed: User with ID {payload['user_id']} is not a coordinator"
            log_audit_event(
                event_type="award_coordinator.create.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "award_id": payload['award_id'], 
                    "user_id": payload['user_id'],
                    "user_role": user.role_associations[0].role.value if user.role_associations else "no_role"
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Check if association already exists
        existing_assoc = AwardCoordinators.query.filter_by(
            award_id=payload['award_id'],
            user_id=payload['user_id']
        ).first()
        if existing_assoc:
            error_msg = "Coordinator is already assigned to this award"
            log_audit_event(
                event_type="award_coordinator.create.failed",
                user_id=actor_id,
                details={
                    "error": error_msg,
                    "award_id": payload['award_id'],
                    "user_id": payload['user_id']
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 409

        # Create the association
        award_coordinator = AwardCoordinators(
            award_id=payload['award_id'],
            user_id=payload['user_id']
        )
        db.session.add(award_coordinator)
        db.session.commit()

        # Log successful creation
        log_audit_event(
            event_type="award_coordinator.create.success",
            user_id=actor_id,
            details={
                "award_id": payload['award_id'],
                "user_id": payload['user_id']
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            "message": "Coordinator assigned to award successfully",
            "award_id": payload['award_id'],
            "user_id": payload['user_id']
        }), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creating award coordinator association")
        error_msg = f"System error occurred while creating award coordinator association: {str(exc)}"
        log_audit_event(
            event_type="award_coordinator.create.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/award_coordinators/<award_id>/<user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_award_coordinator(award_id, user_id):
    """Remove a coordinator from an award."""
    actor_id, context = _resolve_actor_context("delete_award_coordinator")
    
    try:
        # Find the specific association
        award_coordinator = AwardCoordinators.query.filter_by(
            award_id=award_id,
            user_id=user_id
        ).first()
        
        if not award_coordinator:
            error_msg = f"Resource not found: Association between award ID {award_id} and user ID {user_id} does not exist"
            log_audit_event(
                event_type="award_coordinator.delete.failed",
                user_id=actor_id,
                details={"error": error_msg, "award_id": award_id, "user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Remove the association
        db.session.delete(award_coordinator)
        db.session.commit()

        # Log successful deletion
        log_audit_event(
            event_type="award_coordinator.delete.success",
            user_id=actor_id,
            details={
                "award_id": award_id,
                "user_id": user_id
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": "Coordinator removed from award successfully"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error deleting award coordinator association")
        error_msg = f"System error occurred while deleting award coordinator association: {str(exc)}"
        log_audit_event(
            event_type="award_coordinator.delete.failed",
            user_id=actor_id,
            details={"error": error_msg, "award_id": award_id, "user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/awards/<award_id>/verifiers', methods=['GET'])
@jwt_required()
def get_verifiers_by_award(award_id):
    """Get all verifiers associated with a specific award."""
    actor_id, context = _resolve_actor_context("get_verifiers_by_award")
    
    try:
        # First, verify that the award exists
        award = award_utils.get_award_by_id(award_id, actor_id=actor_id, context=context)
        if not award:
            error_msg = f"Resource not found: Award with ID {award_id} does not exist"
            log_audit_event(
                event_type="award_verifiers.list.failed",
                user_id=actor_id,
                details={"error": error_msg, "award_id": award_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user has permission to view this award
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="award_verifiers.list.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check permissions - allow if:
        # 1. User is admin/superadmin
        # 2. User is the creator of the award
        # 3. User is a verifier for this award
        # 4. User is a coordinator for this award
        privileged = any(
            current_user.has_role(role)
            for role in (Role.ADMIN.value, Role.SUPERADMIN.value)
        )
        
        if not privileged:
            if (award.created_by_id != actor_id and
                not any(verifier.id == actor_id for verifier in award.verifiers) and
                not any(coordinator.id == actor_id for coordinator in award.coordinators)):
                error_msg = f"Authorization failed: You are not authorized to access award ID {award_id}"
                log_audit_event(
                    event_type="award_verifiers.list.failed",
                    user_id=actor_id,
                    details={
                        "error": error_msg, 
                        "award_id": award_id,
                        "user_id": actor_id,
                        "user_role": current_user.role_associations[0].role.value if current_user.role_associations else "no_role"
                    },
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 403

        # Get all verifiers associated with this award
        award_verifiers = AwardVerifiers.query.filter_by(award_id=award_id).all()
        
        # Get the actual user details for each association
        verifiers_data = []
        for av in award_verifiers:
            user = user_utils.get_user_by_id(av.user_id, actor_id=actor_id, context=context)
            if user:
                verifiers_data.append({
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'employee_id': user.employee_id,
                })

        # Log successful retrieval
        log_audit_event(
            event_type="award_verifiers.list.success",
            user_id=actor_id,
            details={
                "award_id": award_id,
                "verifiers_count": len(verifiers_data)
            },
            ip_address=request.remote_addr
        )

        return jsonify(verifiers_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving verifiers for award")
        error_msg = f"System error occurred while retrieving verifiers for award: {str(exc)}"
        log_audit_event(
            event_type="award_verifiers.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "award_id": award_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/awards/<award_id>/coordinators', methods=['GET'])
@jwt_required()
def get_coordinators_by_award(award_id):
    """Get all coordinators associated with a specific award."""
    actor_id, context = _resolve_actor_context("get_coordinators_by_award")
    
    try:
        # First, verify that the award exists
        award = award_utils.get_award_by_id(award_id, actor_id=actor_id, context=context)
        if not award:
            error_msg = f"Resource not found: Award with ID {award_id} does not exist"
            log_audit_event(
                event_type="award_coordinators.list.failed",
                user_id=actor_id,
                details={"error": error_msg, "award_id": award_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user has permission to view this award
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="award_coordinators.list.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check permissions - allow if:
        # 1. User is admin/superadmin
        # 2. User is the creator of the award
        # 3. User is a verifier for this award
        # 4. User is a coordinator for this award
        privileged = any(
            current_user.has_role(role)
            for role in (Role.ADMIN.value, Role.SUPERADMIN.value)
        )
        
        if not privileged:
            if (award.created_by_id != actor_id and
                not any(verifier.id == actor_id for verifier in award.verifiers) and
                not any(coordinator.id == actor_id for coordinator in award.coordinators)):
                error_msg = f"Authorization failed: You are not authorized to access award ID {award_id}"
                log_audit_event(
                    event_type="award_coordinators.list.failed",
                    user_id=actor_id,
                    details={
                        "error": error_msg, 
                        "award_id": award_id,
                        "user_id": actor_id,
                        "user_role": current_user.role_associations[0].role.value if current_user.role_associations else "no_role"
                    },
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 403

        # Get all coordinators associated with this award
        award_coordinators = AwardCoordinators.query.filter_by(award_id=award_id).all()
        
        # Get the actual user details for each association
        coordinators_data = []
        for ac in award_coordinators:
            user = user_utils.get_user_by_id(ac.user_id, actor_id=actor_id, context=context)
            if user:
                coordinators_data.append({
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'employee_id': user.employee_id,
                })

        # Log successful retrieval
        log_audit_event(
            event_type="award_coordinators.list.success",
            user_id=actor_id,
            details={
                "award_id": award_id,
                "coordinators_count": len(coordinators_data)
            },
            ip_address=request.remote_addr
        )

        return jsonify(coordinators_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving coordinators for award")
        error_msg = f"System error occurred while retrieving coordinators for award: {str(exc)}"
        log_audit_event(
            event_type="award_coordinators.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "award_id": award_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/verifiers/<user_id>/awards', methods=['GET'])
@jwt_required()
def get_awards_by_verifier(user_id):
    """Get all awards assigned to a specific verifier."""
    actor_id, context = _resolve_actor_context("get_awards_by_verifier")
    
    try:
        # First, verify that the user exists
        user = user_utils.get_user_by_id(user_id, actor_id=actor_id, context=context)
        if not user:
            error_msg = f"Resource not found: User with ID {user_id} does not exist"
            log_audit_event(
                event_type="verifier_awards.list.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user is a verifier
        if not user.has_role(Role.VERIFIER.value):
            error_msg = f"Validation failed: User with ID {user_id} is not a verifier"
            log_audit_event(
                event_type="verifier_awards.list.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "user_id": user_id,
                    "user_role": user.role_associations[0].role.value if user.role_associations else "no_role"
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Check if the requesting user has permission to see this information
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="verifier_awards.list.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Allow access if:
        # 1. Requesting user is admin/superadmin
        # 2. Requesting user is the verifier in question
        privileged = any(
            current_user.has_role(role)
            for role in (Role.ADMIN.value, Role.SUPERADMIN.value)
        )
        
        if not privileged and str(actor_id) != user_id:
            error_msg = f"Authorization failed: You are not authorized to access verifier ID {user_id}'s awards"
            log_audit_event(
                event_type="verifier_awards.list.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "target_user_id": user_id,
                    "requesting_user_id": actor_id,
                    "requesting_user_role": current_user.role_associations[0].role.value if current_user.role_associations else "no_role"
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 403

        # Get all award-verifier associations for this user
        award_verifiers = AwardVerifiers.query.filter_by(user_id=user_id).all()
        
        # Get the actual award details for each association
        awards_data = []
        for av in award_verifiers:
            award = award_utils.get_award_by_id(av.award_id, actor_id=actor_id, context=context)
            if award:
                awards_data.append({
                    'id': str(award.id),
                    'name': award.name,
                    'description': award.description,
                    'award_type': award.award_type.value if award.award_type else None,
                })

        # Log successful retrieval
        log_audit_event(
            event_type="verifier_awards.list.success",
            user_id=actor_id,
            details={
                "user_id": user_id,
                "awards_count": len(awards_data)
            },
            ip_address=request.remote_addr
        )

        return jsonify(awards_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving awards for verifier")
        error_msg = f"System error occurred while retrieving awards for verifier: {str(exc)}"
        log_audit_event(
            event_type="verifier_awards.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/coordinators/<user_id>/awards', methods=['GET'])
@jwt_required()
def get_awards_by_coordinator(user_id):
    """Get all awards assigned to a specific coordinator."""
    actor_id, context = _resolve_actor_context("get_awards_by_coordinator")
    
    try:
        # First, verify that the user exists
        user = user_utils.get_user_by_id(user_id, actor_id=actor_id, context=context)
        if not user:
            error_msg = f"Resource not found: User with ID {user_id} does not exist"
            log_audit_event(
                event_type="coordinator_awards.list.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user is a coordinator
        if not user.has_role(Role.COORDINATOR.value):
            error_msg = f"Validation failed: User with ID {user_id} is not a coordinator"
            log_audit_event(
                event_type="coordinator_awards.list.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "user_id": user_id,
                    "user_role": user.role_associations[0].role.value if user.role_associations else "no_role"
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Check if the requesting user has permission to see this information
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="coordinator_awards.list.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Allow access if:
        # 1. Requesting user is admin/superadmin
        # 2. Requesting user is the coordinator in question
        privileged = any(
            current_user.has_role(role)
            for role in (Role.ADMIN.value, Role.SUPERADMIN.value)
        )
        
        if not privileged and str(actor_id) != user_id:
            error_msg = f"Authorization failed: You are not authorized to access coordinator ID {user_id}'s awards"
            log_audit_event(
                event_type="coordinator_awards.list.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "target_user_id": user_id,
                    "requesting_user_id": actor_id,
                    "requesting_user_role": current_user.role_associations[0].role.value if current_user.role_associations else "no_role"
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 403

        # Get all award-coordinator associations for this user
        award_coordinators = AwardCoordinators.query.filter_by(user_id=user_id).all()
        
        # Get the actual award details for each association
        awards_data = []
        for ac in award_coordinators:
            award = award_utils.get_award_by_id(ac.award_id, actor_id=actor_id, context=context)
            if award:
                awards_data.append({
                    'id': str(award.id),
                    'name': award.name,
                    'description': award.description,
                    'award_type': award.award_type.value if award.award_type else None,
                })

        # Log successful retrieval
        log_audit_event(
            event_type="coordinator_awards.list.success",
            user_id=actor_id,
            details={
                "user_id": user_id,
                "awards_count": len(awards_data)
            },
            ip_address=request.remote_addr
        )

        return jsonify(awards_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving awards for coordinator")
        error_msg = f"System error occurred while retrieving awards for coordinator: {str(exc)}"
        log_audit_event(
            event_type="coordinator_awards.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400