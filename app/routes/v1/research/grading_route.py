from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.v1.research import research_bp
from app.models.Cycle import Grading, GradingType, Abstracts, BestPaper, Awards
from app.schemas.grading_schema import GradingSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role

grading_schema = GradingSchema()
gradings_schema = GradingSchema(many=True)

@research_bp.route('/gradings', methods=['POST'])
@jwt_required()
@require_roles(Role.VERIFIER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def create_grading():
    """Create a new grading."""
    try:
        data = request.get_json()
        
        # Verify that the grading_type exists
        grading_type_id = data.get('grading_type_id')
        if grading_type_id:
            grading_type = GradingType.query.get(grading_type_id)
            if not grading_type:
                return jsonify({"error": "Grading type not found"}), 404
        
        # Validate that only one of the target entities is provided
        abstract_id = data.get('abstract_id')
        best_paper_id = data.get('best_paper_id')
        award_id = data.get('award_id')
        
        target_count = sum(1 for x in [abstract_id, best_paper_id, award_id] if x)
        if target_count != 1:
            return jsonify({"error": "Exactly one of abstract_id, best_paper_id, or award_id must be provided"}), 400
        
        # Validate that the target entity exists
        if abstract_id:
            abstract = Abstracts.query.get(abstract_id)
            if not abstract:
                return jsonify({"error": "Abstract not found"}), 404
        elif best_paper_id:
            best_paper = BestPaper.query.get(best_paper_id)
            if not best_paper:
                return jsonify({"error": "Best paper not found"}), 404
        elif award_id:
            award = Awards.query.get(award_id)
            if not award:
                return jsonify({"error": "Award not found"}), 404

        # Get the current user ID from JWT
        current_user_id = get_jwt_identity()
        data['graded_by_id'] = current_user_id

        # Marshmallow Schema (non SQLAlchemy) returns a dict; instantiate ORM model explicitly
        payload = grading_schema.load(data)
        grading = Grading(**payload)
        db.session.add(grading)
        db.session.commit()
        return jsonify(grading_schema.dump(grading)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating grading")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/gradings', methods=['GET'])
@jwt_required()
def get_gradings():
    """Get all gradings with optional filtering."""
    try:
        # Get query parameters for filtering
        grading_type_id = request.args.get('grading_type_id')
        abstract_id = request.args.get('abstract_id')
        best_paper_id = request.args.get('best_paper_id')
        award_id = request.args.get('award_id')
        graded_by_id = request.args.get('graded_by_id')
        
        query = Grading.query
        
        if grading_type_id:
            query = query.filter(Grading.grading_type_id == grading_type_id)
        if abstract_id:
            query = query.filter(Grading.abstract_id == abstract_id)
        if best_paper_id:
            query = query.filter(Grading.best_paper_id == best_paper_id)
        if award_id:
            query = query.filter(Grading.award_id == award_id)
        if graded_by_id:
            query = query.filter(Grading.graded_by_id == graded_by_id)
        
        gradings = query.all()
        return jsonify(gradings_schema.dump(gradings)), 200
    except Exception as e:
        current_app.logger.exception("Error getting gradings")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/gradings/<grading_id>', methods=['GET'])
@jwt_required()
def get_grading(grading_id):
    """Get a specific grading."""
    grading = Grading.query.get_or_404(grading_id)
    return jsonify(grading_schema.dump(grading)), 200

@research_bp.route('/gradings/<grading_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.VERIFIER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def update_grading(grading_id):
    """Update a grading."""
    grading = Grading.query.get_or_404(grading_id)
    try:
        data = request.get_json()
        
        # Prevent changing the target entity or grading type
        if 'abstract_id' in data and data['abstract_id'] != str(grading.abstract_id):
            return jsonify({"error": "Cannot change target entity"}), 400
        if 'best_paper_id' in data and data['best_paper_id'] != str(grading.best_paper_id):
            return jsonify({"error": "Cannot change target entity"}), 400
        if 'award_id' in data and data['award_id'] != str(grading.award_id):
            return jsonify({"error": "Cannot change target entity"}), 400
        if 'grading_type_id' in data and data['grading_type_id'] != str(grading.grading_type_id):
            return jsonify({"error": "Cannot change grading type"}), 400
        
        # Since GradingSchema is minimal and not SQLAlchemy-bound, apply allowed fields manually
        allowed = {'score', 'comments'}
        for k, v in data.items():
            if k in allowed:
                setattr(grading, k, v)
        db.session.commit()
        return jsonify(grading_schema.dump(grading)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating grading")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/gradings/<grading_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_grading(grading_id):
    """Delete a grading."""
    grading = Grading.query.get_or_404(grading_id)
    try:
        db.session.delete(grading)
        db.session.commit()
        return jsonify({"message": "Grading deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting grading")
        return jsonify({"error": str(e)}), 400

# Additional endpoints for getting gradings for specific entities
@research_bp.route('/abstracts/<abstract_id>/gradings', methods=['GET'])
@jwt_required()
def get_abstract_gradings(abstract_id):
    """Get all gradings for a specific abstract."""
    gradings = Grading.query.filter_by(abstract_id=abstract_id).all()
    return jsonify(gradings_schema.dump(gradings)), 200

@research_bp.route('/best-papers/<best_paper_id>/gradings', methods=['GET'])
@jwt_required()
def get_best_paper_gradings(best_paper_id):
    """Get all gradings for a specific best paper."""
    gradings = Grading.query.filter_by(best_paper_id=best_paper_id).all()
    return jsonify(gradings_schema.dump(gradings)), 200

@research_bp.route('/awards/<award_id>/gradings', methods=['GET'])
@jwt_required()
def get_award_gradings(award_id):
    """Get all gradings for a specific award."""
    gradings = Grading.query.filter_by(award_id=award_id).all()
    return jsonify(gradings_schema.dump(gradings)), 200