from marshmallow import fields

from app.models.User import UserSettings
from app.extensions import ma


class UserSettingsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = UserSettings
        load_instance = True
        include_fk = True

    user_id = fields.String(dump_only=True)
    theme = fields.String(allow_none=True)
    video_quality = fields.String(allow_none=True)
    video_speed = fields.String(allow_none=True)
    auto_play = fields.Boolean()
    auto_next = fields.Boolean()
    captions = fields.Boolean()
    sidebar_collapsed = fields.Boolean()
    last_viewed_section = fields.String(allow_none=True)