from marshmallow import fields

from app.models.AuditLog import AuditLog
from app.extensions import ma


class AuditLogSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = AuditLog
        load_instance = True
        include_fk = True

    id = fields.Integer(dump_only=True)
    event = fields.String(required=True)
    user_id = fields.String(allow_none=True)
    target_user_id = fields.String(allow_none=True)
    ip = fields.String(allow_none=True)
    detail = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)