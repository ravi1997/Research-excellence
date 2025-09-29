from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.routes.v1.research import research_bp
from app.models.Cycle import PaperCategory
from app.schemas.paper_category_schema import PaperCategorySchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role

category_schema = PaperCategorySchema()
categories_schema = PaperCategorySchema(many=True)

@research_bp.route('/papercategories', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_paper_category():
    """Create a new research paper category."""
    try:
        data = request.get_json()
        category = category_schema.load(data)
        db.session.add(category)
        db.session.commit()
        return jsonify(category_schema.dump(category)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating category")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/papercategories', methods=['GET'])
@jwt_required()
def get_paper_categories():
    """Get all research paper categories."""
    categories = PaperCategory.query.all()
    return jsonify(categories_schema.dump(categories)), 200

@research_bp.route('/papercategories/<category_id>', methods=['GET'])
@jwt_required()
def get_paper_category(category_id):
    """Get a specific research paper category."""
    category = PaperCategory.query.get_or_404(category_id)
    return jsonify(category_schema.dump(category)), 200

@research_bp.route('/papercategories/<category_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_paper_category(category_id):
    """Update a research paper category."""
    category = PaperCategory.query.get_or_404(category_id)
    try:
        data = request.get_json()
        category = category_schema.load(data, instance=category, partial=True)
        db.session.commit()
        return jsonify(category_schema.dump(category)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating category")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/papercategories/<category_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_paper_category(category_id):
    """Delete a research paper category."""
    category = PaperCategory.query.get_or_404(category_id)
    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({"message": "Category deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting category")
        return jsonify({"error": str(e)}), 400