from marshmallow import fields

from app.models.Cycle import PaperCategory
from app.extensions import ma


class PaperCategorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PaperCategory
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    name = fields.String(required=True)