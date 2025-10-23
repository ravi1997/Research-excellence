from marshmallow import fields
from marshmallow_enum import EnumField

from app.models.Cycle import CycleWindow
from app.extensions import ma


class CycleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = CycleWindow
        load_instance = True
        include_fk = True
        exclude = ['win']  # Exclude the DATERANGE field that marshmallow can't handle

    id = fields.String(dump_only=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)