from marshmallow import Schema, fields, validate
from app.extensions import ma
from app.models.Cycle import GradingType

class GradingTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = GradingType
        load_instance = True
        include_fk = True
    id = fields.UUID(dump_only=True)
    criteria = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    min_score = fields.Int(required=True)
    max_score = fields.Int(required=True)
    grading_for = fields.Str(required=True, validate=validate.OneOf(
        choices=['abstract', 'best_paper', 'award']
    ))

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    # Omit gradings back reference to avoid recursion (can be added via dedicated endpoint if needed)