from marshmallow import fields
from marshmallow_enum import EnumField

from app.models.Cycle import Author
from app.extensions import ma


class AuthorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Author
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    name = fields.String(required=True)
    affiliation = fields.String(allow_none=True)
    email = fields.Email(allow_none=True)
    is_presenter = fields.Boolean()
    is_corresponding = fields.Boolean()