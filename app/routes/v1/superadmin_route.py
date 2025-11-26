import traceback
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta, timezone
from app.models import AuditLog, User
from app.models.User import UserRole
from app.models.enumerations import Role
from app.models.Cycle import Category, PaperCategory
from app.utils.decorator import require_roles
from app.extensions import db
from app.schemas.user_schema import UserSchema
from sqlalchemy import text

super_api_bp = Blueprint('super_api_bp',  __name__)

@super_api_bp.route('/users', methods=['GET'])
@jwt_required()
@require_roles(Role.ADMIN.value,Role.SUPERADMIN.value)
def list_users():
    """API endpoint to list users with filtering and pagination."""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '').strip()
        role = request.args.get('role', '').strip()
        status = request.args.get('status', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_dir = request.args.get('sort_dir', 'desc')
        
        # Validate limit
        if limit > 1000:
            limit = 100  # Maximum limit for performance reasons
        
        # Build query
        query = User.query.options(
            joinedload(User.categories),
            joinedload(User.paper_categories),
            joinedload(User.award_categories),
        )
        
        # Apply search filter
        if search:
            search_filter = or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.employee_id.ilike(f'%{search}%'),
                User.mobile.ilike(f'%{search}%'),
            )
            query = query.filter(search_filter)
        
        # Apply role filter
        if role and role != 'all':
            query = query.join(User.role_associations).filter(UserRole.role == Role(role))
        
        # Apply status filter
        if status == 'active':
            query = query.filter(User.is_active == True)
        elif status == 'inactive':
            query = query.filter(User.is_active == False)
        
        # Apply sorting
        if sort_by == 'username':
            if sort_dir == 'asc':
                query = query.order_by(User.username.asc())
            else:
                query = query.order_by(User.username.desc())
        elif sort_by == 'email':
            if sort_dir == 'asc':
                query = query.order_by(User.email.asc())
            else:
                query = query.order_by(User.email.desc())
        elif sort_by == 'created_at':
            if sort_dir == 'asc':
                query = query.order_by(User.created_at.asc())
            else:
                query = query.order_by(User.created_at.desc())
        else:
            # Default sort
            query = query.order_by(User.created_at.desc())
        
        # Calculate pagination
        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        
        # Ensure page is within valid range
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Execute query with pagination
        users = query.offset(offset).limit(limit).all()
        
        # Prepare response
        user_schema = UserSchema()
        items = []
        for user in users:
            user_dict = user_schema.dump(user)
            # Add roles to the response
            user_dict['roles'] = [r.value for r in user.roles]
            # Add locked status
            user_dict['locked'] = user.is_locked()
            items.append(user_dict)
        
        response = {
            'items': items,
            'current_page': page,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error in list_users: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>', methods=['GET'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def get_user(user_id):
    """API endpoint to get a specific user."""
    try:
        user = (
            User.query.options(
                joinedload(User.categories),
                joinedload(User.paper_categories),
                joinedload(User.award_categories),
            )
            .filter_by(id=user_id)
            .first()
        )
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_schema = UserSchema()
        user_data = user_schema.dump(user)
        user_data['roles'] = [r.value for r in user.roles]
        user_data['locked'] = user.is_locked()
        
        return jsonify({'user': user_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>/roles', methods=['POST'])
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def update_user_roles(user_id):
    """API endpoint to update user roles."""
    try:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        roles = data.get('roles', [])
        
        # Clear existing roles
        user.role_associations.clear()
        
        # Add new roles
        for role_name in roles:
            if role_name in [r.value for r in Role]:
                user.role_associations.append(UserRole(role=Role(role_name)))

        db.session.commit()
        
        return jsonify({'message': 'Roles updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/bulk/roles', methods=['POST'])
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def bulk_update_user_roles():
    """API endpoint to bulk update user roles."""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        roles = data.get('roles', [])
        
        users = User.query.filter(User.id.in_(user_ids)).all()
        
        for user in users:
            # Clear existing roles
            user.role_associations.clear()
            
            # Add new roles
            for role_name in roles:
                if role_name in [r.value for r in Role]:
                    user.role_associations.append(UserRole(role=Role(role_name)))
        
        db.session.commit()
        
        return jsonify({'message': f'Roles updated for {len(users)} users'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>/activate', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def activate_user(user_id):
    """API endpoint to activate a user."""
    try:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        
        return jsonify({'message': 'User activated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>/deactivate', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def deactivate_user(user_id):
    """API endpoint to deactivate a user."""
    try:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'message': 'User deactivated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>/lock', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def lock_user(user_id):
    """API endpoint to lock a user account."""
    try:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.lock_account()
        db.session.commit()
        
        return jsonify({'message': 'User locked successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>/unlock', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def unlock_user(user_id):
    """API endpoint to unlock a user account."""
    try:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.unlock_account()
        db.session.commit()
        
        return jsonify({'message': 'User unlocked successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>/verify', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def verify_user(user_id):
    """API endpoint to verify a user account."""
    try:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.is_verified = True
        db.session.commit()

        return jsonify({'message': 'User verified successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>/unverify', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def unverify_user(user_id):
    """API endpoint to unverify a user account."""
    try:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.is_verified = False
        db.session.commit()

        return jsonify({'message': 'User unverifed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@super_api_bp.route('/users/bulk/activate', methods=['POST'])
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def bulk_activate_users():
    """API endpoint to bulk activate users."""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        users = User.query.filter(User.id.in_(user_ids)).all()
        for user in users:
            user.is_active = True
            user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({'message': f'{len(users)} users activated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/bulk/deactivate', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_deactivate_users():
    """API endpoint to bulk deactivate users."""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        users = User.query.filter(User.id.in_(user_ids)).all()
        for user in users:
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({'message': f'{len(users)} users deactivated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/bulk/lock', methods=['POST'])
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def bulk_lock_users():
    """API endpoint to bulk lock users."""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        users = User.query.filter(User.id.in_(user_ids)).all()
        for user in users:
            user.lock_account()
        
        db.session.commit()
        
        return jsonify({'message': f'{len(users)} users locked successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/bulk/unlock', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_unlock_users():
    """API endpoint to bulk unlock users."""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        users = User.query.filter(User.id.in_(user_ids)).all()
        for user in users:
            user.unlock_account()
        
        db.session.commit()
        
        return jsonify({'message': f'{len(users)} users unlocked successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_user():
    """API endpoint to create a new user."""
    try:
        data = request.get_json()
        
        # Check if user already exists by email
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Check if user already exists by employee_id
        if data.get('employee_id') and User.query.filter_by(employee_id=data['employee_id']).first():
            return jsonify({'error': 'Employee ID already exists'}), 409
        
        # Create new user
        user = User(
            username=data.get('username'),
            email=data.get('email'),
            employee_id=data.get('employee_id'),
            mobile=data.get('mobile'),
            is_active=data.get('is_active', True)
        )
        
        # Set password if provided
        password = data.get('password')
        if password:
            user.set_password(password)
        else:
            # Generate a temporary password
            from app.utils.generators import generate_strong_password
            temp_password = generate_strong_password(12)
            user.set_password(temp_password)
        
        user.require_password_change = True
        
        # Add roles
        roles = data.get('roles', [])
        for role_name in roles:
            if role_name in [r.value for r in Role]:
                user.role_associations.append(UserRole(role=Role(role_name)))
        
        db.session.add(user)

        try:
            category_ids = _extract_category_ids(data, default_none=False)
            _apply_user_categories(user, category_ids)

            paper_category_ids = _extract_paper_category_ids(data, default_none=False)
            _apply_user_paper_categories(user, paper_category_ids)

            award_category_ids = _extract_award_category_ids(data, default_none=False)
            _apply_user_award_categories(user, award_category_ids)
        except ValueError as exc:
            db.session.rollback()
            return jsonify({'error': str(exc)}), 400

        db.session.commit()
        
        user_schema = UserSchema()
        user_data = user_schema.dump(user)
        user_data['roles'] = [r.value for r in user.roles]
        
        return jsonify({'message': 'User created successfully', 'user': user_data}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create user: {str(e)}")
        current_app.logger.error(f'{traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/users/<user_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_user(user_id):
    """API endpoint to update an existing user."""
    try:
        user = (
            User.query.options(joinedload(User.categories))
            .filter_by(id=user_id)
            .first()
        )
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Check if email is being changed and if it already exists
        new_email = data.get('email')
        if new_email and new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                return jsonify({'error': 'Email already exists'}), 409
        
        # Check if employee_id is being changed and if it already exists
        new_employee_id = data.get('employee_id')
        if new_employee_id and new_employee_id != user.employee_id:
            if new_employee_id and User.query.filter_by(employee_id=new_employee_id).first():
                return jsonify({'error': 'Employee ID already exists'}), 409
        
        # Update user fields
        user.username = data.get('username', user.username)
        user.email = new_email or user.email
        user.employee_id = new_employee_id or user.employee_id
        user.mobile = data.get('mobile', user.mobile)
        user.is_active = data.get('is_active', user.is_active)
        
        # Update roles only if provided
        if 'roles' in data:
            incoming_roles = data.get('roles') or []

            db_role_values = _get_db_role_values()
            allowed_values = {value.lower(): value for value in db_role_values}

            resolved_roles = []
            for raw_role in incoming_roles:
                key = str(raw_role).strip().lower()
                db_value = allowed_values.get(key)
                if not db_value:
                    db.session.rollback()
                    return jsonify({'error': f"Invalid role '{raw_role}'"}), 400

                matched_enum = None
                for role_enum in Role:
                    if role_enum.value.lower() == db_value.lower() or role_enum.name.lower() == db_value.lower():
                        matched_enum = role_enum
                        break
                if not matched_enum:
                    # Fall back to creating via value to support legacy enums
                    try:
                        matched_enum = Role(db_value)
                    except ValueError:
                        db.session.rollback()
                        return jsonify({'error': f"Unsupported role '{raw_role}'"}), 400

                resolved_roles.append(matched_enum)

            user.role_associations.clear()
            for role_enum in resolved_roles:
                user.role_associations.append(UserRole(role=role_enum))
        
        # Update password if provided
        new_password = data.get('password')
        if new_password:
            user.set_password(new_password)

        try:
            category_ids = _extract_category_ids(data)
            _apply_user_categories(user, category_ids)

            paper_category_ids = _extract_paper_category_ids(data)
            _apply_user_paper_categories(user, paper_category_ids)

            award_category_ids = _extract_award_category_ids(data)
            _apply_user_award_categories(user, award_category_ids)
        except ValueError as exc:
            db.session.rollback()
            return jsonify({'error': str(exc)}), 400
        
        db.session.commit()
        
        user_schema = UserSchema()
        user_data = user_schema.dump(user)
        user_data['roles'] = [r.value for r in user.roles]
        
        return jsonify({'message': 'User updated successfully', 'user': user_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@super_api_bp.route('/audit/list', methods=['GET'])
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def list_audit_logs():
    """API endpoint to list audit logs with filtering and pagination."""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        event = request.args.get('event', None)
        user_id = request.args.get('user_id', None)
        target_user_id = request.args.get('target_user_id', None)
        ip = request.args.get('ip', None)
        date_range = request.args.get('date_range', None)
        
        # Validate limit
        if limit > 1000:
            limit = 100  # Maximum limit for performance reasons
        
        # Build query
        query = AuditLog.query
        
        # Apply filters
        if event:
            query = query.filter(AuditLog.event == event)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if target_user_id:
            query = query.filter(AuditLog.target_user_id == target_user_id)
        
        if ip:
            query = query.filter(AuditLog.ip == ip)
        
        # Date range filtering
        if date_range:
            now = datetime.utcnow()
            if date_range == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(AuditLog.created_at >= start_date)
            elif date_range == 'week':
                start_date = now - timedelta(days=7)
                query = query.filter(AuditLog.created_at >= start_date)
            elif date_range == 'month':
                start_date = now - timedelta(days=30)
                query = query.filter(AuditLog.created_at >= start_date)
            elif date_range == 'custom':
                # Additional logic would be needed to handle custom date ranges
                pass
        
        # Order by ID (descending to show newest first)
        query = query.order_by(AuditLog.id.desc())
        
        # Calculate pagination
        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        
        # Ensure page is within valid range
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Execute query with pagination
        audit_logs = query.offset(offset).limit(limit).all()
        
        # Prepare response
        items = [log.to_dict() for log in audit_logs]
        
        response = {
            'items': items,
            'current_page': page,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
        
        return jsonify(response), 200
    
    except ValueError as e:
        # Handle cases where request parameters can't be converted to int
        return jsonify({
            'items': [],
            'current_page': 1,
            'total_pages': 1,
            'total_count': 0,
            'has_next': False,
            'has_prev': False,
            'error': f'Invalid parameter: {str(e)}'
        }), 40
    except Exception as e:
        current_app.logger.error(f"Error in list_audit_logs: {str(e)}")
        return jsonify({
            'items': [],
            'current_page': 1,
            'total_pages': 1,
            'total_count': 0,
            'has_next': False,
            'has_prev': False,
            'error': f'System error occurred: {str(e)}'
        }), 500


@super_api_bp.route('/audit/export', methods=['GET'])
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def export_audit_logs():
    """API endpoint to export audit logs in JSON format."""
    try:
        # Get query parameters (same as list but without pagination)
        event = request.args.get('event', None)
        user_id = request.args.get('user_id', None)
        target_user_id = request.args.get('target_user_id', None)
        ip = request.args.get('ip', None)
        date_range = request.args.get('date_range', None)
        
        # Build query
        query = AuditLog.query
        
        # Apply filters (same as list endpoint)
        if event:
            query = query.filter(AuditLog.event == event)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if target_user_id:
            query = query.filter(AuditLog.target_user_id == target_user_id)
        
        if ip:
            query = query.filter(AuditLog.ip == ip)
        
        # Date range filtering
        if date_range:
            now = datetime.utcnow()
            if date_range == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(AuditLog.created_at >= start_date)
            elif date_range == 'week':
                start_date = now - timedelta(days=7)
                query = query.filter(AuditLog.created_at >= start_date)
            elif date_range == 'month':
                start_date = now - timedelta(days=30)
                query = query.filter(AuditLog.created_at >= start_date)
        
        # Order by ID (descending to show newest first)
        query = query.order_by(AuditLog.id.desc())
        
        # Execute query (limit to 10000 records for export to prevent memory issues)
        audit_logs = query.limit(10000).all()
        
        # Prepare response
        items = [log.to_dict() for log in audit_logs]
        
        return jsonify({
            'items': items,
            'count': len(items)
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error in export_audit_logs: {str(e)}")
        return jsonify({
            'items': [],
            'count': 0,
            'error': f'System error occurred: {str(e)}'
        }), 500


@super_api_bp.route('/audit/events', methods=['GET'])
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def get_unique_audit_events():
    """API endpoint to get unique event types from audit logs."""
    try:
        # Query unique event types from the audit logs table
        unique_events = db.session.query(AuditLog.event).distinct(AuditLog.event).all()
        
        # Extract event names from the tuples returned by the query
        event_list = [event[0] for event in unique_events if event[0] is not None]
        
        # Sort the events alphabetically for better UX
        event_list.sort()
        
        return jsonify({
            'events': event_list,
            'count': len(event_list)
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error in get_unique_audit_events: {str(e)}")
        return jsonify({
            'events': [],
            'count': 0,
            'error': f'System error occurred: {str(e)}'
        }), 500


_DB_ROLE_CACHE = None


def _extract_category_like_ids(payload, *, plural_key, singular_key, default_none=True):
    """Pull a flat list of category-ish IDs from a payload."""
    if not isinstance(payload, dict):
        return None

    sentinel = object()
    value = payload.get(plural_key, sentinel)
    if value is sentinel:
        plural_without_suffix = plural_key.replace("_ids", "")
        value = payload.get(plural_without_suffix, sentinel)
        if value is sentinel:
            if singular_key in payload:
                single = payload.get(singular_key)
                value = [] if not single else [single]
            else:
                return None if default_none else []

    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, dict):
        candidate = value.get("id") or value.get(singular_key)
        return [candidate] if candidate else []

    result = []
    for item in value:
        candidate = item
        if isinstance(item, dict):
            candidate = item.get("id") or item.get(singular_key)
        if candidate in (None, ""):
            continue
        result.append(candidate)
    return result


def _extract_category_ids(payload, *, default_none=True):
    return _extract_category_like_ids(payload, plural_key="category_ids", singular_key="category_id", default_none=default_none)


def _extract_paper_category_ids(payload, *, default_none=True):
    return _extract_category_like_ids(payload, plural_key="paper_category_ids", singular_key="paper_category_id", default_none=default_none)


def _extract_award_category_ids(payload, *, default_none=True):
    return _extract_category_like_ids(payload, plural_key="award_category_ids", singular_key="award_category_id", default_none=default_none)


def _normalize_category_ids(category_ids):
    if category_ids is None:
        return None
    normalized = []
    for raw in category_ids:
        if raw in (None, ""):
            continue
        try:
            normalized_id = str(uuid.UUID(str(raw)))
        except (ValueError, TypeError, AttributeError):
            continue
        if normalized_id not in normalized:
            normalized.append(normalized_id)
    return normalized


def _apply_user_categories(user, category_ids):
    normalized = _normalize_category_ids(category_ids)
    if normalized is None:
        return

    if not normalized:
        user.categories = []
        user.category_id = None
        return

    categories = Category.query.filter(Category.id.in_(normalized)).all()
    category_map = {str(cat.id): cat for cat in categories}
    missing = [cid for cid in normalized if cid not in category_map]
    if missing:
        raise ValueError(f"Unknown category ids: {', '.join(missing)}")

    ordered = []
    for cid in normalized:
        cat = category_map.get(cid)
        if cat and cat not in ordered:
            ordered.append(cat)

    user.categories = ordered
    user.category_id = ordered[0].id if ordered else None


def _apply_user_paper_categories(user, category_ids):
    normalized = _normalize_category_ids(category_ids)
    if normalized is None:
        return

    if not normalized:
        user.paper_categories = []
        return

    categories = PaperCategory.query.filter(PaperCategory.id.in_(normalized)).all()
    category_map = {str(cat.id): cat for cat in categories}
    missing = [cid for cid in normalized if cid not in category_map]
    if missing:
        raise ValueError(f"Unknown paper category ids: {', '.join(missing)}")

    ordered = []
    for cid in normalized:
        cat = category_map.get(cid)
        if cat and cat not in ordered:
            ordered.append(cat)

    user.paper_categories = ordered


def _apply_user_award_categories(user, category_ids):
    normalized = _normalize_category_ids(category_ids)
    if normalized is None:
        return

    if not normalized:
        user.award_categories = []
        return

    categories = PaperCategory.query.filter(PaperCategory.id.in_(normalized)).all()
    category_map = {str(cat.id): cat for cat in categories}
    missing = [cid for cid in normalized if cid not in category_map]
    if missing:
        raise ValueError(f"Unknown award category ids: {', '.join(missing)}")

    ordered = []
    for cid in normalized:
        cat = category_map.get(cid)
        if cat and cat not in ordered:
            ordered.append(cat)

    user.award_categories = ordered


def _get_db_role_values():
    global _DB_ROLE_CACHE
    if _DB_ROLE_CACHE is not None:
        return _DB_ROLE_CACHE

    try:
        rows = db.session.execute(
            text(
                """
                SELECT enumlabel
                FROM pg_enum
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
                WHERE pg_type.typname = :enum_name
                ORDER BY enumsortorder
                """
            ),
            {"enum_name": "role"},
        ).fetchall()
        values = [row[0] for row in rows if row and row[0]]
        if values:
            _DB_ROLE_CACHE = values
            return values
    except Exception as exc:
        current_app.logger.warning("Failed to introspect role enum; falling back to application enum: %s", exc)

    fallback = [role.value for role in Role]
    _DB_ROLE_CACHE = fallback
    return fallback
