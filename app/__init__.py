import json
import os
from dotenv import load_dotenv
from flask import Flask, app, render_template, request, jsonify, send_from_directory, g
import secrets
from app.security_utils import log_structured
from app.utils.logging_utils import get_logger, init_logger
import logging
from logging.handlers import RotatingFileHandler
from flask_compress import Compress
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .commands.user_commands import create_user, create_superadmin, rotate_superadmin_password
from .commands.setup_commands import setup_command
from .commands.seed_commands import seed_command


from app.routes import register_blueprints

# Load environment variables from .env file
load_dotenv()

# Import configuration after loading .env
from .config import config, Config
from .extensions import jwt, db, migrate, ma
from .security import init_jwt_callbacks
from .models import *
from app.models.enumerations import Role
from app.models.User import User, UserRole
from datetime import datetime, timezone
from sqlalchemy import event, inspect
from flask_jwt_extended import verify_jwt_in_request, get_jwt



def configure_logging(app):
    log_file = app.config.get('LOG_FILE', '/tmp/research_excellence_app.log')
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    if not app.logger.handlers:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=app.config.get('LOG_MAX_BYTES', 10485760),  # 10MB default
            backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
        )
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        )
        file_handler.setFormatter(formatter)
        log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)

    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    app.logger.setLevel(log_level)
    app.logger.info("Logging configured with level: %s", app.config.get('LOG_LEVEL', 'INFO'))

    # Configure categorized loggers using the same application config.
    init_logger(app)

    # Wire internal library/module loggers to use the same handlers/formatting
    # Avoid duplicate emission by disabling propagation and attaching app handlers.
    def _wire_logger(name: str, level: int | None = None):
        try:
            lg = logging.getLogger(name)
            lg.propagate = False
            # Clear any pre-existing handlers to prevent double-logging
            lg.handlers = []
            for h in app.logger.handlers:
                lg.addHandler(h)
            lg.setLevel(level if level is not None else app.logger.level)
            app.logger.debug(f"Logger wired: %s", name)
        except Exception:
            # Non-fatal; continue
            pass

    # Wire known internal module loggers. Add here when new modules introduce
    # their own named loggers to keep formatting consistent.
    names_levels = {
        'tasks': logging.INFO,
        'auth': logging.INFO,
        'security_utils': logging.INFO,
    }
    # Allow env overrides: APP_LOG_LEVEL_<LOGGER>=DEBUG|INFO|WARNING|ERROR|CRITICAL
    lvl_map = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET,
    }
    for k, v in os.environ.items():
        if not k.startswith('APP_LOG_LEVEL_'):
            continue
        name = k[len('APP_LOG_LEVEL_'):].strip().lower()
        level = lvl_map.get((v or '').strip().upper())
        if not name or level is None:
            continue
        names_levels[name] = level
    for name, lvl in names_levels.items():
        _wire_logger(name, lvl)


