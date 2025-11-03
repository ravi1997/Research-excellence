from typing import Dict, Optional, Tuple
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models.Cycle import Abstracts, Author, AbstractAuthors
from app.models.Token import Token
from app.models.User import User
from app.models.enumerations import Role
from app.routes.v1.research import research_bp
from app.utils.decorator import require_roles
from app.utils.model_utils import abstract_utils, author_utils, audit_log_utils, token_utils


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


@research_bp.route('/abstract_authors', methods=['POST'])
@jwt_required()
def create_abstract_author():
    """Associate an author with an abstract."""
    actor_id, context = _resolve_actor_context("create_abstract_author")
    
    try:
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="abstract_author.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Validate required fields
        required_fields = ['abstract_id', 'author_id', 'author_order']
        for field in required_fields:
            if field not in payload:
                error_msg = f"Request validation failed: Missing required field '{field}'"
                log_audit_event(
                    event_type="abstract_author.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "missing_field": field},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 400

        # Validate abstract exists and user can access it
        abstract = abstract_utils.get_abstract_by_id(payload['abstract_id'], actor_id=actor_id, context=context)
        if not abstract:
            error_msg = f"Validation failed: Abstract with ID {payload['abstract_id']} does not exist"
            log_audit_event(
                event_type="abstract_author.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": payload['abstract_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Validate author exists
        author = author_utils.get_author_by_id(payload['author_id'], actor_id=actor_id, context=context)
        if not author:
            error_msg = f"Validation failed: Author with ID {payload['author_id']} does not exist"
            log_audit_event(
                event_type="abstract_author.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "author_id": payload['author_id']},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if the user can modify this abstract
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="abstract_author.create.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Only admin, superadmin, or the creator of the abstract can modify it
        if not (
                current_user.has_role(Role.ADMIN.value) or
                current_user.has_role(Role.SUPERADMIN.value) or
                abstract.created_by_id == actor_id
        ):
            error_msg = f"Authorization failed: You are not authorized to modify abstract ID {payload['abstract_id']}"
            log_audit_event(
                event_type="abstract_author.create.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "abstract_id": payload['abstract_id'],
                    "user_role": current_user.role_associations[0].role.value if current_user.role_associations else "no_role",
                    "abstract_creator_id": abstract.created_by_id
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 403

        # Check if association already exists
        existing_assoc = AbstractAuthors.query.filter_by(
            abstract_id=payload['abstract_id'],
            author_id=payload['author_id']
        ).first()
        if existing_assoc:
            error_msg = "Association already exists between this abstract and author"
            log_audit_event(
                event_type="abstract_author.create.failed",
                user_id=actor_id,
                details={
                    "error": error_msg,
                    "abstract_id": payload['abstract_id'],
                    "author_id": payload['author_id']
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 409

        # Create the association
        abstract_author = AbstractAuthors(
            abstract_id=payload['abstract_id'],
            author_id=payload['author_id'],
            author_order=payload['author_order']
        )
        db.session.add(abstract_author)
        db.session.commit()

        # Log successful creation
        log_audit_event(
            event_type="abstract_author.create.success",
            user_id=actor_id,
            details={
                "abstract_id": payload['abstract_id'],
                "author_id": payload['author_id'],
                "author_order": payload['author_order']
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            "message": "Author associated with abstract successfully",
            "abstract_id": payload['abstract_id'],
            "author_id": payload['author_id'],
            "author_order": payload['author_order']
        }), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creating abstract author association")
        error_msg = f"System error occurred while creating abstract author association: {str(exc)}"
        log_audit_event(
            event_type="abstract_author.create.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/abstract_authors/<abstract_id>/<author_id>', methods=['DELETE'])
@jwt_required()
def delete_abstract_author(abstract_id, author_id):
    """Remove an author from an abstract."""
    actor_id, context = _resolve_actor_context("delete_abstract_author")
    
    try:
        # Find the specific association
        abstract_author = AbstractAuthors.query.filter_by(
            abstract_id=abstract_id,
            author_id=author_id
        ).first()
        
        if not abstract_author:
            error_msg = f"Resource not found: Association between abstract ID {abstract_id} and author ID {author_id} does not exist"
            log_audit_event(
                event_type="abstract_author.delete.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": abstract_id, "author_id": author_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Get the abstract to check permissions
        abstract = abstract_utils.get_abstract_by_id(abstract_id, actor_id=actor_id, context=context)
        if not abstract:
            error_msg = f"Validation failed: Abstract with ID {abstract_id} does not exist"
            log_audit_event(
                event_type="abstract_author.delete.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": abstract_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if the user can modify this abstract
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="abstract_author.delete.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Only admin, superadmin, or the creator of the abstract can modify it
        if not (
                current_user.has_role(Role.ADMIN.value) or
                current_user.has_role(Role.SUPERADMIN.value) or
                abstract.created_by_id == actor_id
        ):
            error_msg = f"Authorization failed: You are not authorized to modify abstract ID {abstract_id}"
            log_audit_event(
                event_type="abstract_author.delete.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "abstract_id": abstract_id,
                    "user_role": current_user.role_associations[0].role.value if current_user.role_associations else "no_role",
                    "abstract_creator_id": abstract.created_by_id
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 403

        # Remove the association
        db.session.delete(abstract_author)
        db.session.commit()

        # Log successful deletion
        log_audit_event(
            event_type="abstract_author.delete.success",
            user_id=actor_id,
            details={
                "abstract_id": abstract_id,
                "author_id": author_id
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": "Author association removed from abstract successfully"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error deleting abstract author association")
        error_msg = f"System error occurred while deleting abstract author association: {str(exc)}"
        log_audit_event(
            event_type="abstract_author.delete.failed",
            user_id=actor_id,
            details={"error": error_msg, "abstract_id": abstract_id, "author_id": author_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/abstracts/<abstract_id>/authors', methods=['GET'])
@jwt_required()
def get_authors_by_abstract(abstract_id):
    """Get all authors associated with a specific abstract."""
    actor_id, context = _resolve_actor_context("get_authors_by_abstract")
    
    try:
        # First, verify that the abstract exists and user has permission to access it
        abstract = abstract_utils.get_abstract_by_id(abstract_id, actor_id=actor_id, context=context)
        if not abstract:
            error_msg = f"Resource not found: Abstract with ID {abstract_id} does not exist"
            log_audit_event(
                event_type="abstract_authors.list.failed",
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
                event_type="abstract_authors.list.failed",
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
                    event_type="abstract_authors.list.failed",
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

        # Get all authors associated with this abstract
        abstract_authors = AbstractAuthors.query.filter_by(abstract_id=abstract_id).order_by(AbstractAuthors.author_order).all()
        
        # Get the actual author details for each association
        authors_data = []
        for aa in abstract_authors:
            author = author_utils.get_author_by_id(aa.author_id, actor_id=actor_id, context=context)
            if author:
                authors_data.append({
                    'id': str(author.id),
                    'name': author.name,
                    'email': author.email,
                    'affiliation': author.affiliation,
                    'is_presenter': author.is_presenter,
                    'is_corresponding': author.is_corresponding,
                    'author_order': aa.author_order
                })

        # Log successful retrieval
        log_audit_event(
            event_type="abstract_authors.list.success",
            user_id=actor_id,
            details={
                "abstract_id": abstract_id,
                "authors_count": len(authors_data)
            },
            ip_address=request.remote_addr
        )

        return jsonify(authors_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving authors for abstract")
        error_msg = f"System error occurred while retrieving authors for abstract: {str(exc)}"
        log_audit_event(
            event_type="abstract_authors.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "abstract_id": abstract_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/authors/<author_id>/abstracts', methods=['GET'])
@jwt_required()
def get_abstracts_by_author(author_id):
    """Get all abstracts associated with a specific author."""
    actor_id, context = _resolve_actor_context("get_abstracts_by_author")
    
    try:
        # First, verify that the author exists
        author = author_utils.get_author_by_id(author_id, actor_id=actor_id, context=context)
        if not author:
            error_msg = f"Resource not found: Author with ID {author_id} does not exist"
            log_audit_event(
                event_type="author_abstracts.list.failed",
                user_id=actor_id,
                details={"error": error_msg, "author_id": author_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Get all abstract-author associations for this author
        abstract_authors = AbstractAuthors.query.filter_by(author_id=author_id).all()
        
        # Get the actual abstract details for each association
        abstracts_data = []
        for aa in abstract_authors:
            abstract = abstract_utils.get_abstract_by_id(aa.abstract_id, actor_id=actor_id, context=context)
            if abstract:
                # Check if user has permission to view this abstract
                current_user = User.query.get(actor_id)
                if not current_user:
                    continue  # Skip if user not found/authenticated

                # Check permissions - allow if:
                # 1. User is admin/superadmin
                # 2. User is the creator of the abstract
                # 3. User is a verifier for this abstract
                # 4. User is a coordinator for this abstract
                privileged = any(
                    current_user.has_role(role)
                    for role in (Role.ADMIN.value, Role.SUPERADMIN.value)
                )
                
                if privileged or (
                    abstract.created_by_id == actor_id or
                    any(verifier.id == actor_id for verifier in abstract.verifiers) or
                    any(coordinator.id == actor_id for coordinator in abstract.coordinators)
                ):
                    abstracts_data.append({
                        'id': str(abstract.id),
                        'title': abstract.title,
                        'abstract_number': abstract.abstract_number,
                        'status': abstract.status.name,
                        'author_order': aa.author_order
                    })

        # Log successful retrieval
        log_audit_event(
            event_type="author_abstracts.list.success",
            user_id=actor_id,
            details={
                "author_id": author_id,
                "abstracts_count": len(abstracts_data)
            },
            ip_address=request.remote_addr
        )

        return jsonify(abstracts_data), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving abstracts for author")
        error_msg = f"System error occurred while retrieving abstracts for author: {str(exc)}"
        log_audit_event(
            event_type="author_abstracts.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "author_id": author_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@research_bp.route('/abstract_authors/<abstract_id>/<author_id>', methods=['PUT'])
@jwt_required()
def update_abstract_author(abstract_id, author_id):
    """Update an author's position/order in an abstract."""
    actor_id, context = _resolve_actor_context("update_abstract_author")
    
    try:
        # Find the specific association
        abstract_author = AbstractAuthors.query.filter_by(
            abstract_id=abstract_id,
            author_id=author_id
        ).first()
        
        if not abstract_author:
            error_msg = f"Resource not found: Association between abstract ID {abstract_id} and author ID {author_id} does not exist"
            log_audit_event(
                event_type="abstract_author.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": abstract_id, "author_id": author_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Get the abstract to check permissions
        abstract = abstract_utils.get_abstract_by_id(abstract_id, actor_id=actor_id, context=context)
        if not abstract:
            error_msg = f"Validation failed: Abstract with ID {abstract_id} does not exist"
            log_audit_event(
                event_type="abstract_author.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": abstract_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Check if the user can modify this abstract
        current_user = User.query.get(actor_id)
        if not current_user:
            error_msg = "Authentication failed: User not found"
            log_audit_event(
                event_type="abstract_author.update.failed",
                user_id=actor_id,
                details={"error": error_msg},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Only admin, superadmin, or the creator of the abstract can modify it
        if not (
                current_user.has_role(Role.ADMIN.value) or
                current_user.has_role(Role.SUPERADMIN.value) or
                abstract.created_by_id == actor_id
        ):
            error_msg = f"Authorization failed: You are not authorized to modify abstract ID {abstract_id}"
            log_audit_event(
                event_type="abstract_author.update.failed",
                user_id=actor_id,
                details={
                    "error": error_msg, 
                    "abstract_id": abstract_id,
                    "user_role": current_user.role_associations[0].role.value if current_user.role_associations else "no_role",
                    "abstract_creator_id": abstract.created_by_id
                },
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 403

        # Get the updated order from the request
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            error_msg = "Request validation failed: Invalid payload provided"
            log_audit_event(
                event_type="abstract_author.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": abstract_id, "author_id": author_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        if 'author_order' not in payload:
            error_msg = "Request validation failed: Missing required field 'author_order'"
            log_audit_event(
                event_type="abstract_author.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "abstract_id": abstract_id, "author_id": author_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Update the author order
        abstract_author.author_order = payload['author_order']
        db.session.commit()

        # Log successful update
        log_audit_event(
            event_type="abstract_author.update.success",
            user_id=actor_id,
            details={
                "abstract_id": abstract_id,
                "author_id": author_id,
                "new_author_order": payload['author_order']
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            "message": "Author order updated successfully",
            "abstract_id": abstract_id,
            "author_id": author_id,
            "author_order": payload['author_order']
        }), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error updating abstract author association")
        error_msg = f"System error occurred while updating abstract author association: {str(exc)}"
        log_audit_event(
            event_type="abstract_author.update.failed",
            user_id=actor_id,
            details={"error": error_msg, "abstract_id": abstract_id, "author_id": author_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400