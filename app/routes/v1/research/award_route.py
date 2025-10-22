from flask import request, jsonify, current_app,abort, send_file
import json
import os
import uuid
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.User import User
from app.routes.v1.research import research_bp
from app.models.Cycle import AwardVerifiers, Awards, Author, Category, PaperCategory, Cycle
from app.schemas.awards_schema import AwardsSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role, Status
from werkzeug.utils import secure_filename

from app.utils.services.mail import send_mail
from app.utils.services.sms import send_sms

award_schema = AwardsSchema()
awards_schema = AwardsSchema(many=True)

@research_bp.route('/awards', methods=['POST'])
@jwt_required()
def create_award():
    """Create a new research award."""
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

            # Main award PDF (frontend key: award_pdf; maintain compatibility with abstract_pdf if provided)
            pdf_file = request.files.get('award_pdf') or request.files.get('abstract_pdf')
            if pdf_file:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(pdf_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                pdf_file.save(file_path)
                current_app.logger.info(f"Award PDF saved to: {file_path}")
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
        if not (
                user.has_role(Role.ADMIN.value) or
                user.has_role(Role.SUPERADMIN.value) or
                user.has_role(Role.VERIFIER.value) or
                user.has_role(Role.COORDINATOR.value)
        ):
            query = query.filter_by(created_by_id=current_user_id)
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
                current_app.logger.info(f"Created author {author.name} with ID {author_id} for award")
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

        # Load and persist award
        award = award_schema.load(data)
        db.session.add(award)
        db.session.commit()
        
        # Send notification (SMS and Email) to the user who created the award
        send_sms(
            user.mobile, f"Your award id : {award.id} has been created successfully and is pending submission for review."
        )
        send_mail(
            user.email,
            "Award Created Successfully",
            f"Dear {user.username},\n\nYour award with ID {award.id} has been created successfully and is pending submission for review.\n Details:\nTitle: {award.title}\nAward ID: {award.id}\n\nBest regards,\nResearch Section,AIIMS"
        )        
        return jsonify(award_schema.dump(award)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating award")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/awards/<abstract_id>/pdf', methods=['GET'])
@jwt_required()
def get_awards_pdf(abstract_id):
    abstract = Awards.query.get_or_404(abstract_id)
    if not abstract.full_paper_path:
        abort(404, description="No PDF uploaded for this abstract.")
    try:
        return send_file(abstract.full_paper_path, mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        current_app.logger.exception("Error sending PDF file")
        abort(404, description="PDF file not found.")


@research_bp.route('/awards/<abstract_id>/forwarding_pdf', methods=['GET'])
@jwt_required()
def get_awards_forwarding_pdf(abstract_id):
    abstract = Awards.query.get_or_404(abstract_id)
    if not abstract.forwarding_letter_path:
        abort(404, description="No PDF uploaded for this abstract.")
    try:
        return send_file(abstract.forwarding_letter_path, mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        current_app.logger.exception("Error sending PDF file")
        abort(404, description="PDF file not found.")

@research_bp.route('/awards', methods=['GET'])
@jwt_required()
def get_awards():
    """Get all research awards with filtering and pagination support."""
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
        
        # Build query for awards
        query = Awards.query
        
        q_int = q.isdigit() and int(q) or None
        
        # Apply search filter
        if q:
            search_filter = db.or_(
                Awards.title.ilike(f'%{q}%'),
                Awards.description.ilike(f'%{q}%') if hasattr(Awards, 'description') else None
            )
            # Filter out None values
            search_filters = [f for f in [
                Awards.title.ilike(f'%{q}%'),
                Awards.description.ilike(f'%{q}%') if hasattr(Awards, 'description') else None,
                Awards.id == q_int if q_int else None
            ] if f is not None]
            
            if search_filters:
                search_filter = db.or_(*search_filters)
                query = query.filter(search_filter)
        
        # Apply status filter
        if status in ['PENDING', 'UNDER_REVIEW', 'ACCEPTED', 'REJECTED']:
            status_value = Status[status]
            query = query.filter(Awards.status == status_value)
        
        # Apply verifiers filter
        if verifiers:
            if verifiers.lower() == 'yes':
                # Only awards with assigned verifiers
                query = query.join(AwardVerifiers, Awards.id == AwardVerifiers.award_id)
            elif verifiers.lower() == 'no':
                # Only awards without assigned verifiers
                query = query.outerjoin(AwardVerifiers, Awards.id == AwardVerifiers.award_id).filter(AwardVerifiers.award_id.is_(None))
        
        # Apply verifier filter (filter by current user if they are a verifier)
        if verifier_filter:
            current_user_id = get_jwt_identity()
            # Only show awards assigned to the current user (robust join)
            query = query.join(AwardVerifiers, AwardVerifiers.award_id == Awards.id)
            query = query.join(User, User.id == AwardVerifiers.user_id)
            query = query.filter(AwardVerifiers.user_id == current_user_id)
        
        current_user_id = get_jwt_identity()
        user = User.query.filter_by(id=current_user_id).first()
        if not (
                user.has_role(Role.ADMIN.value) or
                user.has_role(Role.SUPERADMIN.value) or
                user.has_role(Role.VERIFIER.value) or
                user.has_role(Role.COORDINATOR.value)
        ):
            query = query.filter_by(created_by_id=current_user_id)

        # Apply sorting
        if sort_by == 'title':
            order_by = Awards.title.asc() if sort_dir.lower() == 'asc' else Awards.title.desc()
        elif sort_by == 'created_at':
            order_by = Awards.created_at.asc() if sort_dir.lower() == 'asc' else Awards.created_at.desc()
        else:  # default to id
            order_by = Awards.id.asc() if sort_dir.lower() == 'asc' else Awards.id.desc()
        
        query = query.order_by(order_by)
        
        # Apply pagination
        total = query.count()
        awards = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # Add verifiers count to each award
        awards_data = []
        for award in awards:
            award_dict = award_schema.dump(award)
            # Count verifiers assigned to this award
            verifiers_count = db.session.query(AwardVerifiers).filter_by(award_id=award.id).count()
            award_dict['verifiers_count'] = verifiers_count
            awards_data.append(award_dict)
        
        # Prepare response
        response = {
            'items': awards_data,
            'total': total,
            'page': page,
            'pages': (total + page_size - 1) // page_size,
            'page_size': page_size
        }
        
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.exception("Error listing awards with parameters")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/awards/<award_id>', methods=['GET'])
@jwt_required()
def get_award(award_id):
    """Get a specific research award."""
    award = Awards.query.get_or_404(award_id)
    data = award_schema.dump(award)
    # Add PDF URLs if available
    if award.full_paper_path:
        data['pdf_url'] = f"/api/v1/research/awards/{award_id}/pdf"
    if award.forwarding_letter_path:
        data['forwarding_pdf_url'] = f"/api/v1/research/awards/{award_id}/forwarding_pdf"
    return jsonify(data), 200

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


@research_bp.route('/awards/status', methods=['GET'])
@jwt_required()
def get_award_submission_status():
    """Get submission status of awards for the current user."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)

    if user.has_role(Role.ADMIN.value) or user.has_role(Role.SUPERADMIN.value):
        # Admins can see all awards
        awards = Awards.query
    elif user.has_role(Role.VERIFIER.value):
        # Verifiers can see awards assigned to them
        awards = db.session.query(Awards).join(
            AwardVerifiers, Awards.id == AwardVerifiers.award_id
        ).filter(
            AwardVerifiers.user_id == current_user_id
        )
    else:
        awards = Awards.query.filter_by(created_by_id=current_user_id)

    pending_awards = awards.filter(Awards.status==Status.PENDING).count()
    under_review_awards = awards.filter(Awards.status==Status.UNDER_REVIEW).count()
    accepted_awards = awards.filter(Awards.status==Status.ACCEPTED).count()
    rejected_awards = awards.filter(Awards.status==Status.REJECTED).count()

    return jsonify({
        "pending": pending_awards,
        "under_review": under_review_awards,
        "accepted": accepted_awards,
        "rejected": rejected_awards
    }), 200


# Verifier Management Routes for Awards

@research_bp.route('/awards/<award_id>/verifiers/<user_id>', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def assign_verifier_to_award(award_id, user_id):
    """Assign a verifier to an award."""
    try:
        # Check if award exists
        award = Awards.query.get_or_404(award_id)
        
        # Check if user exists and is a verifier
        user = User.query.get_or_404(user_id)
        if not user.has_role(Role.VERIFIER.value):
            return jsonify({"error": "User is not a verifier"}), 400
        
        # Check if already assigned
        existing_assignment = AwardVerifiers.query.filter_by(
            award_id=award_id, user_id=user_id).first()
        
        if existing_assignment:
            return jsonify({"message": "Verifier already assigned to this award"}), 200
        
        # Create new assignment
        assignment = AwardVerifiers(
            award_id=award_id,
            user_id=user_id
        )
        db.session.add(assignment)
        db.session.commit()
        
        return jsonify({"message": "Verifier assigned successfully"}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error assigning verifier to award")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/awards/<award_id>/verifiers/<user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def unassign_verifier_from_award(award_id, user_id):
    """Unassign a verifier from an award."""
    try:
        # Check if award exists
        award = Awards.query.get_or_404(award_id)
        
        # Check if assignment exists
        assignment = AwardVerifiers.query.filter_by(
            award_id=award_id, user_id=user_id).first_or_404()
        
        db.session.delete(assignment)
        db.session.commit()
        
        return jsonify({"message": "Verifier unassigned successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error unassigning verifier from award")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/awards/<award_id>/verifiers', methods=['GET'])
@jwt_required()
def get_verifiers_for_award(award_id):
    """Get all verifiers assigned to an award."""
    try:
        # Check if award exists
        award = Awards.query.get_or_404(award_id)
        
        # Get all verifiers for this award
        verifiers = db.session.query(User).join(
            AwardVerifiers, User.id == AwardVerifiers.user_id
        ).filter(
            AwardVerifiers.award_id == award_id
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
        current_app.logger.exception("Error getting verifiers for award")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/verifiers/<user_id>/awards', methods=['GET'])
@jwt_required()
def get_awards_for_verifier(user_id):
    """Get all awards assigned to a verifier."""
    try:
        # Check if user exists
        user = User.query.get_or_404(user_id)
        
        # Get all awards assigned to this verifier
        awards = db.session.query(Awards).join(
            AwardVerifiers, Awards.id == AwardVerifiers.award_id
        ).filter(
            AwardVerifiers.user_id == user_id
        ).all()
        
        return jsonify(awards_schema.dump(awards)), 200
    except Exception as e:
        current_app.logger.exception("Error getting awards for verifier")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/awards/bulk-assign-verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_assign_verifiers_to_awards():
    """Bulk assign verifiers to multiple awards."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'award_ids' not in data or 'user_ids' not in data:
            return jsonify({"error": "Missing award_ids or user_ids in request"}), 400
        
        award_ids = data['award_ids']
        user_ids = data['user_ids']
        
        # Validate that all awards and users exist
        awards = Awards.query.filter(Awards.id.in_(award_ids)).all()
        users = User.query.filter(User.id.in_(user_ids)).all()
        
        # Check if all users are verifiers
        non_verifiers = [user for user in users if not user.has_role(Role.VERIFIER.value)]
        if non_verifiers:
            return jsonify({"error": "Some users are not verifiers"}), 400
        
        # Create assignments
        assignments_created = 0
        for award_id in award_ids:
            for user_id in user_ids:
                # Check if already assigned
                existing_assignment = AwardVerifiers.query.filter_by(
                    award_id=award_id, user_id=user_id).first()
                
                if not existing_assignment:
                    assignment = AwardVerifiers(
                        award_id=award_id,
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
        current_app.logger.exception("Error in bulk assigning verifiers to awards")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/awards/bulk-unassign-verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_unassign_verifiers_from_awards():
    """Bulk unassign verifiers from multiple awards."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'award_ids' not in data or 'user_ids' not in data:
            return jsonify({"error": "Missing award_ids or user_ids in request"}), 400
        
        award_ids = data['award_ids']
        user_ids = data['user_ids']
        
        # Delete assignments
        assignments_deleted = AwardVerifiers.query.filter(
            AwardVerifiers.award_id.in_(award_ids),
            AwardVerifiers.user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully deleted {assignments_deleted} assignments",
            "assignments_deleted": assignments_deleted
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error in bulk unassigning verifiers from awards")
        return jsonify({"error": str(e)}), 400