def create_app(config_name=None):
    # Determine configuration based on environment variable or parameter
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    config_class = config.get(config_name, Config)
    
    app = Flask(__name__, static_url_path='/static')
    app.config.from_object(config_class)
    
    # Initialize configuration-specific setup
    config_class.init_app(app)

    configure_logging(app)
    app.logger.info("Using config: %s", config_class.__name__)
    get_logger("app").info("Application startup with config %s", config_class.__name__)

    # Optional proxy fix: enable when running behind a trusted proxy by setting PROXY_FIX_NUM
    try:
        num_proxies = int(os.environ.get('PROXY_FIX_NUM', '0'))
    except Exception:
        num_proxies = 0
    if num_proxies > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=num_proxies, x_proto=num_proxies, x_host=num_proxies, x_port=num_proxies, x_prefix=num_proxies)
        app.logger.info("ProxyFix enabled for %d proxies", num_proxies)
    
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    jwt.init_app(app)
    init_jwt_callbacks(jwt)
    app.cli.add_command(create_user)
    app.cli.add_command(create_superadmin)
    app.cli.add_command(rotate_superadmin_password)
    app.cli.add_command(setup_command)
    app.cli.add_command(seed_command)

    # ------------------------------------------------------------------
    # Logging & Access log middleware
    # ------------------------------------------------------------------
    @app.before_request
    def _log_request():
        log_structured("request", method=request.method, path=request.path, ip=request.remote_addr, args=dict(request.args))

    @app.after_request
    def _log_response(resp):
        # log_structured("response", method=request.method, path=request.path, status=resp.status_code)
        # Security headers (idempotent set / override)
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        resp.headers.setdefault('X-XSS-Protection', '1; mode=block')
        resp.headers.setdefault('Referrer-Policy', 'no-referrer')
        resp.headers.setdefault('Permissions-Policy', 'fullscreen=()')
        nonce = getattr(g, 'csp_nonce', None)
        script_src = "'self' blob: 'unsafe-eval' 'wasm-unsafe-eval'"
        if nonce:
            script_src += f" 'nonce-{nonce}'"
        csp = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "media-src 'self' data:; "
            f"script-src {script_src}; "
            "worker-src 'self' blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "object-src 'none'; frame-ancestors 'self' http://127.0.0.1:5000; base-uri 'self'; manifest-src 'self'"
        )
        # Only set if not already (allow tests to override)
        resp.headers.setdefault('Content-Security-Policy', csp)
        # Basic favicon fallbacks if not present
        if 'Link' not in resp.headers:
            resp.headers.add('Link', '</static/images/favicon.ico>; rel="icon"')
        return resp

    # ------------------------------------------------------------------
    # Enforce password change requirement (post-auth) except for allowed paths
    # ------------------------------------------------------------------
    @app.before_request
    def _enforce_password_change():
        # Skip for static and unauthenticated endpoints
        p = request.path
        if p.startswith('/static') or p.startswith('/static') or p.startswith('/favicon') or p.startswith('/favicon'):
            return
        allowed_paths = {
            '/api/v1/user/change-password',
            '/change-password',
            '/api/v1/auth/login',
            '/api/v1/auth/logout',
            '/api/v1/auth/me',
            '/api/v1/user/status',
            # Backwards-compat (if any legacy routes remain)
            '/api/v1/user/change-password',
            '/change-password',
            '/api/v1/auth/login',
            '/api/v1/auth/logout',
            '/api/v1/auth/me',
            '/api/v1/user/status'
        }
        if p in allowed_paths or p.startswith('/auth') or p.startswith('/auth'):
            return
        try:
            verify_jwt_in_request(optional=True)
            jwt_data = get_jwt()
            if not jwt_data:
                return
            uid = jwt_data.get('sub')
            if not uid:
                return
            # Lazy import to avoid circular
            from app.models.User import User as U
            from app.extensions import db as _db
            from app.security_utils import coerce_uuid
            user = _db.session.get(U, coerce_uuid(uid))
            if user and user.require_password_change:
                return jsonify({'error':'password_change_required'}), 403
        except Exception:
            # Do not block if token missing/invalid; other handlers manage it
            return

    @app.before_request
    def _set_csp_nonce():
        # Only generate if we might need (cheap anyway)
        g.csp_nonce = secrets.token_urlsafe(12)

    # Jinja helper
    @app.context_processor
    def _inject_nonce():
        return {'csp_nonce': lambda: getattr(g, 'csp_nonce', '')}

    # ------------------------------------------------------------------
    # Context processor to make current user available in templates
    # ------------------------------------------------------------------
    @app.context_processor
    def inject_user():
        from flask_jwt_extended import get_jwt_identity
        from app.models.User import User
        try:
            user_id = get_jwt_identity()
            if user_id:
                user = User.query.get(user_id)
                return dict(current_user=user)
        except Exception:
            pass
        return dict(current_user=None)

    # ------------------------------------------------------------------
    # Dynamic DB schema readiness guard
    # If core tables are missing, short-circuit API requests with 503 instead
    # of producing raw ProgrammingError stack traces. Re-checks until ready.
    # ------------------------------------------------------------------
    CORE_TABLES = {"users", "user_roles"}

    @app.before_request
    def _schema_guard():  # pragma: no cover (runtime environment dependent)
        # Allow static, favicon, and OPTIONS preflight unimpeded
        if request.method == 'OPTIONS':
            return
        p = request.path
        if p.startswith('/static') or p.startswith('/static') or p in ('/favicon.ico','/favicon.ico'):
            return
        ready = app.config.get('DB_SCHEMA_READY')
        if ready:
            return
        try:
            insp = inspect(db.engine)
            present = set(insp.get_table_names())
            if CORE_TABLES.issubset(present):
                app.config['DB_SCHEMA_READY'] = True
                return
            # Not ready yet; only intercept API / auth / admin sensitive endpoints
            if p.startswith('/api/') or p.startswith('/api/') or p.startswith('/admin') or p.startswith('/admin'):
                return jsonify({
                    'error': 'database_uninitialized',
                    'detail': 'Core tables missing. Run migrations: flask db upgrade',
                    'missing': sorted(list(CORE_TABLES - present))
                }), 503
        except Exception:
            # On unexpected inspection failure, do not block (original error will surface)
            return

    # ------------------------------------------------------------------
    # Error Handlers (generic safe messages)
    # ------------------------------------------------------------------
    # Then in error handler:



    @app.errorhandler(401)
    def _unauthorized(e):
        return render_template('login.html')

    @app.errorhandler(404)
    def _not_found(e):
        try:
            return jsonify({"error": f"{e}"}), 404
        except Exception:
            return jsonify({"error": "not_found"}), 404

    @app.errorhandler(429)
    def _rate_limited(e):
        return jsonify({"error": "rate_limited"}), 429

    @app.errorhandler(500)
    def _server_error(e):
        app.logger.exception("Unhandled server error")
        return jsonify({"error": "internal_server_error"}), 500
    # MongoDB connectivity (legacy) removed; SQLAlchemy is the sole datastore.



    

    Compress(app)
    CORS(app,supports_credentials=True)
    app.logger.info("Middleware loaded: Compress, CORS")

    # ------------------------------------------------------------------
    # Optional auto-migration (development / CI convenience)
    # Controlled via AUTO_MIGRATE_ON_STARTUP env flag.
    # Executes Alembic 'upgrade head' once per start.
    # ------------------------------------------------------------------
    if app.config.get('AUTO_MIGRATE_ON_STARTUP'):
        with app.app_context():
            try:
                from alembic import command
                from alembic.config import Config as AlembicConfig
                alembic_ini = os.path.join(os.path.dirname(__file__), '..', 'migrations', 'alembic.ini')
                # Allow both repo layouts; fallback to top-level migrations/alembic.ini
                if not os.path.exists(alembic_ini):
                    alembic_ini = os.path.join(app.root_path, '..', 'migrations', 'alembic.ini')
                if os.path.exists(alembic_ini):
                    alembic_cfg = AlembicConfig(alembic_ini)
                    # Ensure script location resolves relative paths
                    if not alembic_cfg.get_main_option('script_location'):
                        alembic_cfg.set_main_option('script_location', 'migrations')
                    app.logger.info('Auto-migration: upgrading database schema to head')
                    # command.upgrade(alembic_cfg, 'head')
                    app.logger.info('Auto-migration complete.')
                else:
                    app.logger.info('Auto-migration enabled but alembic.ini not found; skipping.')
            except Exception as e:
                app.logger.info('Auto-migration failed: %s', e)


    # ------------------------------------------------------------------
    # User Accounts Bootstrap (runs once per start; idempotent)
    # ------------------------------------------------------------------
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            table_names = set(inspector.get_table_names())
            required = {"users", "user_roles"}
            if not required.issubset(table_names):
                app.logger.info("Bootstrap skip: required tables %s missing (have: %s)", required, table_names)
            else:
                # Superadmin bootstrap
                superadmin_pwd = app.config.get('SUPERADMIN_PASSWORD')
                if superadmin_pwd:
                    exists = User.query.join(UserRole).filter(UserRole.role == Role.SUPERADMIN).first()
                    if not exists:
                        su = User(
                            username=app.config.get('SUPERADMIN_USERNAME'),
                            email=app.config.get('SUPERADMIN_EMAIL'),
                            employee_id=app.config.get('SUPERADMIN_EMPLOYEE_ID'),
                            mobile=app.config.get('SUPERADMIN_MOBILE'),
                            is_active=True,
                            is_email_verified=True,
                            is_verified=True,
                            is_admin=True,
                            user_type=None,
                            created_at=datetime.now(timezone.utc)
                        )
                        su.set_password(superadmin_pwd)
                        db.session.add(su)
                        db.session.flush()
                        db.session.add(UserRole(user_id=su.id, role=Role.SUPERADMIN))
                        db.session.add(UserRole(user_id=su.id, role=Role.ADMIN))
                        db.session.commit()
                        app.logger.info("🚀 Superadmin user bootstrapped: %s (%s)", su.username, su.email)
                    else:
                        app.logger.info("Superadmin already present; bootstrap skipped")
                else:
                    app.logger.info("SUPERADMIN_PASSWORD not set; superadmin bootstrap disabled")
                
                # Admin user bootstrap (in development environment)
                if app.config.get('MY_ENVIRONMENT') == 'DEVELOPMENT':
                    admin_pwd = app.config.get('ADMIN_PASSWORD')
                    if admin_pwd:
                        admin_exists = User.query.join(UserRole).filter(UserRole.role == Role.ADMIN).filter(User.username == app.config.get('ADMIN_USERNAME')).first()
                        if not admin_exists:
                            admin_user = User(
                                username=app.config.get('ADMIN_USERNAME'),
                                email=app.config.get('ADMIN_EMAIL'),
                                employee_id=app.config.get('ADMIN_EMPLOYEE_ID'),
                                mobile=app.config.get('ADMIN_MOBILE'),
                                is_active=True,
                                is_email_verified=True,
                                is_verified=True,
                                is_admin=True,
                                user_type=None,
                                created_at=datetime.now(timezone.utc)
                            )
                            admin_user.set_password(admin_pwd)
                            db.session.add(admin_user)
                            db.session.flush()
                            db.session.add(UserRole(user_id=admin_user.id, role=Role.ADMIN))
                            db.session.commit()
                            app.logger.info("🚀 Admin user bootstrapped: %s (%s)", admin_user.username, admin_user.email)
                
                # Verifier user bootstrap (in development environment)
                if app.config.get('MY_ENVIRONMENT') == 'DEVELOPMENT':
                    verifier_pwd = app.config.get('VERIFIER_PASSWORD')
                    if verifier_pwd:
                        verifier_exists = User.query.join(UserRole).filter(UserRole.role == Role.VERIFIER).filter(User.username == app.config.get('VERIFIER_USERNAME')).first()
                        if not verifier_exists:
                            verifier_user = User(
                                username=app.config.get('VERIFIER_USERNAME'),
                                email=app.config.get('VERIFIER_EMAIL'),
                                employee_id=app.config.get('VERIFIER_EMPLOYEE_ID'),
                                mobile=app.config.get('VERIFIER_MOBILE'),
                                is_active=True,
                                is_email_verified=True,
                                is_verified=True,
                                is_admin=False,
                                user_type=None,
                                created_at=datetime.now(timezone.utc)
                            )
                            verifier_user.set_password(verifier_pwd)
                            db.session.add(verifier_user)
                            db.session.flush()
                            db.session.add(UserRole(user_id=verifier_user.id, role=Role.VERIFIER))
                            db.session.commit()
                            app.logger.info("🚀 Verifier user bootstrapped: %s (%s)", verifier_user.username, verifier_user.email)
                
                # Regular user bootstrap (in development environment)
                if app.config.get('MY_ENVIRONMENT') == 'DEVELOPMENT':
                    user_pwd = app.config.get('USER_PASSWORD')
                    if user_pwd:
                        user_exists = User.query.filter(User.username == app.config.get('USER_USERNAME')).first()
                        if not user_exists:
                            regular_user = User(
                                username=app.config.get('USER_USERNAME'),
                                email=app.config.get('USER_EMAIL'),
                                employee_id=app.config.get('USER_EMPLOYEE_ID'),
                                mobile=app.config.get('USER_MOBILE'),
                                is_active=True,
                                is_email_verified=True,
                                is_verified=True,
                                is_admin=False,
                                user_type=None,
                                created_at=datetime.now(timezone.utc)
                            )
                            regular_user.set_password(user_pwd)
                            db.session.add(regular_user)
                            db.session.flush()
                            db.session.add(UserRole(user_id=regular_user.id, role=Role.USER))
                            db.session.commit()
                            app.logger.info("🚀 Regular user bootstrapped: %s (%s)", regular_user.username, regular_user.email)
        except Exception as e:
            db.session.rollback()
            app.logger.exception("User bootstrap failed: %s", e)

    # ------------------------------------------------------------------
    # Protect SUPERADMIN role from accidental total removal
    # ------------------------------------------------------------------
    # @event.listens_for(db.session.__class__, "before_commit")
    # def _ensure_superadmin(session):  # pragma: no cover (simple guard)
    #     try:
    #         # Don't interfere with unit tests or bootstrap phases
    #         if app.config.get('TESTING'):
    #             return
    #         # Count current SUPERADMIN role rows (submitted state already flushed)
    #         remaining = UserRole.query.filter(UserRole.role == Role.SUPERADMIN).count()
    #         if remaining == 0:
    #             app.logger.error("❌ Attempt blocked: would remove last superadmin role")
    #             raise ValueError("cannot_remove_last_superadmin")
    #     except Exception as e:
    #         # Re-raise to abort commit if it's our sentinel value
    #         if str(e) == 'cannot_remove_last_superadmin':
    #             raise
    #         app.logger.exception("Error in superadmin protection hook: %s", e)

    try:
        register_blueprints(app)
        app.logger.info("Blueprints registered.")
    except Exception as e:
        app.logger.exception("Error registering blueprints: %s", e)

    # Ensure upload directory exists
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
        os.makedirs(upload_folder, exist_ok=True)
        app.logger.info("Upload folder ensured at: %s", upload_folder)
    except Exception as e:
        app.logger.warning("Failed to create upload folder: %s", e)

    # Favicon route to eliminate 404 /favicon.ico requests
    @app.route('/favicon.ico')
    @app.route('/favicon.ico')
    def favicon():
        static_dir = os.path.join(app.root_path, 'static')
        # Prefer root static/favicon.ico; fallback to images/favicon.ico
        if os.path.exists(os.path.join(static_dir, 'favicon.ico')):
            return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
        images_dir = os.path.join(static_dir, 'images')
        return send_from_directory(images_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    app.logger.info("✅ Flask app created successfully.")
    return app
