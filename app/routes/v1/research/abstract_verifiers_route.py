from typing import Dict, Optional, Tuple
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models.Cycle import Abstracts, AbstractVerifiers
from app.models.User import User
from app.models.Token import Token
from app.models.enumerations import Role
from app.routes.v1.research import research_bp
from app.utils.decorator import require_roles
from app.utils.model_utils import abstract_utils, user_utils, audit_log_utils, token_utils


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


@research_bp.route('/abstract_verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_abstract_verifier():
    """Assign a verifier to an abstract."""
    actor_id, context = _resolve_actor_context("create_abstract_verifier")
    
    try:
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="abstract_verifier.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Validate required fields
        required_fields = ['abstract_id', 'user_id']
        for field in required_fields:
            if field not in payload:
                error_msg = f"Request validation failed: Missing required field '{field}'"
                log_audit_event(
                    event_type="abstract_verifier.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "missing_field": field},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 40

        # Validate abstract exists
        abstract = abstract_utils.get_abstract_by_id(payload['abstract_id'], actor_id=actor_id, context=context)
        if not abstract:
            error_msg = f"Validation failed: Abstract with ID {payload['abstract_id']} does not exist"
            log_audit_event(
                event_type="abstract_verifier.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": payload['abstract_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Validate user exists
        user = user_utils.get_user_by_id(payload['user_id'], actor_id=actor_id, context=context)
        if not user:
            error_msg = f"Validation failed: User with ID {payload['user_id']} does not exist"
            log_audit_event(
                event_type="abstract_verifier.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": payload['user_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user is a verifier
        if not user.has_role(Role.VERIFIER.value):
            error_msg = f"Validation failed: User with ID {payload['user_id']} is not a verifier"
            log_audit_event(
                event_type="abstract_verifier.create.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "abstract_id": payload['abstract_id'], 
                    "user_id": payload['user_id'],
                    "user_role": user.role_associations[0].role.value if user.role_associations else "no_role"
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Check if association already exists
        existing_assoc = AbstractVerifiers.query.filter_by(
            abstract_id=payload['abstract_id'],
            user_id=payload['user_id']
        ).first()
        if existing_assoc:
            error_msg = "Verifier is already assigned to this abstract"
            log_audit_event(
                event_type="abstract_verifier.create.failed",
                user_id=actor_id,
                details={
                    "error": error_msg,
                    "abstract_id": payload['abstract_id'],
                    "user_id": payload['user_id']
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 409

        # Create the association
        abstract_verifier = AbstractVerifiers(
            abstract_id=payload['abstract_id'],
            user_id=payload['user_id']
        )
        db.session.add(abstract_verifier)
        db.session.commit()

        # Log successful creation
        log_audit_event(
            event_type="abstract_verifier.create.success",
            user_id=actor_id,
            details={
                "abstract_id": payload['abstract_id'],
                "user_id": payload['user_id']
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            "message": "Verifier assigned to abstract successfully",
            "abstract_id": payload['abstract_id'],
            "user_id": payload['user_id']
        }), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creating abstract verifier association")
        error_msg = f"System error occurred while creating abstract verifier association: {str(exc)}"
        log_audit_event(
            event_type="abstract_verifier.create.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/abstracts/<abstract_id>/verifiers/<user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_abstract_verifier(abstract_id, user_id):
    """Remove a verifier from an abstract."""
    actor_id, context = _resolve_actor_context("delete_abstract_verifier")
    
    try:
        # Find the specific association
        abstract_verifier = AbstractVerifiers.query.filter_by(
            abstract_id=abstract_id,
            user_id=user_id
        ).first()
        
        if not abstract_verifier:
            error_msg = f"Resource not found: Association between abstract ID {abstract_id} and user ID {user_id} does not exist"
            log_audit_event(
                event_type="abstract_verifier.delete.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": abstract_id, "user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Remove the association
        db.session.delete(abstract_verifier)
        db.session.commit()

        # Log successful deletion
        log_audit_event(
            event_type="abstract_verifier.delete.success",
            user_id=actor_id,
            details={
                "abstract_id": abstract_id,
                "user_id": user_id
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": "Verifier removed from abstract successfully"}), 20
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error deleting abstract verifier association")
        error_msg = f"System error occurred while deleting abstract verifier association: {str(exc)}"
        log_audit_event(
            event_type="abstract_verifier.delete.failed",
            user_id=actor_id,
            details={"error": error_msg, "abstract_id": abstract_id, "user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 40


@research_bp.route('/abstracts/<abstract_id>/verifiers', methods=['GET'])
@jwt_required()
def get_verifiers_by_abstract(abstract_id):
    """Get all verifiers associated with a specific abstract."""
    actor_id, context = _resolve_actor_context("get_verifiers_by_abstract")
    
    try:
        # First, verify that the abstract exists
        abstract = abstract_utils.get_abstract_by_id(abstract_id, actor_id=actor_id, context=context)
        if not abstract:
            error_msg = f"Resource not found: Abstract with ID {abstract_id} does not exist"
            log_audit_event(
                event_type="abstract_verifiers.list.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": abstract_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user has permission to view this abstract
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="abstract_verifiers.list.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check permissions - allow if:
        # 1. User is admin/superadmin
        # 2. User is the creator of the abstract
        # 3. User is a verifier for this abstract
        # 4. User is a coordinator for this abstract
        privileged = any(
            current_user.has_role(role)
            for role in (Role.ADMIN.value, Role.SUPERADMIN.value)
        )
        
        if not privileged:
            if (abstract.created_by_id != actor_id and
                not any(verifier.id == actor_id for verifier in abstract.verifiers) and
                not any(coordinator.id == actor_id for coordinator in abstract.coordinators)):
                error_msg = f"Authorization failed: You are not authorized to access abstract ID {abstract_id}"
                log_audit_event(
                    event_type="abstract_verifiers.list.failed",
                    user_id=actor_id,
                    details={
                        "error": error_msg, 
                        "abstract_id": abstract_id,
                        "user_id": actor_id,
                        "user_role": current_user.role_associations[0].role.value if current_user.role_associations else "no_role"
                    },
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 403

        # Get all verifiers associated with this abstract
        abstract_verifiers = AbstractVerifiers.query.filter_by(abstract_id=abstract_id).all()
        
        # Get the actual user details for each association
        verifiers_data = []
        for av in abstract_verifiers:
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
            event_type="abstract_verifiers.list.success",
            user_id=actor_id,
            details={
                "abstract_id": abstract_id,
                "verifiers_count": len(verifiers_data)
            },
            ip_address=request.remote_addr
        )

        return jsonify(verifiers_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving verifiers for abstract")
        error_msg = f"System error occurred while retrieving verifiers for abstract: {str(exc)}"
        log_audit_event(
            event_type="abstract_verifiers.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "abstract_id": abstract_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/verifiers/<user_id>/abstracts', methods=['GET'])
@jwt_required()
def get_abstracts_by_verifier(user_id):
    """Get all abstracts assigned to a specific verifier."""
    actor_id, context = _resolve_actor_context("get_abstracts_by_verifier")
    
    try:
        # First, verify that the user exists
        user = user_utils.get_user_by_id(user_id, actor_id=actor_id, context=context)
        if not user:
            error_msg = f"Resource not found: User with ID {user_id} does not exist"
            log_audit_event(
                event_type="verifier_abstracts.list.failed",
                user_id=actor_id,
                details={"error": error_msg, "user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if user is a verifier
        if not user.has_role(Role.VERIFIER.value):
            error_msg = f"Validation failed: User with ID {user_id} is not a verifier"
            log_audit_event(
                event_type="verifier_abstracts.list.failed",
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
                event_type="verifier_abstracts.list.failed",
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
            error_msg = f"Authorization failed: You are not authorized to access verifier ID {user_id}'s abstracts"
            log_audit_event(
                event_type="verifier_abstracts.list.failed",
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

        # Get all abstract-verifier associations for this user
        abstract_verifiers = AbstractVerifiers.query.filter_by(user_id=user_id).all()
        
        # Get the actual abstract details for each association
        abstracts_data = []
        for av in abstract_verifiers:
            abstract = abstract_utils.get_abstract_by_id(av.abstract_id, actor_id=actor_id, context=context)
            if abstract:
                abstracts_data.append({
                    'id': str(abstract.id),
                    'title': abstract.title,
                    'abstract_number': abstract.abstract_number,
                    'status': abstract.status.name,
                    'review_phase': abstract.review_phase  # Include review phase info
                })

        # Log successful retrieval
        log_audit_event(
            event_type="verifier_abstracts.list.success",
            user_id=actor_id,
            details={
                "user_id": user_id,
                "abstracts_count": len(abstracts_data)
            },
            ip_address=request.remote_addr
        )

        return jsonify(abstracts_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving abstracts for verifier")
        error_msg = f"System error occurred while retrieving abstracts for verifier: {str(exc)}"
        log_audit_event(
            event_type="verifier_abstracts.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 40