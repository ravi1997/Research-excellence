from marshmallow import fields
from marshmallow_enum import EnumField

from app.models.Cycle import Cycle
from app.extensions import ma


class CycleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Cycle
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    name = fields.String(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)