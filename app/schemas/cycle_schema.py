from marshmallow import fields
from marshmallow_enum import EnumField

from app.models.Cycle import Cycle, CycleWindow
from app.models.enumerations import CyclePhase
from app.extensions import ma


class CycleWindowSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CycleWindow
        load_instance = True
        include_fk = True
        exclude = ['win']  # Exclude the DATERANGE field that marshmallow can't handle

    id = fields.String(dump_only=True)
    phase = fields.String(required=True)  # Using String to allow for the enum values
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    cycle_id = fields.String(required=True)


class CycleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Cycle
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    name = fields.String(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    windows = fields.Nested(CycleWindowSchema, many=True, dump_only=True)