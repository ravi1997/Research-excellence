from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.routes.v1.research import research_bp
from app.models.Cycle import Category
from app.schemas.category_schema import CategorySchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)

@research_bp.route('/categories', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def create_category():
    """Create a new research category."""
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

@research_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """Get all research categories."""
    categories = Category.query.all()
    return jsonify(categories_schema.dump(categories)), 200

@research_bp.route('/categories/<category_id>', methods=['GET'])
@jwt_required()
def get_category(category_id):
    """Get a specific research category."""
    category = Category.query.get_or_404(category_id)
    return jsonify(category_schema.dump(category)), 200

@research_bp.route('/categories/<category_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def update_category(category_id):
    """Update a research category."""
    category = Category.query.get_or_404(category_id)
    try:
        data = request.get_json()
        category = category_schema.load(data, instance=category, partial=True)
        db.session.commit()
        return jsonify(category_schema.dump(category)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating category")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/categories/<category_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_category(category_id):
    """Delete a research category."""
    category = Category.query.get_or_404(category_id)
    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({"message": "Category deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting category")
        return jsonify({"error": str(e)}), 400