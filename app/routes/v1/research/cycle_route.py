from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.routes.v1.research import research_bp
from app.models.Cycle import Cycle, CycleWindow
from app.schemas.cycle_schema import CycleSchema, CycleWindowSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role, CyclePhase

cycle_schema = CycleSchema()
cycles_schema = CycleSchema(many=True)
cycle_window_schema = CycleWindowSchema()
cycle_windows_schema = CycleWindowSchema(many=True)

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
    return jsonify(cycles_schema.dump(cycles)), 201

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

# New routes for managing cycle windows
@research_bp.route('/cycles/<cycle_id>/windows', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_cycle_window(cycle_id):
    """Create a new window for a cycle."""
    try:
        data = request.get_json()
        # Verify that the cycle exists
        cycle = Cycle.query.get_or_404(cycle_id)
        
        # Validate the phase
        try:
            CyclePhase(data.get('phase'))
        except ValueError:
            return jsonify({"error": "Invalid phase value"}), 400
        
        # Check if a window of this phase already exists for this cycle
        existing_window = CycleWindow.query.filter_by(
            cycle_id=cycle_id, 
            phase=data.get('phase')
        ).first()
        if existing_window:
            return jsonify({"error": f"A window for phase {data.get('phase')} already exists for this cycle"}), 400
            
        # Create the new window
        window_data = {
            'cycle_id': cycle_id,
            'phase': data.get('phase'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date')
        }
        cycle_window = cycle_window_schema.load(window_data)
        db.session.add(cycle_window)
        db.session.commit()
        return jsonify(cycle_window_schema.dump(cycle_window)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating cycle window")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/cycles/<cycle_id>/windows', methods=['GET'])
@jwt_required()
def get_cycle_windows(cycle_id):
    """Get all windows for a specific cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    windows = CycleWindow.query.filter_by(cycle_id=cycle_id).all()
    return jsonify(cycle_windows_schema.dump(windows)), 200

@research_bp.route('/cycles/<cycle_id>/windows/<window_id>', methods=['GET'])
@jwt_required()
def get_cycle_window(cycle_id, window_id):
    """Get a specific window for a cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    window = CycleWindow.query.filter_by(cycle_id=cycle_id, id=window_id).first_or_404()
    return jsonify(cycle_window_schema.dump(window)), 20

@research_bp.route('/cycles/<cycle_id>/windows/<window_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_cycle_window(cycle_id, window_id):
    """Update a specific window for a cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    window = CycleWindow.query.filter_by(cycle_id=cycle_id, id=window_id).first_or_404()
    try:
        data = request.get_json()
        # Validate the phase if it's being updated
        if 'phase' in data:
            try:
                CyclePhase(data.get('phase'))
            except ValueError:
                return jsonify({"error": "Invalid phase value"}), 400
        cycle_window = cycle_window_schema.load(data, instance=window, partial=True)
        db.session.commit()
        return jsonify(cycle_window_schema.dump(cycle_window)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating cycle window")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/cycles/<cycle_id>/windows/<window_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_cycle_window(cycle_id, window_id):
    """Delete a specific window for a cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    window = CycleWindow.query.filter_by(cycle_id=cycle_id, id=window_id).first_or_404()
    try:
        db.session.delete(window)
        db.session.commit()
        return jsonify({"message": "Cycle window deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting cycle window")
        return jsonify({"error": str(e)}), 400

# Convenience routes for specific component windows
@research_bp.route('/cycles/<cycle_id>/abstract-windows', methods=['GET'])
@jwt_required()
def get_abstract_windows(cycle_id):
    """Get abstract-specific windows for a cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    abstract_phases = [
        CyclePhase.ABSTRACT_SUBMISSION, 
        CyclePhase.ABSTRACT_VERIFICATION, 
        CyclePhase.ABSTRACT_FINAL
    ]
    windows = CycleWindow.query.filter(
        CycleWindow.cycle_id == cycle_id,
        CycleWindow.phase.in_(abstract_phases)
    ).all()
    return jsonify(cycle_windows_schema.dump(windows)), 200

@research_bp.route('/cycles/<cycle_id>/best-paper-windows', methods=['GET'])
@jwt_required()
def get_best_paper_windows(cycle_id):
    """Get best paper-specific windows for a cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    best_paper_phases = [
        CyclePhase.BEST_PAPER_SUBMISSION, 
        CyclePhase.BEST_PAPER_VERIFICATION, 
        CyclePhase.BEST_PAPER_FINAL
    ]
    windows = CycleWindow.query.filter(
        CycleWindow.cycle_id == cycle_id,
        CycleWindow.phase.in_(best_paper_phases)
    ).all()
    return jsonify(cycle_windows_schema.dump(windows)), 200

@research_bp.route('/cycles/<cycle_id>/award-windows', methods=['GET'])
@jwt_required()
def get_award_windows(cycle_id):
    """Get award-specific windows for a cycle."""
    cycle = Cycle.query.get_or_404(cycle_id)
    award_phases = [
        CyclePhase.AWARD_SUBMISSION, 
        CyclePhase.AWARD_VERIFICATION, 
        CyclePhase.AWARD_FINAL
    ]
    windows = CycleWindow.query.filter(
        CycleWindow.cycle_id == cycle_id,
        CycleWindow.phase.in_(award_phases)
    ).all()
    return jsonify(cycle_windows_schema.dump(windows)), 200