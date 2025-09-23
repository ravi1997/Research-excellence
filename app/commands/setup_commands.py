import click
from flask import current_app
from flask.cli import with_appcontext
from flask_migrate import upgrade as alembic_upgrade, stamp as alembic_stamp
from app.extensions import db
from app.models.User import User, UserRole
from app.models.enumerations import Role
from sqlalchemy import inspect as sa_inspect


def create_user_if_not_exists(username, email, employee_id, mobile, password, roles):
    """Create a user with specified roles if they don't already exist."""
    try:
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            click.echo(f"ℹ User '{username}' already exists, skipping creation")
            return existing_user

        # Create new user
        user = User(
            username=username,
            email=email,
            employee_id=employee_id,
            mobile=mobile,
            is_active=True,
            is_email_verified=True,
            is_verified=True,
            is_admin='admin' in [r.value for r in roles],
            user_type=None
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.flush()  # Get the user ID without committing
        
        # Add roles
        for role in roles:
            user_role = UserRole(user_id=user.id, role=role)
            db.session.add(user_role)
        
        db.session.commit()
        click.echo(f"✔ Created user '{username}' with roles: {[r.value for r in roles]}")
        return user
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning(f"Failed to create user '{username}': {e}")
        click.echo(f"⚠ Failed to create user '{username}': {e}")
        return None


@click.command("setup")
@click.option("--reindex/--no-reindex", default=True, help="Rebuild FTS vectors after migrations (PostgreSQL only)")
@click.option("--create-unaccent/--no-create-unaccent", default=True, help="Ensure unaccent extension (PostgreSQL only)")
@click.option("--create-superadmin/--no-create-superadmin", default=True, help="Create superadmin if none exists (uses env or provided password)")
@click.option("--create-admin/--no-create-admin", default=True, help="Create admin user (development environment)")
@click.option("--create-verifier/--no-create-verifier", default=True, help="Create verifier user (development environment)")
@click.option("--create-user/--no-create-user", default=True, help="Create regular user (development environment)")
@click.option("--create-viewer/--no-create-viewer", default=True, help="Create viewer user (development environment)")
@click.option("--superadmin-password", default=None, help="Superadmin password (falls back to SUPERADMIN_PASSWORD env)")
@click.option("--admin-password", default=None, help="Admin password (falls back to ADMIN_PASSWORD env)")
@click.option("--verifier-password", default=None, help="Verifier password (falls back to VERIFIER_PASSWORD env)")
@click.option("--user-password", default=None, help="User password (falls back to USER_PASSWORD env)")
@click.option("--viewer-password", default=None, help="Viewer password (falls back to VIEWER_PASSWORD env)")
@with_appcontext
def setup_command(reindex: bool, create_unaccent: bool, create_superadmin: bool, 
                  create_admin: bool, create_verifier: bool, create_user: bool, create_viewer: bool,
                  superadmin_password: str | None, admin_password: str | None, 
                  verifier_password: str | None, user_password: str | None, viewer_password: str | None):
    """One-shot project setup for fresh systems.

    - Upgrades DB schema to head (Alembic)
    - Ensures unaccent extension (PostgreSQL)
    - Creates user accounts from config if they don't exist
    - Rebuilds videos.search_vec for all rows (PostgreSQL)

    Safe to run multiple times; all steps are idempotent.
    """
    engine = db.engine
    engine_name = getattr(engine, 'name', '').lower()
    current_app.logger.info("setup: starting (engine=%s)", engine_name)

    # 1) Ensure Postgres unaccent extension (if requested)
    if engine_name == 'postgresql' and create_unaccent:
        try:
            with engine.begin() as conn:
                conn.execute(db.text("CREATE EXTENSION IF NOT EXISTS unaccent"))
            click.echo("✔ unaccent extension ensured")
        except Exception as e:
            # Non-fatal: migrations may still run; surface message
            current_app.logger.warning("setup: could not create unaccent: %s", e)
            click.echo(f"⚠ Could not create unaccent extension: {e}")

    # 2) Upgrade schema to head
    try:
        # Detect inconsistent stamp (alembic_version at head but tables missing)
        try:
            insp = sa_inspect(db.engine)
            tables = set(insp.get_table_names())
        except Exception:
            tables = set()

        if ('users' not in tables or 'user_roles' not in tables) and 'alembic_version' in tables:
            # Likely a fresh DB with only alembic_version stamped incorrectly.
            click.echo('ℹ Detected stale stamp without tables; re-stamping to base then upgrading')
            alembic_stamp(revision='base')  # reset revision without modifying schema
            alembic_upgrade()
        else:
            alembic_upgrade()  # uses Flask-Migrate configured context
        click.echo("✔ Database upgraded to head")
    except Exception as e:
        current_app.logger.exception('setup: migration failed: %s', e)
        raise click.ClickException(f"Migration failed: {e}")

    # 3) Create superadmin user
    if create_superadmin:
        try:
            pwd = superadmin_password or current_app.config.get('SUPERADMIN_PASSWORD')
            if pwd:
                existing_superadmin = User.query.join(UserRole).filter(UserRole.role == Role.SUPERADMIN).first()
                if not existing_superadmin:
                    create_user_if_not_exists(
                        current_app.config.get('SUPERADMIN_USERNAME', 'superadmin'),
                        current_app.config.get('SUPERADMIN_EMAIL', 'superadmin@example.com'),
                        current_app.config.get('SUPERADMIN_EMPLOYEE_ID', 'SUPER001'),
                        current_app.config.get('SUPERADMIN_MOBILE', '9000000000'),
                        pwd,
                        [Role.SUPERADMIN, Role.ADMIN]
                    )
                    click.echo("✔ Superadmin created")
                else:
                    click.echo("ℹ Superadmin already exists, skipping creation")
            else:
                click.echo("ℹ SUPERADMIN_PASSWORD not provided; skipping superadmin creation")
        except Exception as e:
            current_app.logger.warning('setup: superadmin creation skipped/failed: %s', e)
            click.echo(f"⚠ Superadmin creation skipped/failed: {e}")

    # 4) Create admin user (in development environment)
    if create_admin and current_app.config.get('MY_ENVIRONMENT') == 'DEVELOPMENT':
        try:
            pwd = admin_password or current_app.config.get('ADMIN_PASSWORD')
            if pwd:
                existing_admin = User.query.join(UserRole).filter(UserRole.role == Role.ADMIN).filter(
                    User.username == current_app.config.get('ADMIN_USERNAME', 'admin')
                ).first()
                if not existing_admin:
                    create_user_if_not_exists(
                        current_app.config.get('ADMIN_USERNAME', 'admin'),
                        current_app.config.get('ADMIN_EMAIL', 'admin@example.com'),
                        current_app.config.get('ADMIN_EMPLOYEE_ID', 'ADMIN001'),
                        current_app.config.get('ADMIN_MOBILE', '9000000001'),
                        pwd,
                        [Role.ADMIN]
                    )
                    click.echo("✔ Admin user created")
                else:
                    click.echo("ℹ Admin user already exists, skipping creation")
            else:
                click.echo("ℹ ADMIN_PASSWORD not provided; skipping admin user creation")
        except Exception as e:
            current_app.logger.warning('setup: admin user creation skipped/failed: %s', e)
            click.echo(f"⚠ Admin user creation skipped/failed: {e}")

    # 5) Create verifier user (in development environment)
    if create_verifier and current_app.config.get('MY_ENVIRONMENT') == 'DEVELOPMENT':
        try:
            pwd = verifier_password or current_app.config.get('VERIFIER_PASSWORD')
            if pwd:
                existing_verifier = User.query.join(UserRole).filter(UserRole.role == Role.VERIFIER).filter(
                    User.username == current_app.config.get('VERIFIER_USERNAME', 'verifier')
                ).first()
                if not existing_verifier:
                    create_user_if_not_exists(
                        current_app.config.get('VERIFIER_USERNAME', 'verifier'),
                        current_app.config.get('VERIFIER_EMAIL', 'verifier@example.com'),
                        current_app.config.get('VERIFIER_EMPLOYEE_ID', 'VERIF001'),
                        current_app.config.get('VERIFIER_MOBILE', '9000000003'),
                        pwd,
                        [Role.VERIFIER]
                    )
                    click.echo("✔ Verifier user created")
                else:
                    click.echo("ℹ Verifier user already exists, skipping creation")
            else:
                click.echo("ℹ VERIFIER_PASSWORD not provided; skipping verifier user creation")
        except Exception as e:
            current_app.logger.warning('setup: verifier user creation skipped/failed: %s', e)
            click.echo(f"⚠ Verifier user creation skipped/failed: {e}")

    # 6) Create regular user (in development environment)
    if create_user and current_app.config.get('MY_ENVIRONMENT') == 'DEVELOPMENT':
        try:
            pwd = user_password or current_app.config.get('USER_PASSWORD')
            if pwd:
                existing_user = User.query.filter(User.username == current_app.config.get('USER_USERNAME', 'user')).first()
                if not existing_user:
                    create_user_if_not_exists(
                        current_app.config.get('USER_USERNAME', 'user'),
                        current_app.config.get('USER_EMAIL', 'user@example.com'),
                        current_app.config.get('USER_EMPLOYEE_ID', 'USER001'),
                        current_app.config.get('USER_MOBILE', '9000000002'),
                        pwd,
                        [Role.USER, Role.VIEWER]
                    )
                    click.echo("✔ Regular user created")
                else:
                    click.echo("ℹ Regular user already exists, skipping creation")
            else:
                click.echo("ℹ USER_PASSWORD not provided; skipping regular user creation")
        except Exception as e:
            current_app.logger.warning('setup: regular user creation skipped/failed: %s', e)
            click.echo(f"⚠ Regular user creation skipped/failed: {e}")

    # 7) Create viewer user (in development environment)
    if create_viewer and current_app.config.get('MY_ENVIRONMENT') == 'DEVELOPMENT':
        try:
            pwd = viewer_password or current_app.config.get('VIEWER_PASSWORD')
            if pwd:
                existing_viewer = User.query.join(UserRole).filter(UserRole.role == Role.VIEWER).filter(
                    User.username == current_app.config.get('VIEWER_USERNAME', 'viewer')
                ).first()
                if not existing_viewer:
                    create_user_if_not_exists(
                        current_app.config.get('VIEWER_USERNAME', 'viewer'),
                        current_app.config.get('VIEWER_EMAIL', 'viewer@example.com'),
                        current_app.config.get('VIEWER_EMPLOYEE_ID', 'VIEW001'),
                        current_app.config.get('VIEWER_MOBILE', '9000000004'),
                        pwd,
                        [Role.VIEWER]
                    )
                    click.echo("✔ Viewer user created")
                else:
                    click.echo("ℹ Viewer user already exists, skipping creation")
            else:
                click.echo("ℹ VIEWER_PASSWORD not provided; skipping viewer user creation")
        except Exception as e:
            current_app.logger.warning('setup: viewer user creation skipped/failed: %s', e)
            click.echo(f"⚠ Viewer user creation skipped/failed: {e}")

    # 8) Reindex FTS vectors (optional; Postgres only)
    if reindex and engine_name == 'postgresql':
        try:
            with engine.begin() as conn:
                res = conn.execute(db.text(
                    """
                    UPDATE videos v
                    SET search_vec = compute_video_search_vec(v.uuid, v.title, v.description, v.transcript, v.category_id)
                    """
                ))
                click.echo(f"✔ Reindexed videos.search_vec (rowcount={getattr(res, 'rowcount', '?')})")
        except Exception as e:
            # Non-fatal; keep setup overall successful
            current_app.logger.warning('setup: reindex failed: %s', e)
            click.echo(f"⚠ Reindex failed: {e}")

    click.echo("✅ Setup complete")
