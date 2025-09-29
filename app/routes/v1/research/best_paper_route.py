from flask import request, jsonify, current_app
import json
import os
import uuid
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.User import User
from app.routes.v1.research import research_bp
from app.models.Cycle import BestPaperVerifiers, BestPaper, Author
from app.schemas.best_paper_schema import BestPaperSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role, Status
from werkzeug.utils import secure_filename

# NOTE: Underlying model/schema still named BestPaper for now; outward API renamed to best_papers
best_paper_schema = BestPaperSchema()
best_papers_schema = BestPaperSchema(many=True)

@research_bp.route('/best-papers', methods=['POST'])
@jwt_required()
def create_best_paper():
    """Create a new Best Paper submission."""
    try:
        # Handle both JSON and multipart form-data (for file uploads)
        if request.is_json:
            data = request.get_json()
            full_paper_path = None
            forwarding_letter_path = None
        else:
            data_json = request.form.get('data')
            if not data_json:
                return jsonify({"error": "No data provided"}), 400

            try:
                # Get the current user ID from JWT
                current_user_id = get_jwt_identity()

                # Set created_by_id in data for schema load
                data = json.loads(data_json)
                data['created_by_id'] = current_user_id
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400

            # Handle file uploads
            full_paper_path = None
            forwarding_letter_path = None

            # Main best paper PDF (frontend key: bestpaper_pdf; maintain compatibility with abstract_pdf if provided)
            pdf_file = request.files.get('bestpaper_pdf') or request.files.get('abstract_pdf')
            if pdf_file:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(pdf_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                pdf_file.save(file_path)
                current_app.logger.info(f"Best paper PDF saved to: {file_path}")
                # Store relative path like abstracts route (strip leading app/ if present)
                full_paper_path = file_path.replace("app/", "", 1)

            # Forwarding letter PDF (frontend key: forwarding_pdf)
            fwd_file = request.files.get('forwarding_pdf')
            if fwd_file:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(fwd_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                fwd_file.save(file_path)
                current_app.logger.info(f"Forwarding letter PDF saved to: {file_path}")
                forwarding_letter_path = file_path.replace("app/", "", 1)

        # Extract potential authors array (frontend sends single-author array)
        authors_data = data.pop('authors', []) or []

        # If client already provided author_id use it, otherwise create an Author from first authors entry
        author_id = data.get('author_id')
        if not author_id:
            if authors_data:
                a0 = authors_data[0] or {}
                author = Author(
                    name=a0.get('name', ''),
                    email=a0.get('email'),
                    affiliation=a0.get('affiliation'),
                    is_presenter=a0.get('is_presenter', False),
                    is_corresponding=a0.get('is_corresponding', False),
                )
                if not author.name:
                    return jsonify({"error": "Author name is required"}), 400
                db.session.add(author)
                db.session.flush()  # obtain author.id
                author_id = str(author.id)
                current_app.logger.info(f"Created author {author.name} with ID {author_id} for best paper")
            else:
                return jsonify({"error": "Author information is required"}), 400

        # Inject resolved author_id and any uploaded file paths
        data['author_id'] = author_id
        if 'paper_category_id' not in data:
            return jsonify({"error": "paper_category_id is required"}), 400
        if full_paper_path:
            data['full_paper_path'] = full_paper_path
        if forwarding_letter_path:
            data['forwarding_letter_path'] = forwarding_letter_path

        # Load and persist best paper
        best_paper = best_paper_schema.load(data)
        db.session.add(best_paper)
        db.session.commit()
        return jsonify(best_paper_schema.dump(best_paper)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating best paper")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/best-papers', methods=['GET'])
@jwt_required()
def get_best_papers():
    """Get all Best Paper submissions."""
    best_papers = BestPaper.query.all()
    return jsonify(best_papers_schema.dump(best_papers)), 200

@research_bp.route('/best-papers/<best_paper_id>', methods=['GET'])
@jwt_required()
def get_best_paper(best_paper_id):
    """Get a specific Best Paper submission."""
    best_paper = BestPaper.query.get_or_404(best_paper_id)
    return jsonify(best_paper_schema.dump(best_paper)), 200

@research_bp.route('/best-papers/<best_paper_id>', methods=['PUT'])
@jwt_required()
def update_best_paper(best_paper_id):
    """Update a Best Paper submission."""
    best_paper = BestPaper.query.get_or_404(best_paper_id)
    try:
        # Check if user is authorized to update this best paper
        current_user_id = get_jwt_identity()
        # In a real implementation, you might want to check if the user
        # is the author or has admin privileges
        
        data = request.get_json()
        best_paper = best_paper_schema.load(data, instance=best_paper, partial=True)
        db.session.commit()
        return jsonify(best_paper_schema.dump(best_paper)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating best paper")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/best-papers/<best_paper_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_best_paper(best_paper_id):
    """Delete a Best Paper submission."""
    best_paper = BestPaper.query.get_or_404(best_paper_id)
    try:
        db.session.delete(best_paper)
        db.session.commit()
        return jsonify({"message": "Best Paper deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting best paper")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/best-papers/<best_paper_id>/submit', methods=['POST'])
@jwt_required()
def submit_best_paper(best_paper_id):
    """Submit a Best Paper for review."""
    best_paper = BestPaper.query.get_or_404(best_paper_id)
    try:
        # Check if user is authorized to submit this best paper
        current_user_id = get_jwt_identity()
        # In a real implementation, you might want to check if the user
        # is the author of the submission
        best_paper.status = Status.UNDER_REVIEW
        db.session.commit()
        return jsonify({"message": "Best Paper submitted for review"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error submitting best paper")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/best-papers/status', methods=['GET'])
@jwt_required()
def get_best_paper_submission_status():
    """Get submission status of Best Paper submissions for the current user."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)

    if user.has_role(Role.ADMIN.value) or user.has_role(Role.SUPERADMIN.value):
        # Admins can see all submissions
        best_papers_query = BestPaper.query
    elif user.has_role(Role.VERIFIER.value):
        # Verifiers can see submissions assigned to them
        best_papers_query = db.session.query(BestPaper).join(
            BestPaperVerifiers, BestPaper.id == BestPaperVerifiers.best_paper_id
        ).filter(
            BestPaperVerifiers.user_id == current_user_id
        )
    else:
        # NOTE: BestPaper model currently lacks created_by field; this filter may need adjustment if field added.
        # fallback to all until ownership implemented
        best_papers_query = BestPaper.query.filter_by(
            created_by_id=current_user_id)

    pending_count = best_papers_query.filter_by(status=Status.PENDING).count()
    under_review_count = best_papers_query.filter_by(status=Status.UNDER_REVIEW).count()
    accepted_count = best_papers_query.filter_by(status=Status.ACCEPTED).count()
    rejected_count = best_papers_query.filter_by(status=Status.REJECTED).count()

    return jsonify({
        "pending": pending_count,
        "under_review": under_review_count,
        "accepted": accepted_count,
        "rejected": rejected_count
    }), 200
