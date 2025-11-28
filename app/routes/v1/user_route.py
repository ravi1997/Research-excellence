# routes/user_routes.py

from app.models.Cycle import AwardVerifiers, BestPaperVerifiers
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
import traceback
from app.schemas.user_schema import UserSchema
from app.schemas.user_settings_schema import UserSettingsSchema
from app.utils.decorator import require_roles
from app.models.User import User, UserSettings, UserType, Role, MAX_OTP_RESENDS, PASSWORD_EXPIRATION_DAYS
from app.security_utils import rate_limit, ip_and_path_key, audit_log, coerce_uuid
from app.utils import metrics_cache
from app.utils.model_utils.user_utils import (
    create_user,
    get_user_by_id,
    list_users,
    update_user,
    delete_user,
    set_user_roles,
    activate_user,
    deactivate_user,
    create_user_settings,
    get_user_settings_by_id,
    get_user_settings_by_user_id,
    update_user_settings,
    create_user_role,
    get_user_roles_by_user_id
)
from app.utils.model_utils.base import _serialize_value
from app.utils.logging_utils import get_logger, log_context
from datetime import datetime, timedelta, timezone
from app.extensions import db
user_bp = Blueprint("user_bp", __name__)

# ─── Auth Endpoints ─────────────────────────────────────


