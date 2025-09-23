from marshmallow import fields

from app.models.User import Department
from app.extensions import ma


class DepartmentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Department
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    name = fields.String(required=True)