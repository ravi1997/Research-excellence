# routes/user_routes.py

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from app.schemas.user_schema import UserSchema
from app.schemas.user_settings_schema import UserSettingsSchema
from app.utils.decorator import require_roles
from app.models.User import User, UserSettings, UserType, Role, MAX_OTP_RESENDS, PASSWORD_EXPIRATION_DAYS
from app.security_utils import rate_limit, ip_and_path_key, audit_log, coerce_uuid
from app.utils import metrics_cache
from datetime import datetime, timedelta, timezone
from app.extensions import db
user_bp = Blueprint("user_bp", __name__)

# ─── Auth Endpoints ─────────────────────────────────────


@user_bp.route("/change-password", methods=["POST","PUT"])
@jwt_required()
@rate_limit(ip_and_path_key, limit=5, window_sec=900)
def change_password():
    data = request.json or {}
    user_id = get_jwt_identity()
    uid = coerce_uuid(user_id)
    user = User.query.filter_by(id=uid).first()
    if not user:
        audit_log('password_change_failed', actor_id=user_id, detail='user_not_found')
        return jsonify({"message": "User not found"}), 404
    if not user.check_password(data.get("current_password", "")):
        audit_log('password_change_failed', actor_id=user.id, detail='bad_current_password')
        return jsonify({"message": "Current password incorrect"}), 400
    try:
        user.set_password(data.get("new_password"))
    except ValueError as ve:
        audit_log('password_change_failed', actor_id=user.id, detail=str(ve))
        return jsonify({"message": str(ve)}), 400
    user.require_password_change = False
    db.session.commit()
    audit_log('password_changed', actor_id=user.id)
    return jsonify({"message": "Password changed"}), 200


