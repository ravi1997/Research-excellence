# models/user.py

import uuid
import bcrypt
import logging
import secrets
import hashlib
from enum import Enum
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Enum as SqlEnum, Table, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from flask import current_app

from app.models.enumerations import Role, UserType
from app.models.Cycle import user_categories
from app.security_utils import password_strong
from app.utils.generators import generate_strong_password
from app.utils.services.sms import send_sms

from ..extensions import db

logger = logging.getLogger("auth")

# --- Constants ---
MAX_FAILED_ATTEMPTS = 5
MAX_OTP_RESENDS = 5
LOCK_DURATION_HOURS = 24
PASSWORD_EXPIRATION_DAYS = 90

# --- Association Table for User Roles ---

class UserRole(db.Model):
    __tablename__ = "user_roles"
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        "users.id"), primary_key=True)
    role = db.Column(SqlEnum(Role), nullable=False, primary_key=True)

    user = db.relationship("User", back_populates="role_associations")


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(100), nullable=False, unique=True)
    users = db.relationship("User", back_populates="department")


class UserSettings(db.Model):
    __tablename__ = "user_settings"
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), primary_key=True)
    theme = db.Column(db.String(20), nullable=True)  # 'light', 'dark', 'system'
    video_quality = db.Column(db.String(20), nullable=True)  # 'auto', '480p', '720p', '1080p'
    video_speed = db.Column(db.String(10), nullable=True)  # '0.5x', '1x', '1.25x', '1.5x', '2x'
    auto_play = db.Column(db.Boolean, default=False)
    auto_next = db.Column(db.Boolean, default=True)
    captions = db.Column(db.Boolean, default=False)
    
    # Navigation preferences
    sidebar_collapsed = db.Column(db.Boolean, default=False)
    last_viewed_section = db.Column(db.String(50), nullable=True)
    
    user = db.relationship("User", backref=db.backref("settings", uselist=False))


# --- User Model ---

