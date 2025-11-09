from marshmallow import fields

from app.models.Cycle import Category
from app.extensions import ma


class CategorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Category
        load_instance = True
        include_fk = True

    id = fields.String(dump_only=True)
    name = fields.String(required=True)
    users = fields.Method("get_users", dump_only=True)

    def get_users(self, obj):
        """Return a lightweight view of users mapped to this category."""
        primary_users = getattr(obj, "primary_users", None) or []
        multi_users = getattr(obj, "users", None) or []
        combined = list(multi_users) + list(primary_users)

        seen = set()
        user_list = []
        for user in combined:
            if not user:
                continue
            user_id = getattr(user, "id", None)
            if user_id in seen:
                continue
            seen.add(user_id)
            user_list.append(
                {
                    "id": str(user_id) if user_id else None,
                    "username": getattr(user, "username", None),
                    "email": getattr(user, "email", None),
                }
            )
        return user_list
