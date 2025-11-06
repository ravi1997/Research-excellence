import uuid
from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.String(64), nullable=True)  # actor
    target_user_id = db.Column(db.String(64), nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    detail = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        # Ensure detail is properly formatted for JSON serialization
        detail = self.detail
        if detail and isinstance(detail, str):
            # If detail is a string representation of JSON, make sure it's valid
            try:
                # If it's already a JSON string, return as is
                import json
                json.loads(detail)  # This will raise an exception if not valid JSON
            except (ValueError, TypeError):
                # If it's not valid JSON, treat as a plain string
                pass
        
        return {
            'id': self.id,
            'event': self.event,
            'user_id': self.user_id,
            'target_user_id': self.target_user_id,
            'ip': self.ip,
            'detail': detail,
            'created_at': self.created_at.isoformat(),
        }
    
    @staticmethod
    def validate_detail_format(detail):
        """
        Validate and ensure the detail field is in proper format for storage.
        If it's an object, convert to JSON string. If it's already a string,
        ensure it's valid JSON.
        """
        import json
        
        if detail is None:
            return None
        elif isinstance(detail, str):
            # Check if it's already a valid JSON string
            try:
                json.loads(detail)
                return detail  # Already valid JSON
            except (ValueError, TypeError):
                # It's a string but not valid JSON, so return as is
                return detail
        else:
            # It's a Python object, convert to JSON string
            try:
                return json.dumps(detail)
            except (TypeError, ValueError):
                # If it can't be converted to JSON, convert to string representation
                return str(detail)
