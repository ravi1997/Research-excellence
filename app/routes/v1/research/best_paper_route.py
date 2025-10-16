from flask import request, jsonify, current_app, abort, send_file
import json
import os
import uuid
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.User import User
from app.routes.v1.research import research_bp
from app.models.Cycle import BestPaperVerifiers, BestPaper, Author, Category, PaperCategory, Cycle
from app.schemas.best_paper_schema import BestPaperSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role, Status
from werkzeug.utils import secure_filename

from app.utils.services.mail import send_mail
from app.utils.services.sms import send_sms

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
                user = User.query.get(current_user_id)
                if not user:
                    return jsonify({"error": "User not found"}), 404
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
        # Send notification (SMS and Email) to the user who created the best paper
        send_sms(
            user.mobile, f"Your best paper(Oncology) id : {best_paper.id} has been created successfully and is pending submission for review."
        )

        send_mail(
            user.email,
            "Best Paper(Oncology) Created Successfully",
            f"Dear {user.username},\n\nYour best paper(Oncology) with ID {best_paper.id} has been created successfully and is pending submission for review.\n Details:\nTitle: {best_paper.title}\nBest Paper ID: {best_paper.id}\n\nBest regards,\nResearch Section,AIIMS"
        )

        return jsonify(best_paper_schema.dump(best_paper)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating best paper")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/best-papers/<best_paper_id>/pdf', methods=['GET'])
@jwt_required()
def get_best_paper_pdf(best_paper_id):
    best_paper = BestPaper.query.get_or_404(best_paper_id)
    if not best_paper.full_paper_path:
        abort(404, description="No PDF uploaded for this best paper.")
    try:
        return send_file(best_paper.full_paper_path, mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        current_app.logger.exception("Error sending PDF file")
        abort(404, description="PDF file not found.")


@research_bp.route('/best-papers/<best_paper_id>/forwarding_pdf', methods=['GET'])
@jwt_required()
def get_best_paper_forwarding_pdf(best_paper_id):
    best_paper = BestPaper.query.get_or_404(best_paper_id)
    if not best_paper.forwarding_letter_path:
        abort(404, description="No forwarding PDF uploaded for this best paper.")
    try:
        return send_file(best_paper.forwarding_letter_path, mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        current_app.logger.exception("Error sending PDF file")
        abort(404, description="PDF file not found.")

@research_bp.route('/best-papers', methods=['GET'])
@jwt_required()
def get_best_papers():
    """Get all Best Paper submissions with filtering and pagination support."""
    try:
        # Get query parameters
        q = request.args.get('q', '').strip()
        verifiers = request.args.get('verifiers', '').strip()
        page = int(request.args.get('page', 1))
        status = request.args.get('status', '').strip().upper()
        page_size = int(request.args.get('page_size', 20))
        sort_by = request.args.get('sort_by', 'id')
        sort_dir = request.args.get('sort_dir', 'desc')
        verifier_filter = request.args.get('verifier', '').strip().lower() == 'true'
        
        # Validate page size
        page_size = min(page_size, 100)  # Limit max page size
        page = max(1, page)  # Ensure page is at least 1
        
        # Build query for best papers
        query = BestPaper.query
        
        q_int = q.isdigit() and int(q) or None
        
        # Apply search filter
        if q:
            # Filter out None values
            search_filters = [f for f in [
                BestPaper.title.ilike(f'%{q}%'),
                BestPaper.content.ilike(f'%{q}%') if hasattr(BestPaper, 'content') else None,
                BestPaper.id == q_int if q_int else None
            ] if f is not None]
            
            if search_filters:
                search_filter = db.or_(*search_filters)
                query = query.filter(search_filter)
        
        # Apply status filter
        if status in ['PENDING', 'UNDER_REVIEW', 'ACCEPTED', 'REJECTED']:
            status_value = Status[status]
            query = query.filter(BestPaper.status == status_value)
        
        # Apply verifiers filter
        if verifiers:
            if verifiers.lower() == 'yes':
                # Only best papers with assigned verifiers
                query = query.join(BestPaperVerifiers, BestPaper.id == BestPaperVerifiers.best_paper_id)
            elif verifiers.lower() == 'no':
                # Only best papers without assigned verifiers
                query = query.outerjoin(BestPaperVerifiers, BestPaper.id == BestPaperVerifiers.best_paper_id).filter(BestPaperVerifiers.best_paper_id.is_(None))
        
        # Apply verifier filter (filter by current user if they are a verifier)
        if verifier_filter:
            current_user_id = get_jwt_identity()
            # Only show best papers assigned to the current user (robust join)
            query = query.join(BestPaperVerifiers, BestPaperVerifiers.best_paper_id == BestPaper.id)
            query = query.join(User, User.id == BestPaperVerifiers.user_id)
            query = query.filter(BestPaperVerifiers.user_id == current_user_id)
        
        # Apply sorting
        if sort_by == 'title':
            order_by = BestPaper.title.asc() if sort_dir.lower() == 'asc' else BestPaper.title.desc()
        elif sort_by == 'created_at':
            order_by = BestPaper.created_at.asc() if sort_dir.lower() == 'asc' else BestPaper.created_at.desc()
        else:  # default to id
            order_by = BestPaper.id.asc() if sort_dir.lower() == 'asc' else BestPaper.id.desc()
        
        query = query.order_by(order_by)
        
        # Apply pagination
        total = query.count()
        best_papers = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # Add verifiers count to each best paper
        best_papers_data = []
        for best_paper in best_papers:
            best_paper_dict = best_paper_schema.dump(best_paper)
            # Count verifiers assigned to this best paper
            verifiers_count = db.session.query(BestPaperVerifiers).filter_by(best_paper_id=best_paper.id).count()
            best_paper_dict['verifiers_count'] = verifiers_count
            best_papers_data.append(best_paper_dict)
        
        # Prepare response
        response = {
            'items': best_papers_data,
            'total': total,
            'page': page,
            'pages': (total + page_size - 1) // page_size,
            'page_size': page_size
        }
        
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.exception("Error listing best papers with parameters")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/best-papers/<best_paper_id>', methods=['GET'])
@jwt_required()
def get_best_paper(best_paper_id):
    """Get a specific Best Paper submission."""
    best_paper = BestPaper.query.get_or_404(best_paper_id)
    data = best_paper_schema.dump(best_paper)
    # Add PDF URLs if available
    if best_paper.full_paper_path:
        data['pdf_url'] = f"/api/v1/research/best-papers/{best_paper_id}/pdf"
    if best_paper.forwarding_letter_path:
        data['forwarding_pdf_url'] = f"/api/v1/research/best-papers/{best_paper_id}/forwarding_pdf"
    return jsonify(data), 200

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

    pending_count = best_papers_query.filter(BestPaper.status==Status.PENDING).count()
    under_review_count = best_papers_query.filter(BestPaper.status==Status.UNDER_REVIEW).count()
    accepted_count = best_papers_query.filter(BestPaper.status==Status.ACCEPTED).count()
    rejected_count = best_papers_query.filter(BestPaper.status==Status.REJECTED).count()

    return jsonify({
        "pending": pending_count,
        "under_review": under_review_count,
        "accepted": accepted_count,
        "rejected": rejected_count
    }), 200


# Verifier Management Routes for Best Papers

@research_bp.route('/best-papers/<best_paper_id>/verifiers/<user_id>', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def assign_verifier_to_best_paper(best_paper_id, user_id):
    """Assign a verifier to a best paper."""
    try:
        # Check if best paper exists
        best_paper = BestPaper.query.get_or_404(best_paper_id)
        
        # Check if user exists and is a verifier
        user = User.query.get_or_404(user_id)
        if not user.has_role(Role.VERIFIER.value):
            return jsonify({"error": "User is not a verifier"}), 400
        
        # Check if already assigned
        existing_assignment = BestPaperVerifiers.query.filter_by(
            best_paper_id=best_paper_id, user_id=user_id).first()
        
        if existing_assignment:
            return jsonify({"message": "Verifier already assigned to this best paper"}), 200
        
        # Create new assignment
        assignment = BestPaperVerifiers(
            best_paper_id=best_paper_id,
            user_id=user_id
        )
        db.session.add(assignment)
        db.session.commit()
        
        return jsonify({"message": "Verifier assigned successfully"}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error assigning verifier to best paper")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/best-papers/<best_paper_id>/verifiers/<user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def unassign_verifier_from_best_paper(best_paper_id, user_id):
    """Unassign a verifier from a best paper."""
    try:
        # Check if best paper exists
        best_paper = BestPaper.query.get_or_404(best_paper_id)
        
        # Check if assignment exists
        assignment = BestPaperVerifiers.query.filter_by(
            best_paper_id=best_paper_id, user_id=user_id).first_or_404()
        
        db.session.delete(assignment)
        db.session.commit()
        
        return jsonify({"message": "Verifier unassigned successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error unassigning verifier from best paper")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/best-papers/<best_paper_id>/verifiers', methods=['GET'])
@jwt_required()
def get_verifiers_for_best_paper(best_paper_id):
    """Get all verifiers assigned to a best paper."""
    try:
        # Check if best paper exists
        best_paper = BestPaper.query.get_or_404(best_paper_id)
        
        # Get all verifiers for this best paper
        verifiers = db.session.query(User).join(
            BestPaperVerifiers, User.id == BestPaperVerifiers.user_id
        ).filter(
            BestPaperVerifiers.best_paper_id == best_paper_id
        ).all()
        
        # Convert to simple dict format
        verifiers_data = []
        for verifier in verifiers:
            verifiers_data.append({
                'id': str(verifier.id),
                'username': verifier.username,
                'email': verifier.email,
                'employee_id': verifier.employee_id
            })
        
        return jsonify(verifiers_data), 200
    except Exception as e:
        current_app.logger.exception("Error getting verifiers for best paper")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/verifiers/<user_id>/best-papers', methods=['GET'])
@jwt_required()
def get_best_papers_for_verifier(user_id):
    """Get all best papers assigned to a verifier."""
    try:
        # Check if user exists
        user = User.query.get_or_404(user_id)
        
        # Get all best papers assigned to this verifier
        best_papers = db.session.query(BestPaper).join(
            BestPaperVerifiers, BestPaper.id == BestPaperVerifiers.best_paper_id
        ).filter(
            BestPaperVerifiers.user_id == user_id
        ).all()
        
        return jsonify(best_papers_schema.dump(best_papers)), 200
    except Exception as e:
        current_app.logger.exception("Error getting best papers for verifier")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/best-papers/bulk-assign-verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_assign_verifiers_to_best_papers():
    """Bulk assign verifiers to multiple best papers."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'best_paper_ids' not in data or 'user_ids' not in data:
            return jsonify({"error": "Missing best_paper_ids or user_ids in request"}), 400
        
        best_paper_ids = data['best_paper_ids']
        user_ids = data['user_ids']
        
        # Validate that all best papers and users exist
        best_papers = BestPaper.query.filter(BestPaper.id.in_(best_paper_ids)).all()
        users = User.query.filter(User.id.in_(user_ids)).all()
        
        # Check if all users are verifiers
        non_verifiers = [user for user in users if not user.has_role(Role.VERIFIER.value)]
        if non_verifiers:
            return jsonify({"error": "Some users are not verifiers"}), 400
        
        # Create assignments
        assignments_created = 0
        for best_paper_id in best_paper_ids:
            for user_id in user_ids:
                # Check if already assigned
                existing_assignment = BestPaperVerifiers.query.filter_by(
                    best_paper_id=best_paper_id, user_id=user_id).first()
                
                if not existing_assignment:
                    assignment = BestPaperVerifiers(
                        best_paper_id=best_paper_id,
                        user_id=user_id
                    )
                    db.session.add(assignment)
                    assignments_created += 1
        
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully created {assignments_created} assignments",
            "assignments_created": assignments_created
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error in bulk assigning verifiers to best papers")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/best-papers/bulk-unassign-verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_unassign_verifiers_from_best_papers():
    """Bulk unassign verifiers from multiple best papers."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'best_paper_ids' not in data or 'user_ids' not in data:
            return jsonify({"error": "Missing best_paper_ids or user_ids in request"}), 400
        
        best_paper_ids = data['best_paper_ids']
        user_ids = data['user_ids']
        
        # Delete assignments
        assignments_deleted = BestPaperVerifiers.query.filter(
            BestPaperVerifiers.best_paper_id.in_(best_paper_ids),
            BestPaperVerifiers.user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully deleted {assignments_deleted} assignments",
            "assignments_deleted": assignments_deleted
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error in bulk unassigning verifiers from best papers")
        return jsonify({"error": str(e)}), 400
