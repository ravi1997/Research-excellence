
from urllib.parse import unquote
from datetime import datetime
from flask import Blueprint, current_app, render_template, request, jsonify, abort, redirect, url_for
from app.config import Config
from app.models.User import User
from app.extensions import db
from app.models.Cycle import Abstracts, Awards, BestPaper, AbstractVerifiers, AwardVerifiers, BestPaperVerifiers
from app.models.enumerations import Status
from flask_jwt_extended import (
    create_access_token, jwt_required,
    get_jwt, set_access_cookies, unset_jwt_cookies, get_jwt_identity
)
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


@view_bp.route('/coordinator/add-verifier-abstract')
@jwt_required()
@require_roles(Role.COORDINATOR.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def add_verifier_abstract_page():
    return render_template('abstract/add_verifier.html')


@view_bp.route('/coordinator/add-verifier-award')
@jwt_required()
@require_roles(Role.COORDINATOR.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def add_verifier_award_page():
    return render_template('award/add_verifier.html')

@view_bp.route('/coordinator/add-verifier-bestpaper')
@jwt_required()
@require_roles(Role.COORDINATOR.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def add_verifier_bestpaper_page():
    return render_template('bestPaper/add_verifier.html')

@view_bp.route('/coordinator/abstract-gradings')
@jwt_required()
@require_roles(Role.COORDINATOR.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def coordinator_abstract_gradings_page():
    return render_template('coordinator/abstract_gradings.html')


@view_bp.route('/coordinator/award-gradings')
@jwt_required()
@require_roles(Role.COORDINATOR.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def coordinator_award_gradings_page():
    return render_template('coordinator/award_gradings.html')


@view_bp.route('/coordinator/bestpaper-gradings')
@jwt_required()
@require_roles(Role.COORDINATOR.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def coordinator_bestpaper_gradings_page():
    return render_template('coordinator/paper_gradings.html')
@view_bp.route('/admin/dashboard')        # canonical path
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def admin_dashboard_page():
    # Compute basic dashboard stats
    try:
        total_users = db.session.query(db.func.count(User.id)).scalar() or 0
        active_users = db.session.query(db.func.count(User.id)).filter(User.is_active == True).scalar() or 0
        unverified_users = db.session.query(db.func.count(User.id)).filter(User.is_verified == False).scalar() or 0

        # Count active submissions for key models (PENDING or UNDER_REVIEW)
        active_statuses = [Status.PENDING, Status.UNDER_REVIEW]
        abstracts_count = db.session.query(db.func.count(Abstracts.id)).filter(Abstracts.status.in_(active_statuses)).scalar() or 0
        awards_count = db.session.query(db.func.count(Awards.id)).filter(Awards.status.in_(active_statuses)).scalar() or 0
        best_papers_count = db.session.query(db.func.count(BestPaper.id)).filter(BestPaper.status.in_(active_statuses)).scalar() or 0
        active_submissions = abstracts_count + awards_count + best_papers_count

        # Build a short recent activity list by combining newest users, abstracts, awards
        recent_activities = []
        # latest users
        recent_users = db.session.query(User).order_by(User.created_at.desc()).limit(3).all()
        for u in recent_users:
            recent_activities.append({
                'title': f"New user: {u.username or u.email}",
                'subtitle': f"Mobile: {u.mobile or 'N/A'}",
                'ts': getattr(u, 'created_at', None).isoformat() if getattr(u, 'created_at', None) else '',
                'icon': '👤'
            })

        # latest abstracts
        recent_abstracts = db.session.query(Abstracts).order_by(Abstracts.created_at.desc()).limit(3).all()
        for a in recent_abstracts:
            recent_activities.append({
                'title': f"Abstract submitted: {a.title[:80]}",
                'subtitle': f"Category: {getattr(a, 'category', {}).name if getattr(a, 'category', None) else ''}",
                'ts': getattr(a, 'created_at', None).isoformat() if getattr(a, 'created_at', None) else '',
                'icon': '📝'
            })

        # latest awards
        recent_awards = db.session.query(Awards).order_by(Awards.created_at.desc()).limit(3).all()
        for aw in recent_awards:
            recent_activities.append({
                'title': f"Award submitted: {aw.title[:80]}",
                'subtitle': f"Category: {getattr(aw, 'paper_category', {}).name if getattr(aw, 'paper_category', None) else ''}",
                'ts': getattr(aw, 'created_at', None).isoformat() if getattr(aw, 'created_at', None) else '',
                'icon': '🏆'
            })

        # Trim and sort recent_activities by timestamp descending (best-effort)
        def _parse_ts(item):
            try:
                return item.get('ts') or ''
            except Exception:
                return ''

        recent_activities = sorted(recent_activities, key=_parse_ts, reverse=True)[:8]

        # Provide a sensible reports_url fallback (superadmin audit page)
        reports_url = url_for('view_bp.super_audit_page') if 'view_bp' in globals() else '#'

        return render_template(
            'admin/admin_dashboard.html',
            total_users=total_users,
            active_users=active_users,
            unverified_users=unverified_users,
            active_submissions=active_submissions,
            recent_activities=recent_activities,
            reports_url=reports_url
        )
    except Exception:
        # If anything goes wrong, render template with safe defaults
        return render_template(
            'admin/admin_dashboard.html',
            total_users=0,
            active_users=0,
            unverified_users=0,
            active_submissions=0,
            recent_activities=[],
            reports_url='#'
        )


@view_bp.route('/verifier/dashboard')
@jwt_required()
@require_roles(Role.VERIFIER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def verifier_dashboard_page():
    """Dashboard for verifiers showing assigned items and pending verifications."""
    try:
        current_user_id = get_jwt_identity()

        # Counts of assignments
        assigned_abstracts = db.session.query(db.func.count(AbstractVerifiers.abstract_id)).filter(AbstractVerifiers.user_id == current_user_id).scalar() or 0
        assigned_awards = db.session.query(db.func.count(AwardVerifiers.award_id)).filter(AwardVerifiers.user_id == current_user_id).scalar() or 0
        assigned_bestpapers = db.session.query(db.func.count(BestPaperVerifiers.best_paper_id)).filter(BestPaperVerifiers.user_id == current_user_id).scalar() or 0

        # Pending to verify (limit to items in PENDING or UNDER_REVIEW)
        pending_abstracts = db.session.query(db.func.count(Abstracts.id)).join(AbstractVerifiers, Abstracts.id == AbstractVerifiers.abstract_id).filter(
            AbstractVerifiers.user_id == current_user_id,
            Abstracts.status.in_([Status.PENDING, Status.UNDER_REVIEW])
        ).scalar() or 0

        pending_awards = db.session.query(db.func.count(Awards.id)).join(AwardVerifiers, Awards.id == AwardVerifiers.award_id).filter(
            AwardVerifiers.user_id == current_user_id,
            Awards.status.in_([Status.PENDING, Status.UNDER_REVIEW])
        ).scalar() or 0

        pending_bestpapers = db.session.query(db.func.count(BestPaper.id)).join(BestPaperVerifiers, BestPaper.id == BestPaperVerifiers.best_paper_id).filter(
            BestPaperVerifiers.user_id == current_user_id,
            BestPaper.status.in_([Status.PENDING, Status.UNDER_REVIEW])
        ).scalar() or 0

        total_pending = pending_abstracts + pending_awards + pending_bestpapers

        # Recent assignments: fetch latest assigned items to this verifier
        recent_tasks = []
        recent_abs = db.session.query(Abstracts, AbstractVerifiers.assigned_at).join(AbstractVerifiers, Abstracts.id == AbstractVerifiers.abstract_id).filter(AbstractVerifiers.user_id == current_user_id).order_by(AbstractVerifiers.assigned_at.desc()).limit(5).all()
        for a, at in recent_abs:
            recent_tasks.append({
                'type': 'Abstract',
                'title': a.title[:100],
                'ts': at.isoformat() if at else '',
                'id': str(a.id)
            })

        recent_aw = db.session.query(Awards, AwardVerifiers.assigned_at).join(AwardVerifiers, Awards.id == AwardVerifiers.award_id).filter(AwardVerifiers.user_id == current_user_id).order_by(AwardVerifiers.assigned_at.desc()).limit(5).all()
        for aw, at in recent_aw:
            recent_tasks.append({
                'type': 'Award',
                'title': aw.title[:100],
                'ts': at.isoformat() if at else '',
                'id': str(aw.id)
            })

        recent_bp = db.session.query(BestPaper, BestPaperVerifiers.assigned_at).join(BestPaperVerifiers, BestPaper.id == BestPaperVerifiers.best_paper_id).filter(BestPaperVerifiers.user_id == current_user_id).order_by(BestPaperVerifiers.assigned_at.desc()).limit(5).all()
        for bp, at in recent_bp:
            recent_tasks.append({
                'type': 'BestPaper',
                'title': bp.title[:100],
                'ts': at.isoformat() if at else '',
                'id': str(bp.id)
            })

        recent_tasks = sorted(recent_tasks, key=lambda x: x.get('ts') or '', reverse=True)[:8]

        return render_template(
            'verifier/verifier_dashboard.html',
            assigned_abstracts=assigned_abstracts,
            assigned_awards=assigned_awards,
            assigned_bestpapers=assigned_bestpapers,
            total_pending=total_pending,
            recent_tasks=recent_tasks
        )
    except Exception:
        return render_template('verifier/verifier_dashboard.html', assigned_abstracts=0, assigned_awards=0, assigned_bestpapers=0, total_pending=0, recent_tasks=[])


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
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
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
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def grade_management():
    """Grade management page for administrators and verifiers."""
    return render_template('grade_management.html')
