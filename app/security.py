from flask import jsonify, redirect, request, url_for
from flask_jwt_extended import JWTManager
from app.models import Token
from app.models.User import User
from app.extensions import db
from uuid import UUID
from datetime import datetime, timezone

def init_jwt_callbacks(jwt: JWTManager):
    @jwt.token_in_blocklist_loader
    def is_revoked(jwt_header, jwt_payload):  # pragma: no cover
        jti = jwt_payload.get("jti")
        # Consider token blocked if a block entry exists and not expired
        if not jti:
            return False
        now = datetime.now(timezone.utc)
        q = Token.query.filter(Token.token_type == 'block', Token.jti == jti, Token.expires_at > now)
        return q.first() is not None

    @jwt.additional_claims_loader
    def add_claims(identity):  # pragma: no cover
        # Coerce string UUID identities for SQLite tests / cross-dialect safety
        ident = identity
        if isinstance(identity, str):
            try:
                ident = UUID(identity)
            except Exception:
                ident = identity
        user = db.session.get(User, ident)
        if not user:
            return {}
        return {"roles": [r.value for r in user.roles]}
    # ==== helpers for consistent behavior ====

    def _wants_html() -> bool:
        # Prefer HTML if the client accepts it over JSON, and body isn’t marked JSON
        best = request.accept_mimetypes.best_match(
            ["text/html", "application/json"])
        return best == "text/html" and not request.is_json

    def _login_url() -> str:
        # Preserve destination for GET; for non-GET we drop querystring to avoid replaying unsafe methods
        next_param = request.full_path if request.method == "GET" else request.path
        # Avoid loops if we’re already on the login route
        try:
            login_url = url_for("view_bp.login_page", next=next_param)
        except Exception:
            login_url = "/login"
        return login_url

    def _redirect_to_login():
        if _wants_html():
            # 303 “See Other” so browsers switch to GET on the login page
            return redirect(_login_url(), code=303)
        # API/JS clients: return a structured 401 the frontend can handle
        return jsonify({
            "error": "auth_required",
            "message": "Please log in",
            "redirect": _login_url()
        }), 401

    # ==== JWT error/edge loaders ====
    @jwt.unauthorized_loader
    def _missing_token(err_msg):
        return _redirect_to_login()

    @jwt.expired_token_loader
    def _expired_token(jwt_header, jwt_payload):
        return _redirect_to_login()

    @jwt.invalid_token_loader
    def _invalid_token(err_msg):
        return _redirect_to_login()

    @jwt.revoked_token_loader
    def _revoked_token(jwt_header, jwt_payload):
        return _redirect_to_login()

    @jwt.needs_fresh_token_loader
    def _needs_fresh(jwt_header, jwt_payload):
        return _redirect_to_login()
