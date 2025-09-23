from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.routes.v1.research import research_bp
from app.models.Cycle import Cycle
from app.schemas.cycle_schema import CycleSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role

cycle_schema = CycleSchema()
cycles_schema = CycleSchema(many=True)

@research_bp.route('/cycles', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_cycle():
    """Create a new research cycle."""
    try:
        data = request.get_json()
        cycle = cycle_schema.load(data)
        db.session.add(cycle)
        db.session.commit()
        return jsonify(cycle_schema.dump(cycle)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating cycle")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/cycles', methods=['GET'])
@jwt_required()
def get_cycles():
    """Get all research cycles."""
    cycles = Cycle.query.all()
    return jsonify(cycles_schema.dump(cycles)), 200

@research_bp.route('/cycles/<cycle_id>', methods=['GET'])
@jwt_required()
def get_cycle(cycle_id):
    """Get a specific research cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    return jsonify(cycle_schema.dump(cycle)), 200

@research_bp.route('/cycles/<cycle_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_cycle(cycle_id):
    """Update a research cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    try:
        data = request.get_json()
        cycle = cycle_schema.load(data, instance=cycle, partial=True)
        db.session.commit()
        return jsonify(cycle_schema.dump(cycle)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating cycle")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/cycles/<cycle_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_cycle(cycle_id):
    """Delete a research cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    try:
        db.session.delete(cycle)
        db.session.commit()
        return jsonify({"message": "Cycle deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting cycle")
        return jsonify({"error": str(e)}), 400