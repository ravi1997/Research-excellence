from typing import Dict, Optional, Tuple
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models.Token import Token
from app.models.User import User
from app.models.enumerations import Role

from app.schemas.token_schema import TokenSchema
from app.utils.decorator import require_roles
from app.utils.model_utils import token_utils, audit_log_utils


token_schema = TokenSchema()
tokens_schema = TokenSchema(many=True)


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
    from app.models.Token import Token as TokenModel

    actor_identity = get_jwt_identity()
    actor_id = str(actor_identity) if actor_identity is not None else None
    jwt_payload = get_jwt()
    token_jti: Optional[str] = jwt_payload.get("jti") if jwt_payload else None

    filters = [TokenModel.jti == token_jti] if token_jti else [TokenModel.id == 0]
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


# Create a Blueprint for token routes
from flask import Blueprint
token_bp = Blueprint('token_bp', __name__)


@token_bp.route('/tokens', methods=['GET'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def get_tokens():
    """Get all tokens with filtering support."""
    actor_id, context = _resolve_actor_context("get_tokens")
    
    try:
        # Get filters from query parameters
        user_id = request.args.get('user_id')
        revoked = request.args.get('revoked')
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(int(request.args.get('page_size', 20)), 100)

        filters = []
        if user_id:
            filters.append(Token.user_id == user_id)
        if revoked is not None:
            filters.append(Token.revoked == (revoked.lower() == 'true'))

        # Get tokens
        tokens = token_utils.list_tokens(
            filters=filters,
            actor_id=actor_id,
            context={**context, "filters_applied": bool(filters)}
        )

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = tokens[start:end]

        tokens_data = tokens_schema.dump(paginated)
        
        response = {
            'items': tokens_data,
            'total': len(tokens),
            'page': page,
            'pages': (len(tokens) + page_size - 1) // page_size,
            'page_size': page_size
        }

        # Log successful retrieval
        log_audit_event(
            event_type="token.list.success",
            user_id=actor_id,
            details={
                "filters_applied": bool(filters),
                "user_id_filter": user_id,
                "revoked_filter": revoked,
                "results_count": len(paginated),
                "total_count": len(tokens),
                "page": page,
                "page_size": page_size
            },
            ip_address=request.remote_addr
        )

        return jsonify(response), 200
    except Exception as exc:
        current_app.logger.exception("Error listing tokens")
        error_msg = f"System error occurred while retrieving tokens: {str(exc)}"
        log_audit_event(
            event_type="token.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@token_bp.route('/tokens/<jti>', methods=['GET'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def get_token(jti):
    """Get a specific token by JTI."""
    actor_id, context = _resolve_actor_context("get_token")
    
    try:
        token = token_utils.get_token_by_jti(jti, actor_id=actor_id, context=context)
        if not token:
            error_msg = f"Resource not found: Token with JTI {jti} does not exist"
            log_audit_event(
                event_type="token.get.failed",
                user_id=actor_id,
                details={"error": error_msg, "jti": jti},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Log successful retrieval
        log_audit_event(
            event_type="token.get.success",
            user_id=actor_id,
            details={
                "jti": jti,
                "user_id": token.user_id,
                "revoked": token.revoked
            },
            ip_address=request.remote_addr
        )

        return jsonify(token_schema.dump(token)), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving token")
        error_msg = f"System error occurred while retrieving token: {str(exc)}"
        log_audit_event(
            event_type="token.get.failed",
            user_id=actor_id,
            details={"error": error_msg, "jti": jti, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@token_bp.route('/tokens/<jti>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def revoke_token(jti):
    """Revoke a specific token."""
    actor_id, context = _resolve_actor_context("revoke_token")
    
    try:
        token = token_utils.get_token_by_jti(jti, actor_id=actor_id, context=context)
        if not token:
            error_msg = f"Resource not found: Token with JTI {jti} does not exist"
            log_audit_event(
                event_type="token.revoke.failed",
                user_id=actor_id,
                details={"error": error_msg, "jti": jti},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Update token to revoked state
        updated_token = token_utils.update_token(
            token,
            commit=True,
            actor_id=actor_id,
            context=context,
            revoked=True
        )

        # Log successful revocation
        log_audit_event(
            event_type="token.revoke.success",
            user_id=actor_id,
            details={
                "jti": jti,
                "user_id": updated_token.user_id,
                "revoked_by": actor_id
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": "Token revoked successfully"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error revoking token")
        error_msg = f"System error occurred while revoking token: {str(exc)}"
        log_audit_event(
            event_type="token.revoke.failed",
            user_id=actor_id,
            details={"error": error_msg, "jti": jti, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@token_bp.route('/tokens/user/<user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def revoke_all_tokens_for_user(user_id):
    """Revoke all tokens for a specific user."""
    actor_id, context = _resolve_actor_context("revoke_all_tokens_for_user")
    
    try:
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            error_msg = f"Validation failed: User with ID {user_id} does not exist"
            log_audit_event(
                event_type="token.bulk_revoke.failed",
                user_id=actor_id,
                details={"error": error_msg, "target_user_id": user_id},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 404

        # Get all tokens for the user
        user_tokens = token_utils.list_tokens(
            filters=[Token.user_id == user_id],
            actor_id=actor_id,
            context={**context, "operation": "bulk_revoke"}
        )

        # Revoke all tokens
        revoked_count = 0
        for token in user_tokens:
            if not token.revoked:  # Only revoke if not already revoked
                token_utils.update_token(
                    token,
                    commit=False,  # Don't commit yet, we'll commit at the end
                    actor_id=actor_id,
                    context={**context, "operation": "bulk_revoke"},
                    revoked=True
                )
                revoked_count += 1

        # Commit all changes
        db.session.commit()

        # Log successful bulk revocation
        log_audit_event(
            event_type="token.bulk_revoke.success",
            user_id=actor_id,
            details={
                "target_user_id": user_id,
                "tokens_revoked": revoked_count,
                "total_tokens_for_user": len(user_tokens)
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": f"Successfully revoked {revoked_count} tokens for user {user_id}"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error revoking all tokens for user")
        error_msg = f"System error occurred while revoking tokens for user: {str(exc)}"
        log_audit_event(
            event_type="token.bulk_revoke.failed",
            user_id=actor_id,
            details={"error": error_msg, "target_user_id": user_id, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400


@token_bp.route('/tokens/cleanup', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def cleanup_expired_tokens():
    """Remove expired tokens from the database."""
    actor_id, context = _resolve_actor_context("cleanup_expired_tokens")
    
    try:
        from datetime import datetime
        current_time = datetime.utcnow()
        
        # Find expired tokens (not revoked but expired based on exp claim)
        expired_tokens = Token.query.filter(
            Token.revoked == False,
            Token.expires_at < current_time
        ).all()

        deleted_count = 0
        for token in expired_tokens:
            db.session.delete(token)
            deleted_count += 1

        db.session.commit()

        # Log successful cleanup
        log_audit_event(
            event_type="token.cleanup.success",
            user_id=actor_id,
            details={
                "expired_tokens_removed": deleted_count,
                "cleanup_time": str(current_time)
            },
            ip_address=request.remote_addr
        )

        return jsonify({"message": f"Successfully removed {deleted_count} expired tokens"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error cleaning up expired tokens")
        error_msg = f"System error occurred during token cleanup: {str(exc)}"
        log_audit_event(
            event_type="token.cleanup.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(exc).__name__, "exception_message": str(exc)},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400