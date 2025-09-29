from marshmallow import Schema, fields


class GradingSchema(Schema):
    """Minimal grading schema (no nested objects) to eliminate recursion and invalid excludes."""

    id = fields.UUID(dump_only=True)
    score = fields.Int(required=True)
    comments = fields.Str(required=False, allow_none=True)
    grading_type_id = fields.UUID(required=True)
    abstract_id = fields.UUID(required=False, allow_none=True)
    best_paper_id = fields.UUID(required=False, allow_none=True)
    award_id = fields.UUID(required=False, allow_none=True)
    graded_by_id = fields.UUID(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)