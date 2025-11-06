
from urllib.parse import unquote
from datetime import datetime
from flask import Blueprint, current_app, render_template, request, jsonify, abort, redirect, url_for
from app.config import Config
from app.models.User import User
from app.models.enumerations import Role
# TokenBlocklist removed in favor of unified tokens model
from app.schemas.user_schema import UserSchema
from flask_jwt_extended import (
    create_access_token, jwt_required,
    get_jwt, set_access_cookies, unset_jwt_cookies
)
from app.utils.decorator import require_roles
view_bp = Blueprint('view_bp', __name__)



ALL_ROLES = tuple(r.value for r in Role)

@view_bp.route('/')
def index():
    return render_template('index.html')


@view_bp.route('/login')
def login_page():
    return render_template('login.html')

@view_bp.route('/profile')
@jwt_required()
@require_roles(*ALL_ROLES)
def profile_page():
    return render_template('profile.html')


@view_bp.route('/change-password')
@jwt_required()
@require_roles(*ALL_ROLES)
def change_password_page():
    return render_template('change-password.html')

@view_bp.route('/register')
def create_user_page():
    return render_template('register.html')

@view_bp.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@view_bp.route('/terms')
def terms_page():
    from datetime import timezone
    return render_template('terms.html', effective_date=datetime.now(timezone.utc).date())

@view_bp.route('/privacy')
def privacy_page():
    from datetime import timezone
    return render_template('privacy.html', effective_date=datetime.now(timezone.utc).date())

@view_bp.route('/admin/unverified')
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def admin_unverified_page():  # injected by decorator
    return render_template('admin/admin_unverified.html')

@view_bp.route('/admin/add-verifier')
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def add_verifier_page():
    return render_template('admin/add_verifier.html')


@view_bp.route('/admin/dashboard')        # canonical path
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def admin_dashboard_page():
    return render_template('admin/admin_dashboard.html')


@view_bp.route('/admin/cycle-management')
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def cycle_management_page():
    """Admin page for managing research cycles and their time windows."""
    return render_template('admin/cycle_management.html')



@view_bp.route('/admin/super/audit')
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def super_audit_page():
    """Superadmin audit log exploration page.

    Uses same underlying API endpoints (/api/v1/super/audit/list & export).
    We only seed initial recent logs (e.g., 50) for fast first paint.
    """
    return render_template('superadmin/super_audit.html')

@view_bp.route('/admin/super/users')
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def superadmin_users_management_page():
    """Superadmin user management SPA-like page (fetches data via /api/v1/super/users)."""
    return render_template('superadmin/super_users.html')

@view_bp.route('/admin/super/roles')
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def superadmin_roles_page():
    """Superadmin role assignment management page."""
    return render_template('superadmin/super_roles.html')

@view_bp.route('/admin/super/users/<user_id>/activity')
@jwt_required()
@require_roles(Role.SUPERADMIN.value)
def superadmin_user_activity_page(user_id):
    # Template will fetch data via API; only pass id
    return render_template('superadmin/user_activity.html', user_id=user_id)

# Research Excellence Routes
@view_bp.route('/research/dashboard')
@jwt_required()
@require_roles(*ALL_ROLES)
def research_dashboard():
    """Research dashboard for users."""
    return render_template('research_dashboard.html')

@view_bp.route('/research/abstracts/submit')
@jwt_required()
@require_roles(Role.USER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def submit_abstract():
    """Submit a research abstract."""
    return render_template('abstract/abstract_submit.html')

@view_bp.route('/research/awards/submit')
@jwt_required()
@require_roles(Role.USER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def submit_award():
    """Submit a research award."""
    return render_template('award/award_submit.html')


@view_bp.route('/research/best-paper/submit')
@jwt_required()
@require_roles(Role.USER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def submit_best_paper():
    """Submit a best paper award."""
    return render_template('bestPaper/best_paper_submit.html')


@view_bp.route('/research/abstracts/verify')
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value, Role.VERIFIER.value)
def verify_abstract():
    """Verify research abstracts."""
    return render_template('abstract/verify_abstract.html')


@view_bp.route('/research/awards/verify')
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value, Role.VERIFIER.value)
def verify_award():
    """Verify research awards."""
    return render_template('award/verify_award.html')


@view_bp.route('/research/best-paper/verify')
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value, Role.VERIFIER.value)
def verify_best_paper():
    """Verify best paper submissions."""
    return render_template('bestPaper/verify_best_paper.html')


@view_bp.route('/research/abstracts/list')
@jwt_required()
@require_roles(Role.USER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def list_abstracts():
    """List research abstracts."""
    return render_template('abstract/submitted_list_abstract.html')

@view_bp.route('/research/awards/list')
@jwt_required()
@require_roles(Role.USER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def list_award():
    """List research awards."""
    return render_template('award/submitted_list_award.html')

@view_bp.route('/research/best-paper/list')
@jwt_required()
@require_roles(Role.USER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def list_best_paper():
    """List research best papers."""
    return render_template('bestPaper/submitted_list_paper.html')

@view_bp.route('/research/grades')
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value, Role.VERIFIER.value)
def grade_management():
    """Grade management page for administrators and verifiers."""
    return render_template('grade_management.html')
