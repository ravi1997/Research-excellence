from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.v1.research import research_bp
from app.models.Cycle import Awards, Author, Category, PaperCategory, Cycle
from app.schemas.awards_schema import AwardsSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role

award_schema = AwardsSchema()
awards_schema = AwardsSchema(many=True)

@research_bp.route('/awards', methods=['POST'])
@jwt_required()
def create_award():
    """Create a new research award."""
    try:
        data = request.get_json()
        award = award_schema.load(data)
        db.session.add(award)
        db.session.commit()
        return jsonify(award_schema.dump(award)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating award")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/awards', methods=['GET'])
@jwt_required()
def get_awards():
    """Get all research awards."""
    awards = Awards.query.all()
    return jsonify(awards_schema.dump(awards)), 200

@research_bp.route('/awards/<award_id>', methods=['GET'])
@jwt_required()
def get_award(award_id):
    """Get a specific research award."""
    award = Awards.query.get_or_404(award_id)
    return jsonify(award_schema.dump(award)), 200

@research_bp.route('/awards/<award_id>', methods=['PUT'])
@jwt_required()
def update_award(award_id):
    """Update a research award."""
    award = Awards.query.get_or_404(award_id)
    try:
        # Check if user is authorized to update this award
        current_user_id = get_jwt_identity()
        # In a real implementation, you might want to check if the user
        # is the author or has admin privileges
        
        data = request.get_json()
        award = award_schema.load(data, instance=award, partial=True)
        db.session.commit()
        return jsonify(award_schema.dump(award)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating award")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/awards/<award_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_award(award_id):
    """Delete a research award."""
    award = Awards.query.get_or_404(award_id)
    try:
        db.session.delete(award)
        db.session.commit()
        return jsonify({"message": "Award deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting award")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/awards/<award_id>/submit', methods=['POST'])
@jwt_required()
def submit_award(award_id):
    """Submit an award for review."""
    award = Awards.query.get_or_404(award_id)
    try:
        # Check if user is authorized to submit this award
        current_user_id = get_jwt_identity()
        # In a real implementation, you might want to check if the user
        # is the author of the award
        
        award.status = Status.UNDER_REVIEW
        db.session.commit()
        return jsonify({"message": "Award submitted for review"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error submitting award")
        return jsonify({"error": str(e)}), 400