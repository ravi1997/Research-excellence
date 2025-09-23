from marshmallow import fields

from app.models.Token import Token
from app.extensions import ma


class TokenSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Token
        load_instance = True
        include_fk = True

    id = fields.Integer(dump_only=True)
    token_type = fields.String(required=True)
    user_id = fields.String(allow_none=True)
    token_hash = fields.String(allow_none=True)
    revoked = fields.Boolean()
    replaced_by_id = fields.Integer(allow_none=True)
    user_agent = fields.String(allow_none=True)
    ip_address = fields.String(allow_none=True)
    jti = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    expires_at = fields.DateTime(required=True)