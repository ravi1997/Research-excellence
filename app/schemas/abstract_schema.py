from marshmallow import fields
from marshmallow_enum import EnumField

from app.models.Cycle import Abstracts, Status
from app.extensions import ma
from .category_schema import CategorySchema
from .author_schema import AuthorSchema
from .user_schema import UserSchema
from .grading_schema import GradingSchema


class AbstractSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Abstracts
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    title = fields.String(required=True)
    content = fields.String(required=True)
    category_id = fields.String(required=True)
    cycle_id = fields.String(required=True)
    status = fields.String(required=False)
    pdf_path = fields.String(dump_only=True)
    created_by = fields.Nested(UserSchema, dump_only=True)
    updated_by = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Related fields
    category = fields.Nested(CategorySchema, dump_only=True)
    authors = fields.Nested(AuthorSchema, many=True, dump_only=True)
    verifiers = fields.Nested(UserSchema, many=True, dump_only=True)
    gradings = fields.Nested(GradingSchema, many=True, dump_only=True)
    