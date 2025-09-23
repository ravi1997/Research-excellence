from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.v1.research import research_bp
from app.models.Cycle import Author
from app.schemas.author_schema import AuthorSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role

author_schema = AuthorSchema()
authors_schema = AuthorSchema(many=True)

@research_bp.route('/authors', methods=['POST'])
@jwt_required()
def create_author():
    """Create a new author."""
    try:
        data = request.get_json()
        author = author_schema.load(data)
        db.session.add(author)
        db.session.commit()
        return jsonify(author_schema.dump(author)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating author")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/authors', methods=['GET'])
@jwt_required()
def get_authors():
    """Get all authors."""
    authors = Author.query.all()
    return jsonify(authors_schema.dump(authors)), 200

@research_bp.route('/authors/<author_id>', methods=['GET'])
@jwt_required()
def get_author(author_id):
    """Get a specific author."""
    author = Author.query.get_or_404(author_id)
    return jsonify(author_schema.dump(author)), 200

@research_bp.route('/authors/<author_id>', methods=['PUT'])
@jwt_required()
def update_author(author_id):
    """Update an author."""
    author = Author.query.get_or_404(author_id)
    try:
        # Check if user is authorized to update this author
        current_user_id = get_jwt_identity()
        # In a real implementation, you might want to check if the user
        # is the author or has admin privileges
        
        data = request.get_json()
        author = author_schema.load(data, instance=author, partial=True)
        db.session.commit()
        return jsonify(author_schema.dump(author)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating author")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/authors/<author_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_author(author_id):
    """Delete an author."""
    author = Author.query.get_or_404(author_id)
    try:
        db.session.delete(author)
        db.session.commit()
        return jsonify({"message": "Author deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting author")
        return jsonify({"error": str(e)}), 400