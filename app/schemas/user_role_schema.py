from marshmallow import fields
from marshmallow_enum import EnumField

from app.models.User import UserRole, Role
from app.extensions import ma


class UserRoleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = UserRole
        load_instance = True
        include_fk = True

    user_id = fields.String(required=True)
    role = EnumField(Role, required=True)