class User(db.Model):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=False)
    email = Column(String(120), unique=True)
    employee_id = Column(String(30), unique=True)
    mobile = Column(String(15), unique=True)

    
    designation = Column(String(500), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=True)
    department = relationship("Department", back_populates="users")

    affiliation = Column(String(500), nullable=True)
    
    # user_type indicates 'employee' or 'general'
    user_type = Column(SqlEnum(UserType), nullable=True, default=UserType.EMPLOYEE.value)

    password_hash = Column(String(255))
    password_expiration = Column(DateTime)

    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    # Has admin verified this account (document verified)
    is_verified = Column(Boolean, default=False)
    # Has the user uploaded their employee ID document
    document_submitted = Column(Boolean, default=False)
    # Force user to change password at next login (e.g., after admin unlock reset)
    require_password_change = Column(Boolean, default=False)

    failed_login_attempts = Column(Integer, default=0)
    otp_resend_count = Column(Integer, default=0)
    lock_until = Column(DateTime)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(
        timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_password_change = Column(DateTime, nullable=True)
    otp = Column(String(6))
    otp_expiration = Column(DateTime)
    # Password reset support
    reset_token_hash = Column(String(128))
    reset_token_expires = Column(DateTime)

    # --- Relationships ---
    role_associations = db.relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan")
    roles = association_proxy("role_associations", "role")
    
    abstracts_submitted = db.relationship(
        "Abstracts",
        foreign_keys="Abstracts.created_by_id",
        back_populates="created_by",
        lazy=True,
    )
    abstracts_updated = db.relationship(
        "Abstracts",
        foreign_keys="Abstracts.updated_by_id",
        back_populates="updated_by",
        lazy=True,
    )
    awards_submitted = db.relationship(
        "Awards",
        foreign_keys="Awards.created_by_id",
        back_populates="created_by",
        lazy=True,
    )
    awards_updated = db.relationship(
        "Awards",
        foreign_keys="Awards.updated_by_id",
        back_populates="updated_by",
        lazy=True,
    )
    best_papers_submitted = db.relationship(
        "BestPaper",
        foreign_keys="BestPaper.created_by_id",
        back_populates="created_by",
        lazy=True,
    )
    best_papers_updated = db.relationship(
        "BestPaper",
        foreign_keys="BestPaper.updated_by_id",
        back_populates="updated_by",
        lazy=True,
    )
    abstracts_to_coordinate = db.relationship(
        "Abstracts",
        secondary="abstract_coordinators",
        back_populates="coordinators",
    )
    awards_to_coordinate = db.relationship(
        "Awards",
        secondary="award_coordinators",
        back_populates="coordinators",
    )
    best_papers_to_coordinate = db.relationship(
        "BestPaper",
        secondary="best_paper_coordinators",
        back_populates="coordinators",
    )
    grades_given = db.relationship(
        "Grading",
        back_populates="graded_by",
        lazy=True,
    )

    # Relationship to abstracts that this user can verify
    abstracts_to_verify = db.relationship(
        "Abstracts", secondary="abstract_verifiers", back_populates="verifiers")

    awards_to_verify = db.relationship(
        "Awards", secondary="award_verifiers", back_populates="verifiers")
    best_papers_to_verify = db.relationship(
        "BestPaper", secondary="best_paper_verifiers", back_populates="verifiers")

    category_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("categories.id"),
        nullable=True,
    )
    category = db.relationship("Category", back_populates="primary_users")
    categories = db.relationship(
        "Category",
        secondary=user_categories,
        back_populates="users",
        lazy=True,
    )

    # --- Security Methods ---

    def is_locked(self) -> bool:
        return self.lock_until and datetime.now(timezone.utc) < self.lock_until.replace(tzinfo=timezone.utc)

    def lock_account(self):
        self.lock_until = datetime.now(
            timezone.utc) + timedelta(hours=LOCK_DURATION_HOURS)
        logger.warning(f"User {self.id} locked until {self.lock_until}")

    def unlock_account(self):
        self.lock_until = None
        self.failed_login_attempts = 0
        self.otp_resend_count = 0

        temp_password = generate_strong_password(8)
        self.set_password(temp_password)
        send_sms(
            self.mobile, f"Your account has been unlocked. Temporary password: {temp_password}. Please login and change it immediately.")
        self.require_password_change = True
        logger.info(f"User {self.id} manually unlocked")

    def increment_failed_logins(self):
        if self.is_locked():
            return
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            self.lock_account()

    def reset_failed_logins(self):
        self.failed_login_attempts = 0

    def resend_otp(self):
        if self.is_locked():
            return
        self.otp_resend_count += 1
        if self.otp_resend_count >= MAX_OTP_RESENDS:
            self.lock_account()

    def set_otp(self, otp_code: str, ttl_minutes: int = 5):
        self.otp = otp_code
        self.otp_expiration = datetime.now(
            timezone.utc) + timedelta(minutes=ttl_minutes)
        self.otp_resend_count = 0

    def verify_otp(self, code: str) -> bool:
        current_app.logger.info(
            f"Verifying OTP for user {self.id}. Provided: {code}, Expected: {self.otp}")
        if self.is_locked():
            current_app.logger.warning(
                f"OTP verification failed: user {self.id} is locked.")
            return False

        otp_exp = self.otp_expiration
        if otp_exp and otp_exp.tzinfo is None:
            otp_exp = otp_exp.replace(tzinfo=timezone.utc)

        if not otp_exp or otp_exp <= datetime.now(timezone.utc):
            return False

        if self.otp != code:
            return False

        return True

    def set_password(self, raw_password: str):
        if not password_strong(raw_password):
            raise ValueError("Password does not meet complexity requirements")
        salt = bcrypt.gensalt()
        # Hash & set password metadata
        self.password_hash = bcrypt.hashpw(raw_password.encode(), salt).decode()
        self.password_expiration = datetime.now(timezone.utc) + timedelta(days=PASSWORD_EXPIRATION_DAYS)
        self.last_password_change = datetime.now(timezone.utc)

    def check_password(self, raw_password: str) -> bool:
        try:
            return bcrypt.checkpw(raw_password.encode(), self.password_hash.encode())
        except Exception:
            return False

    # --- Password Reset Helpers ---
    def generate_reset_token(self, ttl_minutes: int = 30) -> str:
        """Generate a secure token, store its hash & expiry, return the plaintext token."""
        token = secrets.token_urlsafe(8)
        self.reset_token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        return token

    def verify_reset_token(self, token: str) -> bool:
        if not token or not self.reset_token_hash or not self.reset_token_expires:
            return False
        exp = self.reset_token_expires
        # Normalize to UTC if stored naive
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= datetime.now(timezone.utc):
            return False
        return hashlib.sha256(token.encode()).hexdigest() == self.reset_token_hash

    def clear_reset_token(self):
        self.reset_token_hash = None
        self.reset_token_expires = None

    def is_password_expired(self) -> bool:
        if not self.password_expiration:
            return False
        exp = self.password_expiration
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp

    # --- Roles ---

    def has_role(self, role: str) -> bool:
        return role in [r.value for r in self.roles]

    def is_superadmin_check(self) -> bool:
        return Role.SUPERADMIN in [r for r in self.roles]

    def is_admin_check(self) -> bool:
        return Role.ADMIN in [r for r in self.roles] or self.is_superadmin_check()

    # --- Authentication (Static) ---

    @staticmethod
    def authenticate(identifier: str, password: str):
        user = User.query.filter(
            User.user_type == UserType.EMPLOYEE,
            User.is_active == True,
            User.is_verified == True,
            db.or_(
                User.username == identifier,
                User.email == identifier,
                User.employee_id == identifier
            )
        ).first()

        if not user or user.is_locked() or not user.check_password(password) or user.is_password_expired():
            if user:
                user.increment_failed_logins()
            return None

        user.last_login = datetime.now(timezone.utc)
        user.reset_failed_logins()
        db.session.commit()
        return user

    @staticmethod
    def authenticate_with_otp(mobile: str, otp_code: str):
        user = User.query.filter_by(mobile=mobile, is_active=True).first()

        if not user or user.is_locked() or not user.verify_otp(otp_code):
            if user:
                user.increment_failed_logins()
            return None

        user.last_login = datetime.now(timezone.utc)
        user.reset_failed_logins()
        db.session.commit()
        return user

    # --- Serialization ---

    def to_dict(self, include_sensitive=False):
        def iso_or_none(dt):
            return dt.isoformat() if dt else None

        data = {
            'id': str(self.id),
            'user_type': self.user_type,
            'username': self.username,
            'email': self.email,
            'employee_id': self.employee_id,
            'mobile': self.mobile,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'is_email_verified': self.is_email_verified,
            'is_verified': self.is_verified,
            'document_submitted': self.document_submitted,
            'require_password_change': self.require_password_change,
            'roles': [r.value for r in self.roles],
            'failed_login_attempts': self.failed_login_attempts,
            'otp_resend_count': self.otp_resend_count,
            'lock_until': iso_or_none(self.lock_until),
            'created_at': iso_or_none(self.created_at),
            'updated_at': iso_or_none(self.updated_at),
            'last_login': iso_or_none(self.last_login),
            'password_expiration': iso_or_none(self.password_expiration),
            'last_password_change': iso_or_none(self.last_password_change),
        }

        if include_sensitive:
            data.update({
                'password_hash': self.password_hash,
                'otp': self.otp,
                'otp_expiration': iso_or_none(self.otp_expiration),
            })

        return data

    def __str__(self):
        return f"<User(username='{self.username}', type='{self.user_type}')>"
