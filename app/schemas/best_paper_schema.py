from marshmallow import fields
from marshmallow_enum import EnumField

from app.models.Cycle import BestPaper, Status
from app.extensions import ma
from app.schemas.author_schema import AuthorSchema
from app.schemas.paper_category_schema import PaperCategorySchema
from app.schemas.user_schema import UserSchema
from .grading_schema import GradingSchema  # keep import if needed elsewhere


class BestPaperSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = BestPaper
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    title = fields.String(required=True)
    author_id = fields.String(required=True)
    paper_category_id = fields.String(required=True)
    cycle_id = fields.String(required=True)
    forwarding_letter_path = fields.String(allow_none=True)
    full_paper_path = fields.String(allow_none=True)
    is_aiims_work = fields.Boolean()
    status = EnumField(Status, required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    # Removed to avoid recursion cycles
    # gradings = fields.Nested(GradingSchema, many=True, dump_only=True)
    
    author = fields.Nested(AuthorSchema, dump_only=True)
    verifiers = fields.Nested(UserSchema, many=True, dump_only=True)
    gradings = fields.Nested(GradingSchema, many=True, dump_only=True)
    paper_category = fields.Nested(PaperCategorySchema, dump_only=True)
    created_by = fields.Nested(UserSchema, dump_only=True)
    updated_by = fields.Nested(UserSchema, dump_only=True)