@user_bp.route("/change-password", methods=["POST","PUT"])
@jwt_required()
@rate_limit(ip_and_path_key, limit=5, window_sec=900)
def change_password():
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="change_password", actor_id=actor_id):
            logger.info("Change password request initiated by user_id=%s", _serialize_value(actor_id))
            
            data = request.json or {}
            uid = coerce_uuid(actor_id)
            
            # Use utility function to get user with audit trail
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "change_password"})
            if not user:
                audit_log('password_change_failed', user_id=actor_id, detail='user_not_found')
                logger.warning("Change password failed - user not found id=%s", _serialize_value(uid))
                return jsonify({"message": "User not found"}), 404
            
            if not user.check_password(data.get("current_password", "")):
                audit_log('password_change_failed', user_id=user.id, detail='bad_current_password')
                logger.warning("Change password failed - incorrect current password for user_id=%s", _serialize_value(user.id))
                return jsonify({"message": "Current password incorrect"}), 400
            
            try:
                user.set_password(data.get("new_password"))
            except ValueError as ve:
                audit_log('password_change_failed', user_id=user.id, detail=str(ve))
                logger.warning("Change password failed - validation error user_id=%s error=%s", _serialize_value(user.id), str(ve))
                return jsonify({"message": str(ve)}), 400
            
            user.require_password_change = False
            db.session.commit()
            audit_log('password_changed', user_id=user.id)
            logger.info("Password successfully changed for user_id=%s", _serialize_value(user.id))
            return jsonify({"message": "Password changed"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during password change user_id=%s error=%s", _serialize_value(actor_id), str(e))
        audit_log('password_change_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during password change user_id=%s error=%s traceback=%s", _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('password_change_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500



@user_bp.route("/reset-password", methods=["POST"])
def reset_password():
    logger = get_logger("user_routes")
    try:
        with log_context(module="user_routes", action="reset_password", actor_id=None):
            logger.info("Password reset request initiated")
            
            data = request.json or {}
            user = None
            actor_id = None # No authenticated user for this endpoint
            
            # OTP flow by mobile
            if data.get("otp") and data.get("mobile"):
                user = User.query.filter_by(mobile=data.get("mobile")).first()
                if not user or not user.verify_otp(data["otp"]):
                    audit_log('password_reset_failed', user_id=actor_id, detail='invalid_otp')
                    logger.warning("Password reset failed - invalid OTP for mobile=%s", data.get("mobile"))
                    return jsonify({"message": "Invalid OTP"}), 400
                actor_id = user.id
            # Direct by user_id (admin tool or verified flow)
            elif data.get("user_id"):
                try:
                    uid = coerce_uuid(data.get("user_id"))
                except Exception:
                    uid = data.get("user_id")
                user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "password_reset"})
                actor_id = uid

            if not user:
                audit_log('password_reset_failed', user_id=actor_id, detail='user_not_found')
                logger.warning("Password reset failed - user not found")
                return jsonify({"message": "User not found"}), 404

            try:
                user.set_password(data.get("new_password"))
                db.session.commit()
                audit_log('password_reset', user_id=user.id)
                logger.info("Password successfully reset for user_id=%s", _serialize_value(user.id))
                return jsonify({"message": "Password reset"}), 200
            except ValueError as ve:
                db.session.rollback()
                audit_log('password_reset_failed', user_id=user.id, detail=str(ve))
                logger.warning("Password reset failed - validation error user_id=%s error=%s", _serialize_value(user.id), str(ve))
                return jsonify({"message": str(ve)}), 400
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error("Database error during password reset user_id=%s error=%s", _serialize_value(user.id), str(e))
                audit_log('password_reset_failed', user_id=user.id, detail=f'database_error: {str(e)}')
                return jsonify({"message": "Database error occurred"}), 500
            except Exception as e:
                db.session.rollback()
                logger.error("Unexpected error during password reset user_id=%s error=%s traceback=%s", _serialize_value(user.id), str(e), traceback.format_exc())
                audit_log('password_reset_failed', user_id=user.id, detail=f'internal_error: {str(e)}')
                return jsonify({"message": "Internal server error"}), 500
    except Exception as e:
        logger.error("Unexpected error in reset_password endpoint error=%s traceback=%s", str(e), traceback.format_exc())
        return jsonify({"message": "Internal server error"}), 500

@user_bp.route("/unlock", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def auth_unlock():
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="auth_unlock", actor_id=actor_id):
            logger.info("Auth unlock request initiated by user_id=%s", _serialize_value(actor_id))
            
            data = request.json or {}
            uid = coerce_uuid(data.get("user_id")) if data.get("user_id") else None
            if not uid:
                audit_log('unlock_failed', user_id=actor_id, detail='user_id_required')
                logger.warning("Unlock failed - user_id required, actor_id=%s", _serialize_value(actor_id))
                return jsonify({"message": "user_id required"}), 400
            
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "auth_unlock"})
            if not user:
                audit_log('unlock_failed', user_id=actor_id, detail='target_user_not_found')
                logger.warning("Unlock failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            try:
                user.unlock_account()
                db.session.commit()
                audit_log('user_unlocked', user_id=user.id, target_user_id=user.id)
                logger.info("User successfully unlocked user_id=%s by actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
                return jsonify({"message": f"User {user.id} unlocked"}), 200
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error("Database error during unlock user_id=%s actor_id=%s error=%s", _serialize_value(user.id), _serialize_value(actor_id), str(e))
                audit_log('unlock_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
                return jsonify({"message": "Database error occurred"}), 500
            except Exception as e:
                db.session.rollback()
                logger.error("Unexpected error during unlock user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(user.id), _serialize_value(actor_id), str(e), traceback.format_exc())
                audit_log('unlock_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
                return jsonify({"message": "Internal server error"}), 500
    except Exception as e:
        logger.error("Unexpected error in auth_unlock endpoint actor_id=%s error=%s traceback=%s", _serialize_value(actor_id), str(e), traceback.format_exc())
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/status", methods=["GET"])
@jwt_required()
def auth_status():
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="auth_status", actor_id=actor_id):
            logger.info("Auth status request initiated by user_id=%s", _serialize_value(actor_id))
            
            uid = coerce_uuid(actor_id)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "auth_status"})
            if not user:
                audit_log('auth_status_failed', user_id=actor_id, detail='user_not_found')
                logger.warning("Auth status failed - user not found user_id=%s", _serialize_value(uid))
                return jsonify({"message": "User not found"}), 404
            
            user_data = UserSchema().dump(user)
            audit_log('auth_status', user_id=actor_id)
            logger.info("Auth status retrieved successfully for user_id=%s", _serialize_value(user.id))
            return jsonify({"user": user_data}), 200
    except SQLAlchemyError as e:
        logger.error("Database error during auth status check user_id=%s error=%s", _serialize_value(actor_id), str(e))
        audit_log('auth_status_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        logger.error("Unexpected error during auth status check user_id=%s error=%s traceback=%s", _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('auth_status_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500

# ─── CRUD Endpoints ─────────────────────────────────────


@user_bp.route("/users", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def list_users_route():
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="list_users", actor_id=actor_id):
            logger.info("List users request initiated by user_id=%s", _serialize_value(actor_id))
            
            users = list_users(actor_id=actor_id, context={"operation": "list_users"}, order_by=User.created_at.asc())
            users_data = [u.to_dict() for u in users]
            audit_log('user_list', user_id=actor_id, detail=f'count={len(users)}')
            logger.info("Users listed successfully, count=%s, actor_id=%s", len(users), _serialize_value(actor_id))
            return jsonify(users_data), 200
    except SQLAlchemyError as e:
        logger.error("Database error during list users actor_id=%s error=%s", _serialize_value(actor_id), str(e))
        audit_log('user_list_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        logger.error("Unexpected error during list users actor_id=%s error=%s traceback=%s", _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_list_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/users/<user_id>", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def get_user_route(user_id):
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="get_user", actor_id=actor_id):
            logger.info("Get user request initiated by user_id=%s for target_user_id=%s", _serialize_value(actor_id), _serialize_value(user_id))
            
            uid = coerce_uuid(user_id)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "get_user"})
            if not user:
                audit_log('user_get_failed', user_id=actor_id, detail=f'target_user_not_found: {uid}')
                logger.warning("Get user failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            user_data = user.to_dict()
            audit_log('user_get', user_id=actor_id, target_user_id=uid)
            logger.info("User retrieved successfully user_id=%s by actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
            return jsonify(user_data), 200
    except SQLAlchemyError as e:
        logger.error("Database error during get user user_id=%s actor_id=%s error=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e))
        audit_log('user_get_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        logger.error("Unexpected error during get user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_get_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/users", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_user_route():
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="create_user", actor_id=actor_id):
            logger.info("Create user request initiated by user_id=%s", _serialize_value(actor_id))
            
            data = request.get_json(force=True, silent=True) or {}
            password = data.pop("password", None)
            
            user = create_user(actor_id=actor_id, context={"operation": "create_user"}, **data)
            if password:
                user.set_password(password)
            
            # Commit after setting password
            db.session.commit()
            
            try:
                metrics_cache.invalidate()
            except Exception:
                pass
            
            audit_log('user_create', user_id=actor_id, target_user_id=user.id)
            logger.info("User created successfully user_id=%s by actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
            return jsonify(user.to_dict()), 201
    except ValueError as ve:
        db.session.rollback()
        audit_log('user_create_failed', user_id=actor_id, detail=str(ve))
        logger.warning("Create user failed - validation error user_id=%s error=%s", _serialize_value(actor_id), str(ve))
        return jsonify({"message": str(ve)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during create user actor_id=%s error=%s", _serialize_value(actor_id), str(e))
        audit_log('user_create_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during create user actor_id=%s error=%s traceback=%s", _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_create_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/users/<user_id>", methods=["PUT"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_user_route(user_id):
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="update_user", actor_id=actor_id):
            logger.info("Update user request initiated by user_id=%s for target_user_id=%s", _serialize_value(actor_id), _serialize_value(user_id))
            
            uid = coerce_uuid(user_id)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "update_user"})
            if not user:
                audit_log('user_update_failed', user_id=actor_id, detail=f'target_user_not_found: {uid}')
                logger.warning("Update user failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            data = request.json or {}
            # Guard: prevent removal of SUPERADMIN role from last superadmin via role updates (if roles list provided)
            roles_payload = data.get('roles') if isinstance(data, dict) else None
            if roles_payload is not None:
                # Determine if user currently has SUPERADMIN
                has_super = any(r.role == Role.SUPERADMIN for r in user.role_associations)
                if has_super and Role.SUPERADMIN.value not in roles_payload:
                    # Count other superadmins
                    from app.models.User import UserRole as UR
                    others = User.query.join(UR).filter(UR.role == Role.SUPERADMIN, User.id != user.id).count()
                    if others == 0:
                        audit_log('superadmin_demote_blocked', user_id=actor_id, target_user_id=user_id, detail='Attempt to remove last superadmin role blocked')
                        logger.warning("Update user failed - attempt to remove last superadmin role user_id=%s actor_id=%s", _serialize_value(user_id), _serialize_value(actor_id))
                        return jsonify({"message": "Cannot remove last superadmin role"}), 403
            
            # Prepare update data, excluding sensitive fields
            update_data = {}
            for k, v in (data or {}).items():
                if k == 'password_hash':
                    continue
                if hasattr(user, k):
                    update_data[k] = v
            
            updated_user = update_user(user, actor_id=actor_id, context={"operation": "update_user"}, **update_data)
            
            try:
                metrics_cache.invalidate()
            except Exception:
                pass
            
            audit_log('user_update', user_id=actor_id, target_user_id=user_id)
            logger.info("User updated successfully user_id=%s by actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
            return jsonify(updated_user.to_dict()), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during update user user_id=%s actor_id=%s error=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e))
        audit_log('user_update_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during update user user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_update_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/users/<user_id>", methods=["DELETE"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_user_route(user_id):
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="delete_user", actor_id=actor_id):
            logger.info("Delete user request initiated by user_id=%s for target_user_id=%s", _serialize_value(actor_id), _serialize_value(user_id))
            
            uid = coerce_uuid(user_id)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "delete_user"})
            if not user:
                audit_log('user_delete_failed', user_id=actor_id, detail=f'target_user_not_found: {uid}')
                logger.warning("Delete user failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            # Prevent deletion of superadmin accounts
            if any(r.role == Role.SUPERADMIN for r in user.role_associations):
                audit_log('superadmin_delete_blocked', user_id=actor_id, target_user_id=user_id, detail='Attempt to delete superadmin blocked')
                logger.warning("Delete user failed - attempt to delete superadmin user_id=%s actor_id=%s", _serialize_value(user_id), _serialize_value(actor_id))
                return jsonify({"message": "Cannot delete superadmin"}), 403
            
            delete_user(user, actor_id=actor_id, context={"operation": "delete_user"})
            
            try:
                metrics_cache.invalidate()
            except Exception:
                pass
            
            audit_log('user_delete', user_id=actor_id, target_user_id=user_id)
            logger.info("User deleted successfully user_id=%s by actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
            return jsonify({"message": "User deleted"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during delete user user_id=%s actor_id=%s error=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e))
        audit_log('user_delete_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during delete user user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_delete_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/verifiers", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def list_verifiers():
    """Get all users with verifier role."""
    current_app.logger.info("Listing all verifiers")
    verifiers = User.query.join(User.role_associations).filter_by(role=Role.VERIFIER).all()
    return jsonify([user.to_dict() for user in verifiers]), 200


@user_bp.route("/users/verifiers", methods=["GET"])
@jwt_required()
@require_roles(Role.COORDINATOR.value,Role.ADMIN.value, Role.SUPERADMIN.value)
def list_verifiers_with_params():
    """Get all users with verifier role with filtering and pagination support."""
    try:
        # Get query parameters
        q = request.args.get('q', '').strip()
        has_abstracts = request.args.get('has_abstracts', '').strip()
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        sort_by = request.args.get('sort_by', 'created_at')
        sort_dir = request.args.get('sort_dir', 'desc')
        
        # Validate page size
        page_size = min(page_size, 100)  # Limit max page size
        page = max(1, page)  # Ensure page is at least 1
        
        # Build query for verifiers
        query = User.query.join(User.role_associations).filter_by(role=Role.VERIFIER)
        
        # Apply search filter
        if q:
            search_filter = db.or_(
                User.username.ilike(f'%{q}%'),
                User.email.ilike(f'%{q}%'),
                User.employee_id.ilike(f'%{q}%'),
                User.mobile.ilike(f'%{q}%')
            )
            query = query.filter(search_filter)
        
        # Apply has_abstracts filter
        if has_abstracts:
            # Import here to avoid circular imports
            from app.models.Cycle import AbstractVerifiers
            
            if has_abstracts.lower() == 'yes':
                # Only verifiers with assigned abstracts
                query = query.join(AbstractVerifiers, User.id == AbstractVerifiers.user_id)
            elif has_abstracts.lower() == 'no':
                # Only verifiers without assigned abstracts
                query = query.outerjoin(AbstractVerifiers, User.id == AbstractVerifiers.user_id).filter(AbstractVerifiers.user_id.is_(None))
        
        # Apply sorting
        if sort_by == 'username':
            order_by = User.username.asc() if sort_dir.lower() == 'asc' else User.username.desc()
        elif sort_by == 'email':
            order_by = User.email.asc() if sort_dir.lower() == 'asc' else User.email.desc()
        else:  # default to created_at
            order_by = User.created_at.asc() if sort_dir.lower() == 'asc' else User.created_at.desc()
        
        query = query.order_by(order_by)
        
        # Apply pagination
        total = query.count()
        verifiers = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # Add abstracts count to each verifier
        verifiers_data = []
        for verifier in verifiers:
            verifier_dict = verifier.to_dict()
            # Count abstracts assigned to this verifier
            from app.models.Cycle import AbstractVerifiers
            abstracts_count = db.session.query(
                AbstractVerifiers).filter_by(user_id=verifier.id).count()
            awards_count = db.session.query(
                AwardVerifiers).filter_by(user_id=verifier.id).count()
            best_papers_count = db.session.query(
                BestPaperVerifiers).filter_by(user_id=verifier.id).count()
            verifier_dict['abstracts_count'] = abstracts_count
            verifier_dict['awards_count'] = awards_count
            verifier_dict['bestpapers_count'] = best_papers_count
            verifiers_data.append(verifier_dict)
        
        # Prepare response
        response = {
            'items': verifiers_data,
            'total': total,
            'page': page,
            'pages': (total + page_size - 1) // page_size,
            'page_size': page_size
        }
        
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.exception("Error listing verifiers with parameters")
        return jsonify({"error": str(e)}), 400




@user_bp.route("/verifiers/<user_id>/abstracts", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value, Role.VERIFIER.value)
def get_verifier_abstracts(user_id):
    """Get all abstracts assigned to a verifier."""
    try:
        # Check if user exists and is a verifier
        user = User.query.get_or_404(user_id)
        if not user.has_role(Role.VERIFIER.value):
            return jsonify({"error": "User is not a verifier"}), 400
        
        # Import here to avoid circular imports
        from app.models.Cycle import Abstracts, AbstractVerifiers
        
        # Get all abstracts assigned to this verifier
        abstracts = db.session.query(Abstracts).join(
            AbstractVerifiers, Abstracts.id == AbstractVerifiers.abstract_id
        ).filter(
            AbstractVerifiers.user_id == user_id
        ).all()
        
        # Convert to dict format
        abstracts_data = []
        for abstract in abstracts:
            abstract_dict = {
                'id': str(abstract.id),
                'title': abstract.title,
                'content': abstract.content,
                'category_id': str(abstract.category_id) if abstract.category_id else None,
                'cycle_id': str(abstract.cycle_id) if abstract.cycle_id else None,
                'created_at': abstract.created_at.isoformat() if abstract.created_at else None,
                'updated_at': abstract.updated_at.isoformat() if abstract.updated_at else None,
                'status': abstract.status.value if abstract.status else None,
                'created_by': str(abstract.created_by) if abstract.created_by else None
            }
            abstracts_data.append(abstract_dict)
        
        return jsonify(abstracts_data), 200
    except Exception as e:
        current_app.logger.exception("Error getting abstracts for verifier")
        return jsonify({"error": str(e)}), 400


@user_bp.route("/abstracts/<abstract_id>/verifiers", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value, Role.VERIFIER.value)
def get_abstract_verifiers(abstract_id):
    """Get all verifiers assigned to an abstract."""
    try:
        # Import here to avoid circular imports
        from app.models.Cycle import Abstracts, AbstractVerifiers
        
        # Check if abstract exists
        abstract = Abstracts.query.get_or_404(abstract_id)
        
        # Get all verifiers for this abstract
        verifiers = db.session.query(User).join(
            AbstractVerifiers, User.id == AbstractVerifiers.user_id
        ).filter(
            AbstractVerifiers.abstract_id == abstract_id
        ).all()
        
        # Convert to dict format
        verifiers_data = []
        for verifier in verifiers:
            verifier_dict = {
                'id': str(verifier.id),
                'username': verifier.username,
                'email': verifier.email,
                'employee_id': verifier.employee_id
            }
            verifiers_data.append(verifier_dict)
        
        return jsonify(verifiers_data), 200
    except Exception as e:
        current_app.logger.exception("Error getting verifiers for abstract")
        return jsonify({"error": str(e)}), 400


@user_bp.route("/user/verifiers", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def list_user_verifiers():
    """Get all users with verifier role - alternate endpoint for compatibility."""
    try:
        # Get query parameters
        q = request.args.get('q', '').strip()
        has_abstracts = request.args.get('has_abstracts', '').strip()
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        sort_by = request.args.get('sort_by', 'created_at')
        sort_dir = request.args.get('sort_dir', 'desc')
        
        # Validate page size
        page_size = min(page_size, 100)  # Limit max page size
        page = max(1, page)  # Ensure page is at least 1
        
        # Build query for verifiers
        query = User.query.join(User.role_associations).filter_by(role=Role.VERIFIER)
        
        # Apply search filter
        if q:
            search_filter = db.or_(
                User.username.ilike(f'%{q}%'),
                User.email.ilike(f'%{q}%'),
                User.employee_id.ilike(f'%{q}%')
            )
            query = query.filter(search_filter)
        
        # Apply has_abstracts filter
        if has_abstracts:
            # Import here to avoid circular imports
            from app.models.Cycle import AbstractVerifiers
            
            if has_abstracts.lower() == 'yes':
                # Only verifiers with assigned abstracts
                query = query.join(AbstractVerifiers, User.id == AbstractVerifiers.user_id)
            elif has_abstracts.lower() == 'no':
                # Only verifiers without assigned abstracts
                query = query.outerjoin(AbstractVerifiers, User.id == AbstractVerifiers.user_id).filter(AbstractVerifiers.user_id.is_(None))
        
        # Apply sorting
        if sort_by == 'username':
            order_by = User.username.asc() if sort_dir.lower() == 'asc' else User.username.desc()
        elif sort_by == 'email':
            order_by = User.email.asc() if sort_dir.lower() == 'asc' else User.email.desc()
        else:  # default to created_at
            order_by = User.created_at.asc() if sort_dir.lower() == 'asc' else User.created_at.desc()
        
        query = query.order_by(order_by)
        
        # Apply pagination
        total = query.count()
        verifiers = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # Add abstracts count to each verifier
        verifiers_data = []
        for verifier in verifiers:
            verifier_dict = verifier.to_dict()
            # Count abstracts assigned to this verifier
            from app.models.Cycle import AbstractVerifiers
            abstracts_count = db.session.query(AbstractVerifiers).filter_by(user_id=verifier.id).count()
            verifier_dict['abstracts_count'] = abstracts_count
            verifiers_data.append(verifier_dict)
        
        # Prepare response
        response = {
            'items': verifiers_data,
            'total': total,
            'page': page,
            'pages': (total + page_size - 1) // page_size,
            'page_size': page_size
        }
        
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.exception("Error listing verifiers with parameters")
        return jsonify({"error": str(e)}), 400


@user_bp.route("/users/<user_id>/lock", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def lock_user_route(user_id):
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="lock_user", actor_id=actor_id):
            logger.info("Lock user request initiated by user_id=%s for target_user_id=%s", _serialize_value(actor_id), _serialize_value(user_id))
            
            uid = coerce_uuid(user_id)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "lock_user"})
            if not user:
                audit_log('user_lock_failed', user_id=actor_id, detail=f'target_user_not_found: {uid}')
                logger.warning("Lock user failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            user.lock_account()
            db.session.commit()
            
            try:
                metrics_cache.invalidate()
            except Exception:
                pass
            
            audit_log('user_lock', user_id=actor_id, target_user_id=user_id)
            logger.info("User locked successfully user_id=%s by actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
            return jsonify({"message": f"User {user.id} locked"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during lock user user_id=%s actor_id=%s error=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e))
        audit_log('user_lock_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during lock user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_lock_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/users/<user_id>/unlock", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def unlock_user_route(user_id):
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="unlock_user", actor_id=actor_id):
            logger.info("Unlock user request initiated by user_id=%s for target_user_id=%s", _serialize_value(actor_id), _serialize_value(user_id))
            
            uid = coerce_uuid(user_id)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "unlock_user"})
            if not user:
                audit_log('user_unlock_failed', user_id=actor_id, detail=f'target_user_not_found: {uid}')
                logger.warning("Unlock user failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            user.unlock_account()
            db.session.commit()
            
            try:
                metrics_cache.invalidate()
            except Exception:
                pass
            
            audit_log('user_unlock', user_id=actor_id, target_user_id=user_id)
            logger.info("User unlocked successfully user_id=%s by actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
            return jsonify({"message": f"User {user.id} unlocked"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during unlock user user_id=%s actor_id=%s error=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e))
        audit_log('user_unlock_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during unlock user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_unlock_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/users/<user_id>/reset-otp-count", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def reset_otp_count_route(user_id):
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="reset_otp_count", actor_id=actor_id):
            logger.info("Reset OTP count request initiated by user_id=%s for target_user_id=%s", _serialize_value(actor_id), _serialize_value(user_id))
            
            uid = coerce_uuid(user_id)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "reset_otp_count"})
            if not user:
                audit_log('user_reset_otp_count_failed', user_id=actor_id, detail=f'target_user_not_found: {uid}')
                logger.warning("Reset OTP count failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            user.otp_resend_count = 0
            db.session.commit()
            
            audit_log('user_reset_otp_count', user_id=actor_id, target_user_id=user_id)
            logger.info("OTP count reset successfully for user_id=%s by actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
            return jsonify({"message": f"OTP count reset for {user.id}"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during reset OTP count user_id=%s actor_id=%s error=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e))
        audit_log('user_reset_otp_count_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during reset OTP count user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_reset_otp_count_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500

# ─── Security Endpoints ─────────────────────────────────


@user_bp.route("/security/extend-password-expiry", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def extend_password_expiry_route():
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="extend_password_expiry", actor_id=actor_id):
            logger.info("Extend password expiry request initiated by user_id=%s", _serialize_value(actor_id))
            
            data = request.json or {}
            uid = data.get("user_id")
            days = data.get("days", PASSWORD_EXPIRATION_DAYS)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "extend_password_expiry"})
            if not user:
                audit_log('password_expiry_extend_failed', user_id=actor_id, detail=f'target_user_not_found: {uid}')
                logger.warning("Extend password expiry failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            user.password_expiration = datetime.now(timezone.utc) + timedelta(days=days)
            db.session.commit()
            
            audit_log('password_expiry_extended', user_id=actor_id, target_user_id=uid, detail=f'days={days}')
            logger.info("Password expiry extended successfully for user_id=%s by actor_id=%s, days=%s", _serialize_value(user.id), _serialize_value(actor_id), days)
            return jsonify({"message": "Password expiry extended"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during extend password expiry user_id=%s actor_id=%s error=%s", _serialize_value(actor_id), _serialize_value(actor_id), str(e))
        audit_log('password_expiry_extend_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during extend password expiry user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(actor_id), _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('password_expiry_extend_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/security/lock-status/<user_id>", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def lock_status_route(user_id):
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="lock_status", actor_id=actor_id):
            logger.info("Lock status request initiated by user_id=%s for target_user_id=%s", _serialize_value(actor_id), _serialize_value(user_id))
            
            uid = coerce_uuid(user_id)
            user = get_user_by_id(uid, actor_id=actor_id, context={"operation": "lock_status"})
            if not user:
                audit_log('user_lock_status_failed', user_id=actor_id, detail=f'target_user_not_found: {uid}')
                logger.warning("Lock status failed - target user not found user_id=%s actor_id=%s", _serialize_value(uid), _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            locked_status = user.is_locked()
            audit_log('user_lock_status', user_id=actor_id, target_user_id=user_id, detail=f'locked={locked_status}')
            logger.info("Lock status retrieved successfully for user_id=%s by actor_id=%s, locked=%s", _serialize_value(user.id), _serialize_value(actor_id), locked_status)
            return jsonify({"locked": locked_status}), 200
    except SQLAlchemyError as e:
        logger.error("Database error during lock status check user_id=%s actor_id=%s error=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e))
        audit_log('user_lock_status_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        logger.error("Unexpected error during lock status check user_id=%s actor_id=%s error=%s traceback=%s", _serialize_value(user_id), _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('user_lock_status_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.route("/security/resend-otp", methods=["POST"])
@rate_limit(ip_and_path_key, limit=5, window_sec=600)
def resend_otp_route():
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()  # May be None if not authenticated
    try:
        with log_context(module="user_routes", action="resend_otp", actor_id=actor_id):
            logger.info("Resend OTP request initiated by user_id=%s", _serialize_value(actor_id))
            
            data = request.get_json(force=True, silent=True) or {}
            mobile = data.get("mobile")
            user = User.query.filter_by(mobile=mobile).first()
            if not user:
                audit_log('resend_otp_failed', user_id=actor_id, detail=f'user_not_found: {mobile}')
                logger.warning("Resend OTP failed - user not found mobile=%s actor_id=%s", mobile, _serialize_value(actor_id))
                return jsonify({"message": "User not found"}), 404
            
            if user.is_locked():
                audit_log('resend_otp_failed', user_id=actor_id, detail=f'account_locked: {user.id}')
                logger.warning("Resend OTP failed - account locked user_id=%s actor_id=%s", _serialize_value(user.id), _serialize_value(actor_id))
                return jsonify({"message": "Account locked"}), 403
            
            user.resend_otp()
            db.session.commit()
            
            payload = {"message": "OTP resent"}
            if current_app.config.get("DEBUG"):
                payload["otp"] = user.otp
            
            audit_log('resend_otp_success', user_id=actor_id, target_user_id=user.id, detail=f'mobile: {mobile}')
            logger.info("OTP resent successfully for user_id=%s mobile=%s by actor_id=%s", _serialize_value(user.id), mobile, _serialize_value(actor_id))
            return jsonify(payload), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during resend OTP mobile=%s actor_id=%s error=%s", mobile, _serialize_value(actor_id), str(e))
        audit_log('resend_otp_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error during resend OTP mobile=%s actor_id=%s error=%s traceback=%s", mobile, _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('resend_otp_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


DEFAULTS = {
    "theme": "system",
    "compact": False,
    "autoplay": False,
    "quality": "auto",
    "speed": "1.0",
    "email_updates": False,
    "weekly_digest": False,
    "private_profile": False,
    "personalize": True,
}


def _get_or_create_user_settings(user_id: int) -> UserSettings:
    logger = get_logger("user_routes")
    try:
        with log_context(module="user_routes", action="_get_or_create_user_settings", actor_id=user_id):
            logger.info("_get_or_create_user_settings called for user_id=%s", _serialize_value(user_id))
            inst = db.session.get(UserSettings, user_id)
            if inst is None:
                logger.info("Creating default settings for user_id=%s", _serialize_value(user_id))
                inst = UserSettings(user_id=user_id, **DEFAULTS)
                db.session.add(inst)
                db.session.commit()
                logger.info("Default settings created for user_id=%s", _serialize_value(user_id))
            else:
                logger.info("Existing settings found for user_id=%s", _serialize_value(user_id))
            return inst
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error in _get_or_create_user_settings user_id=%s error=%s", _serialize_value(user_id), str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error in _get_or_create_user_settings user_id=%s error=%s traceback=%s", _serialize_value(user_id), str(e), traceback.format_exc())
        raise


@user_bp.get("/settings")
@jwt_required()
def get_settings_route():
    """Return current user's settings, creating defaults if missing."""
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="get_settings", actor_id=actor_id):
            logger.info("Get settings request initiated by user_id=%s", _serialize_value(actor_id))
            
            user_settings_schema = UserSettingsSchema()
            inst = _get_or_create_user_settings(actor_id)
            audit_log('settings_get', user_id=actor_id)
            logger.info("Settings retrieved successfully for user_id=%s", _serialize_value(actor_id))
            return user_settings_schema.dump(inst), 200
    except SQLAlchemyError as e:
        logger.error("Database error during get settings user_id=%s error=%s", _serialize_value(actor_id), str(e))
        audit_log('settings_get_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"message": "Database error occurred"}), 500
    except Exception as e:
        logger.error("Unexpected error during get settings user_id=%s error=%s traceback=%s", _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('settings_get_failed', user_id=actor_id, detail=f'internal_error: {str(e)}')
        return jsonify({"message": "Internal server error"}), 500


@user_bp.put("/settings")
@jwt_required()
def put_settings_route():
    """
    Update current user's settings.
    Accepts partial JSON. Unknown fields are ignored by the schema.
    """
    logger = get_logger("user_routes")
    actor_id = get_jwt_identity()
    try:
        with log_context(module="user_routes", action="put_settings", actor_id=actor_id):
            logger.info("Put settings request initiated by user_id=%s", _serialize_value(actor_id))
            
            inst = _get_or_create_user_settings(actor_id)
            user_settings_schema = UserSettingsSchema(session=db.session)
            # Load/validate partial update into the existing instance
            payload = request.get_json(force=True, silent=True) or {}
            
            # `partial=True` allows sending only changed fields
            updated_inst = user_settings_schema.load(payload, instance=inst, partial=True)

            db.session.add(updated_inst)
            db.session.commit()
            
            audit_log('settings_update', user_id=actor_id, detail=','.join(payload.keys()))
            logger.info("Settings updated successfully for user_id=%s, keys=%s", _serialize_value(actor_id), ','.join(payload.keys()))
            return user_settings_schema.jsonify(updated_inst), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error during put settings user_id=%s error=%s", _serialize_value(actor_id), str(e))
        audit_log('settings_update_failed', user_id=actor_id, detail=f'database_error: {str(e)}')
        return jsonify({"error": "database_error", "detail": str(e), "traceback": traceback.format_exc()}), 500
    except Exception as e:
        # Marshmallow validation errors arrive as `ValidationError`
        # which has `.messages`, but falling back to str(e) is OK
        db.session.rollback()
        logger.error("Validation error during put settings user_id=%s error=%s traceback=%s", _serialize_value(actor_id), str(e), traceback.format_exc())
        audit_log('settings_update_failed', user_id=actor_id, detail=f'validation_error: {str(e)}')
        return jsonify({"error": "validation_error", "detail": str(e)}), 400
