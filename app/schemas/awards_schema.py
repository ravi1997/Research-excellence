from marshmallow import fields
from marshmallow_enum import EnumField

from app.models.Cycle import Awards, Status
from app.extensions import ma


class AwardsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Awards
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    title = fields.String(required=True)
    author_id = fields.String(required=True)
    category_id = fields.String(required=True)
    paper_category_id = fields.String(required=True)
    cycle_id = fields.String(required=True)
    forwarding_letter_path = fields.String(allow_none=True)
    full_paper_path = fields.String(allow_none=True)
    is_aiims_work = fields.Boolean()
    status = EnumField(Status, required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)