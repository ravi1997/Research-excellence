from flask import send_file, abort
# Route to serve the PDF file for an abstract

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from app.routes.v1.research import research_bp
from app.models.Cycle import Abstracts, Author, Category, Cycle, AbstractAuthors, AbstractVerifiers
from app.models.User import User
from app.schemas.abstract_schema import AbstractSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role, Status
import json
import uuid

abstract_schema = AbstractSchema()
abstracts_schema = AbstractSchema(many=True)

@research_bp.route('/abstracts', methods=['POST'])
@jwt_required()
def create_abstract():
    """Create a new research abstract."""
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            # Handle form data (for file uploads)
            # Get the JSON data from the form
            data_json = request.form.get('data')
            if not data_json:
                return jsonify({"error": "No data provided"}), 400
            
            try:
                data = json.loads(data_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400
            
            # Handle file upload if present
            pdf_file = request.files.get('abstract_pdf')
            pdf_path = None
            if pdf_file:
                # Save the PDF file to the upload folder specified in config
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                import os
                os.makedirs(upload_folder, exist_ok=True)
                # Secure the filename
                from werkzeug.utils import secure_filename
                filename = secure_filename(pdf_file.filename)
                # Add a UUID to the filename to avoid clashes
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                pdf_file.save(file_path)
                current_app.logger.info(f"PDF file saved to: {file_path}")
                pdf_path = file_path.replace("app/", "", 1)
        
        # Get the current user ID from JWT
        current_user_id = get_jwt_identity()
    

        # Extract authors from data if present
        authors_data = data.pop('authors', [])

        # Set created_by_id in data for schema load
        data['created_by_id'] = current_user_id

        # Load the abstract without authors
        abstract = abstract_schema.load(data)


        # Set pdf_path if file was uploaded
        if pdf_path and hasattr(abstract, 'pdf_path'):
            abstract.pdf_path = pdf_path
        db.session.add(abstract)
        db.session.flush()  # Get the abstract ID without committing

        # Handle authors
        if authors_data:
            for i, author_data in enumerate(authors_data):
                # Create or find author
                author = Author(
                    name=author_data.get('name', ''),
                    email=author_data.get('email'),
                    affiliation=author_data.get('affiliation'),
                    is_presenter=author_data.get('is_presenter', False),
                    is_corresponding=author_data.get('is_corresponding', False)
                )
                db.session.add(author)
                db.session.flush()  # Get the author ID

                # Create the association
                abstract_author = AbstractAuthors(
                    abstract_id=abstract.id,
                    author_id=author.id,
                    author_order=i
                )
                db.session.add(abstract_author)
                current_app.logger.info(f"Added author {author.name} with ID {author.id} to abstract {abstract.id}")

        db.session.commit()
        return jsonify(abstract_schema.dump(abstract)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating abstract")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/abstracts/<abstract_id>', methods=['PUT'])
@jwt_required()
def update_abstract(abstract_id):
    """Update a research abstract."""
    abstract = Abstracts.query.get_or_404(abstract_id)
    try:
        # Check if user is authorized to update this abstract
        current_user_id = get_jwt_identity()
        # In a real implementation, you might want to check if the user
        # is an author of the abstract or has admin privileges

        pdf_path = None
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            # Handle form data (for file uploads)
            data_json = request.form.get('data')
            if not data_json:
                return jsonify({"error": "No data provided"}), 400

            try:
                data = json.loads(data_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400

            # Handle file upload if present
            pdf_file = request.files.get('abstract_pdf')
            if pdf_file:
                # Save the PDF file to the upload folder specified in config
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                import os
                os.makedirs(upload_folder, exist_ok=True)
                from werkzeug.utils import secure_filename
                filename = secure_filename(pdf_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                pdf_file.save(file_path)
                current_app.logger.info(f"PDF file saved to: {file_path}")
                pdf_path = file_path.replace("app/", "", 1)

        # Extract authors from data if present
        authors_data = data.pop('authors', [])

        # Update the abstract
        abstract = abstract_schema.load(data, instance=abstract, partial=True)
        # Update pdf_path if a new file was uploaded
        if pdf_path and hasattr(abstract, 'pdf_path'):
            abstract.pdf_path = pdf_path

        # Remove previous authors and associations
        from app.models.Cycle import AbstractAuthors, Author
        prev_assocs = AbstractAuthors.query.filter_by(abstract_id=abstract.id).all()
        for assoc in prev_assocs:
            # Optionally delete the author record if not used elsewhere
            author = Author.query.get(assoc.author_id)
            db.session.delete(assoc)
            if author:
                # Check if author is associated with any other abstract
                other_assoc = AbstractAuthors.query.filter_by(author_id=author.id).first()
                if not other_assoc:
                    db.session.delete(author)

        # Add new authors and associations
        if authors_data:
            for i, author_data in enumerate(authors_data):
                author = Author(
                    name=author_data.get('name', ''),
                    email=author_data.get('email'),
                    affiliation=author_data.get('affiliation'),
                    is_presenter=author_data.get('is_presenter', False),
                    is_corresponding=author_data.get('is_corresponding', False)
                )
                db.session.add(author)
                db.session.flush()  # Get the author ID
                abstract_author = AbstractAuthors(
                    abstract_id=abstract.id,
                    author_id=author.id,
                    author_order=i
                )
                db.session.add(abstract_author)

        db.session.commit()
        return jsonify(abstract_schema.dump(abstract)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating abstract")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/abstracts/<abstract_id>/pdf', methods=['GET'])
@jwt_required()
def get_abstract_pdf(abstract_id):
    abstract = Abstracts.query.get_or_404(abstract_id)
    if not abstract.pdf_path:
        abort(404, description="No PDF uploaded for this abstract.")
    try:
        return send_file(abstract.pdf_path, mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        current_app.logger.exception("Error sending PDF file")
        abort(404, description="PDF file not found.")

@research_bp.route('/abstracts', methods=['GET'])
@jwt_required()
def get_abstracts():
    """Get all research abstracts with filtering and pagination support."""
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
        
        # Build query for abstracts
        query = Abstracts.query
        
        q_int = q.isdigit() and int(q) or None
        
        # Apply search filter
        if q:
            search_filter = db.or_(
                Abstracts.title.ilike(f'%{q}%'),
                Abstracts.content.ilike(f'%{q}%'),
                Abstracts.abstract_number == q_int
            )
            query = query.filter(search_filter)
        
        if status == 'PENDING' or status == 'UNDER_REVIEW' or status == 'ACCEPTED' or status == 'REJECTED':
            status_value = Status[status]
            query = query.filter(Abstracts.status == status_value)
            
        
        # Apply verifiers filter
        if verifiers:
            if verifiers.lower() == 'yes':
                # Only abstracts with assigned verifiers
                query = query.join(AbstractVerifiers, Abstracts.id == AbstractVerifiers.abstract_id)
            elif verifiers.lower() == 'no':
                # Only abstracts without assigned verifiers
                query = query.outerjoin(AbstractVerifiers, Abstracts.id == AbstractVerifiers.abstract_id).filter(AbstractVerifiers.abstract_id.is_(None))
        
        # Apply verifier filter (filter by current user if they are a verifier)
        if verifier_filter:
            current_user_id = get_jwt_identity()
            # Only show abstracts assigned to the current user (robust join)
            query = query.join(AbstractVerifiers, AbstractVerifiers.abstract_id == Abstracts.id)
            query = query.join(User, User.id == AbstractVerifiers.user_id)
            query = query.filter(AbstractVerifiers.user_id == current_user_id)
        
        # Apply sorting
        if sort_by == 'title':
            order_by = Abstracts.title.asc() if sort_dir.lower() == 'asc' else Abstracts.title.desc()
        elif sort_by == 'created_at':
            order_by = Abstracts.created_at.asc() if sort_dir.lower() == 'asc' else Abstracts.created_at.desc()
        else:  # default to id
            order_by = Abstracts.id.asc() if sort_dir.lower() == 'asc' else Abstracts.id.desc()
        
        query = query.order_by(order_by)
        
        # Apply pagination
        total = query.count()
        abstracts = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # Add verifiers count to each abstract
        abstracts_data = []
        for abstract in abstracts:
            abstract_dict = abstract_schema.dump(abstract)
            # Count verifiers assigned to this abstract
            verifiers_count = db.session.query(AbstractVerifiers).filter_by(abstract_id=abstract.id).count()
            abstract_dict['verifiers_count'] = verifiers_count
            abstracts_data.append(abstract_dict)
        
        # Prepare response
        response = {
            'items': abstracts_data,
            'total': total,
            'page': page,
            'pages': (total + page_size - 1) // page_size,
            'page_size': page_size
        }
        
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.exception("Error listing abstracts with parameters")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/abstracts/<abstract_id>', methods=['GET'])
@jwt_required()
def get_abstract(abstract_id):
    """Get a specific research abstract."""
    abstract = Abstracts.query.get_or_404(abstract_id)
    data = abstract_schema.dump(abstract)
    # Add PDF URL if available
    if abstract.pdf_path:
        data['pdf_url'] = f"/video/api/v1/research/abstracts/{abstract_id}/pdf"
    return jsonify(data), 200
@research_bp.route('/abstracts/<abstract_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_abstract(abstract_id):
    """Delete a research abstract."""
    abstract = Abstracts.query.get_or_404(abstract_id)
    try:
        db.session.delete(abstract)
        db.session.commit()
        return jsonify({"message": "Abstract deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting abstract")
        return jsonify({"error": str(e)}), 400

@research_bp.route('/abstracts/<abstract_id>/submit', methods=['POST'])
@jwt_required()
def submit_abstract(abstract_id):
    """Submit an abstract for review."""
    abstract = Abstracts.query.get_or_404(abstract_id)
    try:
        # Check if user is authorized to submit this abstract
        current_user_id = get_jwt_identity()
        # In a real implementation, you might want to check if the user
        # is an author of the abstract
        
        abstract.status = Status.UNDER_REVIEW
        db.session.commit()
        return jsonify({"message": "Abstract submitted for review"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error submitting abstract")
        return jsonify({"error": str(e)}), 400
    

@research_bp.route('/abstracts/status', methods=['GET'])
@jwt_required()
def get_abstract_submission_status():
    """Get submission status of abstracts for the current user."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    
    if user.has_role(Role.ADMIN.value) or user.has_role(Role.SUPERADMIN.value):
        # Admins can see all abstracts
        abstracts = Abstracts.query
    elif user.has_role(Role.VERIFIER.value):
        # Verifiers can see abstracts assigned to them
        abstracts = db.session.query(Abstracts).join(
            AbstractVerifiers, Abstracts.id == AbstractVerifiers.abstract_id
        ).filter(
            AbstractVerifiers.user_id == current_user_id
        )
    else:    
        abstracts = Abstracts.query.filter_by(created_by_id=current_user_id)

    pending_abstracts = abstracts.filter_by(status=Status.PENDING).count()
    under_review_abstracts = abstracts.filter_by(status=Status.UNDER_REVIEW).count()
    accepted_abstracts = abstracts.filter_by(status=Status.ACCEPTED).count()
    rejected_abstracts = abstracts.filter_by(status=Status.REJECTED).count()

    return jsonify({
        "pending": pending_abstracts,
        "under_review": under_review_abstracts,
        "accepted": accepted_abstracts,
        "rejected": rejected_abstracts
    }), 200


# Verifier Management Routes

@research_bp.route('/abstracts/<abstract_id>/verifiers/<user_id>', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def assign_verifier_to_abstract(abstract_id, user_id):
    """Assign a verifier to an abstract."""
    try:
        # Check if abstract exists
        abstract = Abstracts.query.get_or_404(abstract_id)
        
        # Check if user exists and is a verifier
        user = User.query.get_or_404(user_id)
        if not user.has_role(Role.VERIFIER.value):
            return jsonify({"error": "User is not a verifier"}), 400
        
        # Check if already assigned
        existing_assignment = AbstractVerifiers.query.filter_by(
            abstract_id=abstract_id, user_id=user_id).first()
        
        if existing_assignment:
            return jsonify({"message": "Verifier already assigned to this abstract"}), 200
        
        # Create new assignment
        assignment = AbstractVerifiers(
            abstract_id=abstract_id,
            user_id=user_id
        )
        db.session.add(assignment)
        db.session.commit()
        
        return jsonify({"message": "Verifier assigned successfully"}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error assigning verifier to abstract")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/abstracts/<abstract_id>/verifiers/<user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def unassign_verifier_from_abstract(abstract_id, user_id):
    """Unassign a verifier from an abstract."""
    try:
        # Check if abstract exists
        abstract = Abstracts.query.get_or_404(abstract_id)
        
        # Check if assignment exists
        assignment = AbstractVerifiers.query.filter_by(
            abstract_id=abstract_id, user_id=user_id).first_or_404()
        
        db.session.delete(assignment)
        db.session.commit()
        
        return jsonify({"message": "Verifier unassigned successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error unassigning verifier from abstract")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/abstracts/<abstract_id>/verifiers', methods=['GET'])
@jwt_required()
def get_verifiers_for_abstract(abstract_id):
    """Get all verifiers assigned to an abstract."""
    try:
        # Check if abstract exists
        abstract = Abstracts.query.get_or_404(abstract_id)
        
        # Get all verifiers for this abstract
        verifiers = db.session.query(User).join(
            AbstractVerifiers, User.id == AbstractVerifiers.user_id
        ).filter(
            AbstractVerifiers.abstract_id == abstract_id
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
        current_app.logger.exception("Error getting verifiers for abstract")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/verifiers/<user_id>/abstracts', methods=['GET'])
@jwt_required()
def get_abstracts_for_verifier(user_id):
    """Get all abstracts assigned to a verifier."""
    try:
        # Check if user exists
        user = User.query.get_or_404(user_id)
        
        # Get all abstracts assigned to this verifier
        abstracts = db.session.query(Abstracts).join(
            AbstractVerifiers, Abstracts.id == AbstractVerifiers.abstract_id
        ).filter(
            AbstractVerifiers.user_id == user_id
        ).all()
        
        return jsonify(abstracts_schema.dump(abstracts)), 200
    except Exception as e:
        current_app.logger.exception("Error getting abstracts for verifier")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/abstracts/bulk-assign-verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_assign_verifiers():
    """Bulk assign verifiers to multiple abstracts."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'abstract_ids' not in data or 'user_ids' not in data:
            return jsonify({"error": "Missing abstract_ids or user_ids in request"}), 400
        
        abstract_ids = data['abstract_ids']
        user_ids = data['user_ids']
        
        # Validate that all abstracts and users exist
        abstracts = Abstracts.query.filter(Abstracts.id.in_(abstract_ids)).all()
        users = User.query.filter(User.id.in_(user_ids)).all()
        
        # Check if all users are verifiers
        non_verifiers = [user for user in users if not user.has_role(Role.VERIFIER.value)]
        if non_verifiers:
            return jsonify({"error": "Some users are not verifiers"}), 400
        
        # Create assignments
        assignments_created = 0
        for abstract_id in abstract_ids:
            for user_id in user_ids:
                # Check if already assigned
                existing_assignment = AbstractVerifiers.query.filter_by(
                    abstract_id=abstract_id, user_id=user_id).first()
                
                if not existing_assignment:
                    assignment = AbstractVerifiers(
                        abstract_id=abstract_id,
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
        current_app.logger.exception("Error in bulk assigning verifiers")
        return jsonify({"error": str(e)}), 400


@research_bp.route('/abstracts/bulk-unassign-verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_unassign_verifiers():
    """Bulk unassign verifiers from multiple abstracts."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'abstract_ids' not in data or 'user_ids' not in data:
            return jsonify({"error": "Missing abstract_ids or user_ids in request"}), 400
        
        abstract_ids = data['abstract_ids']
        user_ids = data['user_ids']
        
        # Delete assignments
        assignments_deleted = AbstractVerifiers.query.filter(
            AbstractVerifiers.abstract_id.in_(abstract_ids),
            AbstractVerifiers.user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully deleted {assignments_deleted} assignments",
            "assignments_deleted": assignments_deleted
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error in bulk unassigning verifiers")
        return jsonify({"error": str(e)}), 400
