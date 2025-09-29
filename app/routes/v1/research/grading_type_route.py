from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import String, cast, func
from app.routes.v1.research import research_bp
from app.models.Cycle import GradingType
from app.schemas.grading_type_schema import GradingTypeSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role

grading_type_schema = GradingTypeSchema()
grading_types_schema = GradingTypeSchema(many=True)

@research_bp.route('/grading-types', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_grading_type():
    """Create a new grading type."""
    try:
        data = request.get_json()
        grading_type = grading_type_schema.load(data)
        db.session.add(grading_type)
        db.session.commit()
        return jsonify(grading_type_schema.dump(grading_type)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating grading type")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/grading-types', methods=['GET'])
@jwt_required()
def get_grading_types():
    """Get all grading types."""
    try:
        # Get query parameters for filtering
        grading_for = request.args.get('grading_for', '').strip().lower()
        
        query = GradingType.query
        
        if grading_for:
            query = query.filter(
                func.lower(cast(GradingType.grading_for, String)) == grading_for.lower()
            )
        
        grading_types = query.all()
        return jsonify(grading_types_schema.dump(grading_types)), 200
    except Exception as e:
        current_app.logger.exception("Error getting grading types")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/grading-types/<grading_type_id>', methods=['GET'])
@jwt_required()
def get_grading_type(grading_type_id):
    """Get a specific grading type."""
    grading_type = GradingType.query.get_or_404(grading_type_id)
    return jsonify(grading_type_schema.dump(grading_type)), 200

@research_bp.route('/grading-types/<grading_type_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_grading_type(grading_type_id):
    """Update a grading type."""
    grading_type = GradingType.query.get_or_404(grading_type_id)
    try:
        data = request.get_json()
        grading_type = grading_type_schema.load(data, instance=grading_type, partial=True)
        db.session.commit()
        return jsonify(grading_type_schema.dump(grading_type)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating grading type")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/grading-types/<grading_type_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_grading_type(grading_type_id):
    """Delete a grading type."""
    grading_type = GradingType.query.get_or_404(grading_type_id)
    try:
        db.session.delete(grading_type)
        db.session.commit()
        return jsonify({"message": "Grading type deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting grading type")
        return jsonify({"error": str(e)}), 400