from marshmallow import fields, validate, post_load, EXCLUDE
from marshmallow_enum import EnumField

from app.models.User import User, Role
from app.models.enumerations import UserType
from app.extensions import ma
from .grading_schema import GradingSchema  # retained import if needed for other operations


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        unknown = EXCLUDE  # Ignore extra fields on load
        include_fk = True

    # Override fields that need special handling
    id = fields.String(dump_only=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    mobile = fields.String(required=True, validate=validate.Length(min=10))
    employee_id = fields.String(required=False, allow_none=True)
    user_type = EnumField(UserType, required=False, allow_none=True)
    
    # Roles handling
    roles = fields.List(
        fields.String(validate=validate.OneOf([r.value for r in Role])),
        required=True
    )
    
    # Auth & status
    password = fields.String(load_only=True, required=True)
    is_active = fields.Boolean(dump_only=True)
    is_admin = fields.Boolean(dump_only=True)
    is_email_verified = fields.Boolean(dump_only=True)
    last_login = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # OTP-related fields (only shown if explicitly needed)
    otp = fields.String(allow_none=True)
    otp_expiration = fields.DateTime(allow_none=True)
    failed_login_attempts = fields.Integer(dump_only=True)
    otp_resend_count = fields.Integer(dump_only=True)
    lock_until = fields.DateTime(dump_only=True)
    password_expiration = fields.DateTime(dump_only=True)
    last_password_change = fields.DateTime(dump_only=True)
    
    # Password reset fields
    reset_token_hash = fields.String(load_only=True, allow_none=True)
    reset_token_expires = fields.DateTime(load_only=True, allow_none=True)
    
    # Removed gradings nested relationship to prevent recursion depth during grading dumps
    # gradings = fields.Nested(GradingSchema, many=True, dump_only=True)

    @post_load
    def make_user(self, data, **kwargs):
        # Do not hash password here to avoid bypassing policy and double-hashing.
        # Route logic should call User.set_password() which enforces strength
        # and updates password metadata. We drop the plain password from the
        # deserialized payload so it isn't passed into the model constructor.
        if 'password' in data:
            data.pop('password', None)
        return data