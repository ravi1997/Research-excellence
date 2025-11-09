from marshmallow import Schema, fields
from app.extensions import ma
from app.models.Cycle import Grading


class GradingSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Grading
        load_instance = True
        include_fk = True
    """Minimal grading schema (no nested objects) to eliminate recursion and invalid excludes."""

    id = fields.UUID(dump_only=True)
    score = fields.Int(required=True)
    comments = fields.Str(required=False, allow_none=True)
    grading_type_id = fields.UUID(required=True)
    abstract_id = fields.UUID(required=False, allow_none=True)
    best_paper_id = fields.UUID(required=False, allow_none=True)
    award_id = fields.UUID(required=False, allow_none=True)
    graded_by_id = fields.UUID(required=True)
    verification_level = fields.Integer(dump_only=True)
    cycle_window_id = fields.UUID(dump_only=True, allow_none=True)
    graded_on = fields.DateTime(attribute="graded_on", dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    graded_by = fields.Method("get_graded_by", dump_only=True)
    grading_type = fields.Method("get_grading_type", dump_only=True)

    def get_graded_by(self, obj):
        user = getattr(obj, "graded_by", None)
        if not user:
            return None
        return {
            "id": str(getattr(user, "id", "")) if getattr(user, "id", None) else None,
            "username": getattr(user, "username", None),
            "email": getattr(user, "email", None),
            "full_name": getattr(user, "full_name", None),
        }

    def get_grading_type(self, obj):
        grading_type = getattr(obj, "grading_type", None)
        if not grading_type:
            return None
        return {
            "id": str(getattr(grading_type, "id", "")) if getattr(grading_type, "id", None) else None,
            "criteria": getattr(grading_type, "criteria", None),
            "min_score": getattr(grading_type, "min_score", None),
            "max_score": getattr(grading_type, "max_score", None),
            "grading_for": getattr(grading_type, "grading_for", None),
            "verification_level": getattr(grading_type, "verification_level", None),
        }