@user_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.json or {}
    user = None
    # OTP flow by mobile
    if data.get("otp") and data.get("mobile"):
        user = User.query.filter_by(mobile=data.get("mobile")).first()
        if not user or not user.verify_otp(data["otp"]):
            return jsonify({"message": "Invalid OTP"}), 400
    # Direct by user_id (admin tool or verified flow)
    elif data.get("user_id"):
        try:
            uid = coerce_uuid(data.get("user_id"))
        except Exception:
            uid = data.get("user_id")
        user = User.query.filter_by(id=uid).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    try:
        user.set_password(data.get("new_password"))
        db.session.commit()
    except ValueError as ve:
        db.session.rollback()
        return jsonify({"message": str(ve)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Internal error"}), 500
    return jsonify({"message": "Password reset"}), 200


@user_bp.route("/unlock", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def auth_unlock():
    data = request.json or {}
    uid = coerce_uuid(data.get("user_id")) if data.get("user_id") else None
    if not uid:
        return jsonify({"message": "user_id required"}), 400
    user = User.query.filter_by(id=uid).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    try:
        user.unlock_account()
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Internal error"}), 500
    return jsonify({"message": f"User {user.id} unlocked"}), 200


@user_bp.route("/status", methods=["GET"])
@jwt_required()
def auth_status():
    user_id = get_jwt_identity()
    uid = coerce_uuid(user_id)
    user = User.query.filter_by(id=uid).first()
    return jsonify({"user": UserSchema().dump(user) if user else None}), 200

# ─── CRUD Endpoints ─────────────────────────────────────


@user_bp.route("/users", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def list_users():
    users = User.query.order_by(User.created_at.asc()).all()
    try:
        audit_log('user_list', actor_id=get_jwt_identity(), detail=f'count={len(users)}')
    except Exception:
        pass
    return jsonify([u.to_dict() for u in users]), 200


@user_bp.route("/users/<user_id>", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def get_user(user_id):
    uid = coerce_uuid(user_id)
    user = User.query.filter_by(id=uid).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    try:
        audit_log('user_get', actor_id=get_jwt_identity(), target_user_id=user_id)
    except Exception:
        pass
    return jsonify(user.to_dict()), 200


@user_bp.route("/users", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_user():
    data = request.get_json(force=True, silent=True) or {}
    password = data.pop("password", None)
    try:
        user = User(**data)
        if password:
            user.set_password(password)
        db.session.add(user)
        db.session.commit()
        try:
            metrics_cache.invalidate()
        except Exception:
            pass
        try:
            audit_log('user_create', actor_id=get_jwt_identity(), target_user_id=user.id)
        except Exception:
            pass
        return jsonify(user.to_dict()), 201
    except ValueError as ve:
        db.session.rollback()
        try:
            audit_log('user_create_failed', actor_id=get_jwt_identity(), detail=str(ve))
        except Exception:
            pass
        return jsonify({"message": str(ve)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("create_user failed")
        try:
            audit_log('user_create_failed', actor_id=get_jwt_identity(), detail='internal_error')
        except Exception:
            pass
        return jsonify({"message": "Internal error"}), 500


@user_bp.route("/users/<user_id>", methods=["PUT"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_user(user_id):
    uid = coerce_uuid(user_id)
    user = User.query.filter_by(id=uid).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    data = request.json or {}
    # Guard: prevent removal of SUPERADMIN role from last superadmin via role updates (if roles list provided)
    roles_payload = data.get('roles') if isinstance(data, dict) else None
    if roles_payload is not None:
        from app.security_utils import audit_log
        # Determine if user currently has SUPERADMIN
        has_super = any(r.role == Role.SUPERADMIN for r in user.role_associations)
        if has_super and Role.SUPERADMIN.value not in roles_payload:
            # Count other superadmins
            from app.models.User import UserRole as UR
            others = User.query.join(UR).filter(UR.role == Role.SUPERADMIN, User.id != user.id).count()
            if others == 0:
                audit_log('superadmin_demote_blocked', target_user_id=user_id, detail='Attempt to remove last superadmin role blocked')
                return jsonify({"message": "Cannot remove last superadmin role"}), 403
    for k, v in (data or {}).items():
        if k == 'password_hash':
            continue
        if hasattr(user, k):
            setattr(user, k, v)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Update failed"}), 500
    try:
        metrics_cache.invalidate()
    except Exception:
        pass
    try:
        audit_log('user_update', actor_id=get_jwt_identity(), target_user_id=user_id)
    except Exception:
        pass
    return jsonify(user.to_dict()), 200


@user_bp.route("/users/<user_id>", methods=["DELETE"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_user(user_id):
    uid = coerce_uuid(user_id)
    user = User.query.filter_by(id=uid).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    # Prevent deletion of superadmin accounts
    if any(r.role == Role.SUPERADMIN for r in user.role_associations):
        from app.security_utils import audit_log
        audit_log('superadmin_delete_blocked', actor_id=None, target_user_id=user_id, detail='Attempt to delete superadmin blocked')
        return jsonify({"message": "Cannot delete superadmin"}), 403
    try:
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Delete failed"}), 500
    try:
        metrics_cache.invalidate()
    except Exception:
        pass
    try:
        audit_log('user_delete', actor_id=get_jwt_identity(), target_user_id=user_id)
    except Exception:
        pass
    return jsonify({"message": "User deleted"}), 200


@user_bp.route("/verifiers", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def list_verifiers():
    """Get all users with verifier role."""
    verifiers = User.query.join(User.role_associations).filter_by(role=Role.VERIFIER).all()
    return jsonify([user.to_dict() for user in verifiers]), 200


@user_bp.route("/users/verifiers", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
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


@user_bp.route("/user/verifiers", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def list_verifiers_simple():
    """Get all users with verifier role - simple endpoint for compatibility."""
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
def lock_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    user.lock_account()
    db.session.commit()
    try:
        metrics_cache.invalidate()
    except Exception:
        pass
    try:
        audit_log('user_lock', actor_id=get_jwt_identity(), target_user_id=user_id)
    except Exception:
        pass
    return jsonify({"message": f"User {user.id} locked"}), 200


@user_bp.route("/users/<user_id>/unlock", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def unlock_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    user.unlock_account()
    db.session.commit()
    try:
        metrics_cache.invalidate()
    except Exception:
        pass
    try:
        audit_log('user_unlock', actor_id=get_jwt_identity(), target_user_id=user_id)
    except Exception:
        pass
    return jsonify({"message": f"User {user.id} unlocked"}), 200


@user_bp.route("/users/<user_id>/reset-otp-count", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def reset_otp_count(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    user.otp_resend_count = 0
    db.session.commit()
    try:
        audit_log('user_reset_otp_count', actor_id=get_jwt_identity(), target_user_id=user_id)
    except Exception:
        pass
    return jsonify({"message": f"OTP count reset for {user.id}"}), 200

# ─── Security Endpoints ─────────────────────────────────


@user_bp.route("/security/extend-password-expiry", methods=["POST"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def extend_password_expiry():
    data = request.json or {}
    uid = data.get("user_id")
    days = data.get("days", PASSWORD_EXPIRATION_DAYS)
    user = User.query.filter_by(id=uid).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    user.password_expiration = datetime.now(timezone.utc) + timedelta(days=days)
    db.session.commit()
    try:
        audit_log('password_expiry_extended', actor_id=get_jwt_identity(), target_user_id=uid, detail=f'days={days}')
    except Exception:
        pass
    return jsonify({"message": "Password expiry extended"}), 200


@user_bp.route("/security/lock-status/<user_id>", methods=["GET"])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def lock_status(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    try:
        audit_log('user_lock_status', actor_id=get_jwt_identity(), target_user_id=user_id, detail=f'locked={user.is_locked()}')
    except Exception:
        pass
    return jsonify({"locked": user.is_locked()}), 200


@user_bp.route("/security/resend-otp", methods=["POST"])
@rate_limit(ip_and_path_key, limit=5, window_sec=600)
def resend_otp():
    data = request.get_json(force=True, silent=True) or {}
    mobile = data.get("mobile")
    user = User.query.filter_by(mobile=mobile).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    if user.is_locked():
        return jsonify({"message": "Account locked"}), 403
    user.resend_otp()
    db.session.commit()
    payload = {"message": "OTP resent"}
    if current_app.config.get("DEBUG"):
        payload["otp"] = user.otp
    return jsonify(payload), 200


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
    inst = db.session.get(UserSettings, user_id)
    if inst is None:
        inst = UserSettings(user_id=user_id, **DEFAULTS)
        db.session.add(inst)
        db.session.commit()
    return inst


@user_bp.get("/settings")
@jwt_required()
def get_settings():
    """Return current user's settings, creating defaults if missing."""
    user_id = get_jwt_identity()
    user_settings_schema = UserSettingsSchema()
    inst = _get_or_create_user_settings(user_id)
    try:
        audit_log('settings_get', actor_id=user_id)
    except Exception:
        pass
    return user_settings_schema.dump(inst), 200


@user_bp.put("/settings")
@jwt_required()
def put_settings():
    """
    Update current user's settings.
    Accepts partial JSON. Unknown fields are ignored by the schema.
    """
    user_id = get_jwt_identity()
    inst = _get_or_create_user_settings(user_id)
    user_settings_schema = UserSettingsSchema(session=db.session)
    # Load/validate partial update into the existing instance
    payload = request.get_json(force=True, silent=True) or {}
    try:
        # `partial=True` allows sending only changed fields
        inst = user_settings_schema.load(payload, instance=inst, partial=True)

        db.session.add(inst)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "database_error", "detail": str(e), "traceback": traceback.format_exc()}), 500
    except Exception as e:
        # Marshmallow validation errors arrive as `ValidationError`
        # which has `.messages`, but falling back to str(e) is OK
        return jsonify({"error": "validation_error", "detail": str(e)}), 400

    try:
        audit_log('settings_update', actor_id=user_id, detail=','.join(payload.keys()))
    except Exception:
        pass
    return user_settings_schema.jsonify(inst), 200
