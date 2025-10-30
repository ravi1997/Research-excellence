from flask import send_file, abort
# Route to serve the PDF file for an abstract

import json
import uuid
from typing import Dict, Optional, Tuple

from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import or_

from app.extensions import db
from app.models.Cycle import (
    AbstractAuthors,
    Abstracts,
    Author,
)
from app.models.Token import Token
from app.models.User import User
from app.models.enumerations import Role, Status
from app.routes.v1.research import research_bp
from app.schemas.abstract_schema import AbstractSchema
from app.utils.decorator import require_roles
from app.utils.model_utils import abstract_utils, audit_log_utils, token_utils
from app.utils.model_utils import author_utils
from app.utils.services.mail import send_mail
from app.utils.services.sms import send_sms

abstract_schema = AbstractSchema()
abstracts_schema = AbstractSchema(many=True)


def _resolve_actor_context(action: str) -> Tuple[Optional[str], Dict[str, object]]:
    """
    Resolve the acting user and build a context payload that reuses the shared
    token utilities so every route benefits from consistent logging.
    """

    actor_identity = get_jwt_identity()
    actor_id = str(actor_identity) if actor_identity is not None else None
    jwt_payload = get_jwt()
    token_jti: Optional[str] = jwt_payload.get("jti") if jwt_payload else None

    filters = [Token.jti == token_jti] if token_jti else [Token.id == 0]
    tokens = token_utils.list_tokens(
        filters=filters,
        actor_id=actor_id,
        context={"route": action, "token_jti": token_jti or "none"},
    )

    context: Dict[str, object] = {"route": action}
    if actor_id:
        context["actor_id"] = actor_id
    if token_jti:
        context["token_jti"] = token_jti
    if tokens:
        context["token_record_id"] = tokens[0].id

    return actor_id, context

@research_bp.route('/abstracts', methods=['POST'])
@jwt_required()
@require_roles(Role.USER.value,Role.ADMIN.value, Role.SUPERADMIN.value)
def create_abstract():
    """Create a new research abstract."""
    actor_id, context = _resolve_actor_context("create_abstract")
    if actor_id is None:
        return jsonify({"error": "Unable to resolve actor identity"}), 400

    pdf_path: Optional[str] = None

    try:
        if request.is_json:
            payload = request.get_json() or {}
            if not isinstance(payload, dict):
                return jsonify({"error": "Invalid payload"}), 400
        else:
            data_json = request.form.get("data")
            if not data_json:
                return jsonify({"error": "No data provided"}), 400
            try:
                payload = json.loads(data_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400

            pdf_file = request.files.get("abstract_pdf")
            if pdf_file:
                upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
                import os
                from werkzeug.utils import secure_filename

                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(pdf_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                pdf_file.save(file_path)
                current_app.logger.info("PDF file saved to: %s", file_path)
                pdf_path = file_path.replace("app/", "", 1)

        authors_data = payload.pop("authors", []) or []
        payload["created_by_id"] = actor_id
        if pdf_path:
            payload["pdf_path"] = pdf_path

        abstract = abstract_utils.create_abstract(
            commit=False,
            actor_id=actor_id,
            context=context,
            **payload,
        )

        db.session.flush()

        if authors_data:
            for index, author_data in enumerate(authors_data):
                author = author_utils.create_author(
                    commit=False,
                    actor_id=actor_id,
                    context={**context, "author_index": index},
                    name=author_data.get("name", ""),
                    email=author_data.get("email"),
                    affiliation=author_data.get("affiliation"),
                    is_presenter=author_data.get("is_presenter", False),
                    is_corresponding=author_data.get("is_corresponding", False),
                )
                db.session.flush()
                db.session.add(
                    AbstractAuthors(
                        abstract_id=abstract.id,
                        author_id=author.id,
                        author_order=index,
                    )
                )
                current_app.logger.info(
                    "Added author %s with ID %s to abstract %s",
                    author.name,
                    author.id,
                    abstract.id,
                )

        db.session.commit()

        user = User.query.get(actor_id)
        if user:
            if getattr(user, "mobile", None):
                send_sms(
                    user.mobile,
                    f"Your abstract id : {abstract.id} has been created successfully and is pending submission for review.",
                )
            if getattr(user, "email", None):
                send_mail(
                    user.email,
                    "Abstract Created Successfully",
                    f"Dear {user.username},\n\nYour abstract with ID {abstract.id} has been created successfully and is pending submission for review.\n Details:\nTitle: {abstract.title}\nAbstract ID: {abstract.id}\n\nBest regards,\nResearch Section,AIIMS",
                )

        audit_log_utils.record_event(
            event="abstract.create.success",
            user_id=actor_id,
            target_user_id=actor_id,
            detail=f"Abstract ID: {abstract.id}",
        )
        return jsonify(abstract_schema.dump(abstract)), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creating abstract")
        audit_log_utils.record_event(
            event="abstract.create.failure",
            user_id=actor_id,
            target_user_id=actor_id,
            detail=f"Abstract creation failed: {exc}",
        )
        return jsonify({"error": str(exc)}), 400


@research_bp.route('/abstracts/<abstract_id>', methods=['PUT'])
@jwt_required()
def update_abstract(abstract_id):
    """Update a research abstract."""
    actor_id, context = _resolve_actor_context("update_abstract")
    abstract = abstract_utils.get_abstract_by_id(
        abstract_id,
        actor_id=actor_id,
        context=context,
    )
    if abstract is None:
        abort(404, description="Abstract not found")

    pdf_path: Optional[str] = None

    try:
        if request.is_json:
            payload = request.get_json() or {}
            if not isinstance(payload, dict):
                return jsonify({"error": "Invalid payload"}), 400
        else:
            data_json = request.form.get("data")
            if not data_json:
                return jsonify({"error": "No data provided"}), 400
            try:
                payload = json.loads(data_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400

            pdf_file = request.files.get("abstract_pdf")
            if pdf_file:
                upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
                import os
                from werkzeug.utils import secure_filename

                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(pdf_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                pdf_file.save(file_path)
                current_app.logger.info("PDF file saved to: %s", file_path)
                pdf_path = file_path.replace("app/", "", 1)

        authors_data = payload.pop("authors", [])
        if pdf_path:
            payload["pdf_path"] = pdf_path

        abstract = abstract_utils.update_abstract(
            abstract,
            commit=False,
            actor_id=actor_id,
            context=context,
            **payload,
        )

        prev_assocs = AbstractAuthors.query.filter_by(abstract_id=abstract.id).all()
        for assoc in prev_assocs:
            author = Author.query.get(assoc.author_id)
            db.session.delete(assoc)
            if author:
                other_assoc = AbstractAuthors.query.filter(
                    AbstractAuthors.author_id == author.id,
                    AbstractAuthors.abstract_id != abstract.id,
                ).first()
                if not other_assoc:
                    author_utils.delete_author(
                        author,
                        commit=False,
                        actor_id=actor_id,
                        context={**context, "operation": "purge_author"},
                    )

        if authors_data:
            for index, author_data in enumerate(authors_data):
                author = author_utils.create_author(
                    commit=False,
                    actor_id=actor_id,
                    context={**context, "author_index": index},
                    name=author_data.get("name", ""),
                    email=author_data.get("email"),
                    affiliation=author_data.get("affiliation"),
                    is_presenter=author_data.get("is_presenter", False),
                    is_corresponding=author_data.get("is_corresponding", False),
                )
                db.session.flush()
                db.session.add(
                    AbstractAuthors(
                        abstract_id=abstract.id,
                        author_id=author.id,
                        author_order=index,
                    )
                )

        db.session.commit()
        audit_log_utils.record_event(
            event="abstract.update.success",
            user_id=actor_id,
            detail=f"Abstract updated ID: {abstract.id}",
        )
        return jsonify(abstract_schema.dump(abstract)), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error updating abstract")
        audit_log_utils.record_event(
            event="abstract.update.failure",
            user_id=actor_id,
            detail=f"Abstract update failed ID {abstract_id}: {exc}",
        )
        return jsonify({"error": str(exc)}), 400


@research_bp.route('/abstracts/<abstract_id>/pdf', methods=['GET'])
@jwt_required()
def get_abstract_pdf(abstract_id):
    actor_id, context = _resolve_actor_context("get_abstract_pdf")
    abstract = abstract_utils.get_abstract_by_id(
        abstract_id,
        actor_id=actor_id,
        context=context,
    )
    if abstract is None:
        audit_log_utils.record_event(
            event="abstract.pdf.missing",
            user_id=actor_id,
            detail=f"Abstract not found ID: {abstract_id}",
        )
        abort(404, description="Abstract not found.")

    if not abstract.pdf_path:
        audit_log_utils.record_event(
            event="abstract.pdf.missing",
            user_id=actor_id,
            detail=f"No PDF for abstract ID: {abstract_id}",
        )
        abort(404, description="No PDF uploaded for this abstract.")

    try:
        audit_log_utils.record_event(
            event="abstract.pdf.fetch",
            user_id=actor_id,
            detail=f"Served PDF for abstract ID: {abstract_id}",
        )
        return send_file(abstract.pdf_path, mimetype='application/pdf', as_attachment=False)
    except Exception:
        current_app.logger.exception("Error sending PDF file")
        audit_log_utils.record_event(
            event="abstract.pdf.error",
            user_id=actor_id,
            detail=f"Failed to send PDF for abstract ID: {abstract_id}",
        )
        abort(404, description="PDF file not found.")

@research_bp.route('/abstracts', methods=['GET'])
@jwt_required()
def get_abstracts():
    """Get all research abstracts with filtering and pagination support."""
    actor_id, context = _resolve_actor_context("get_abstracts")
    try:
        q = request.args.get('q', '').strip()
        verifiers = request.args.get('verifiers', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        status = request.args.get('status', '').strip().upper()
        page_size = min(int(request.args.get('page_size', 20)), 100)
        sort_by = request.args.get('sort_by', 'id')
        sort_dir = request.args.get('sort_dir', 'desc').lower()
        verifier_filter = request.args.get('verifier', '').strip().lower() == 'true'

        filters = []
        if q:
            q_int = int(q) if q.isdigit() else None
            filters.append(
                or_(
                    Abstracts.title.ilike(f'%{q}%'),
                    Abstracts.content.ilike(f'%{q}%'),
                    Abstracts.abstract_number == q_int,
                )
            )

        if status in {'PENDING', 'UNDER_REVIEW', 'ACCEPTED', 'REJECTED'}:
            filters.append(Abstracts.status == Status[status])

        user = User.query.filter_by(id=actor_id).first()
        if user is None:
            return jsonify({"error": "User not found"}), 404

        privileged = any(
            user.has_role(role)
            for role in (
                Role.ADMIN.value,
                Role.SUPERADMIN.value,
                Role.VERIFIER.value,
                Role.COORDINATOR.value,
            )
        )
        if not privileged:
            filters.append(Abstracts.created_by_id == actor_id)

        if verifiers:
            if verifiers.lower() == 'yes':
                filters.append(Abstracts.verifiers.any())
            elif verifiers.lower() == 'no':
                filters.append(~Abstracts.verifiers.any())

        if verifier_filter and actor_id:
            filters.append(Abstracts.verifiers.any(User.id == actor_id))

        if sort_by == 'title':
            order_by = Abstracts.title.asc() if sort_dir == 'asc' else Abstracts.title.desc()
        elif sort_by == 'created_at':
            order_by = Abstracts.created_at.asc() if sort_dir == 'asc' else Abstracts.created_at.desc()
        else:
            order_by = Abstracts.id.asc() if sort_dir == 'asc' else Abstracts.id.desc()

        abstracts_all = list(
            abstract_utils.list_abstracts(
                filters=filters,
                order_by=order_by,
                actor_id=actor_id,
                context={**context, "sort_by": sort_by, "sort_dir": sort_dir},
            )
        )

        total = len(abstracts_all)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = abstracts_all[start:end]

        abstracts_data = []
        for abstract in paginated:
            abstract_dict = abstract_schema.dump(abstract)
            abstract_dict['verifiers_count'] = len(abstract.verifiers or [])
            abstracts_data.append(abstract_dict)

        response = {
            'items': abstracts_data,
            'total': total,
            'page': page,
            'pages': (total + page_size - 1) // page_size,
            'page_size': page_size
        }

        audit_log_utils.record_event(
            event="abstract.list.success",
            user_id=actor_id,
            detail=f"Returned {len(abstracts_data)} of {total} abstracts",
        )
        return jsonify(response), 200
    except Exception as exc:
        current_app.logger.exception("Error listing abstracts with parameters")
        audit_log_utils.record_event(
            event="abstract.list.failure",
            user_id=actor_id,
            detail=f"Failed to list abstracts: {exc}",
        )
        return jsonify({"error": str(exc)}), 400

@research_bp.route('/abstracts/<abstract_id>', methods=['GET'])
@jwt_required()
def get_abstract(abstract_id):
    """Get a specific research abstract."""
    actor_id, context = _resolve_actor_context("get_abstract")
    abstract = abstract_utils.get_abstract_by_id(
        abstract_id,
        actor_id=actor_id,
        context=context,
    )
    if abstract is None:
        audit_log_utils.record_event(
            event="abstract.get.missing",
            user_id=actor_id,
            detail=f"Abstract not found ID: {abstract_id}",
        )
        abort(404, description="Abstract not found.")

    data = abstract_schema.dump(abstract)
    if abstract.pdf_path:
        data['pdf_url'] = f"/api/v1/research/abstracts/{abstract_id}/pdf"

    audit_log_utils.record_event(
        event="abstract.get.success",
        user_id=actor_id,
        detail=f"Fetched abstract ID: {abstract_id}",
    )
    return jsonify(data), 200
@research_bp.route('/abstracts/<abstract_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_abstract(abstract_id):
    """Delete a research abstract."""
    actor_id, context = _resolve_actor_context("delete_abstract")
    abstract = abstract_utils.get_abstract_by_id(
        abstract_id,
        actor_id=actor_id,
        context=context,
    )
    if abstract is None:
        audit_log_utils.record_event(
            event="abstract.delete.missing",
            user_id=actor_id,
            detail=f"Abstract not found ID: {abstract_id}",
        )
        abort(404, description="Abstract not found.")
    try:
        abstract_utils.delete_abstract(
            abstract,
            actor_id=actor_id,
            context=context,
        )
        audit_log_utils.record_event(
            event="abstract.delete.success",
            user_id=actor_id,
            detail=f"Deleted abstract ID: {abstract_id}",
        )
        return jsonify({"message": "Abstract deleted"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error deleting abstract")
        audit_log_utils.record_event(
            event="abstract.delete.failure",
            user_id=actor_id,
            detail=f"Failed to delete abstract ID {abstract_id}: {exc}",
        )
        return jsonify({"error": str(exc)}), 400

@research_bp.route('/abstracts/<abstract_id>/submit', methods=['POST'])
@jwt_required()
def submit_abstract(abstract_id):
    """Submit an abstract for review."""
    actor_id, context = _resolve_actor_context("submit_abstract")
    abstract = abstract_utils.get_abstract_by_id(
        abstract_id,
        actor_id=actor_id,
        context=context,
    )
    if abstract is None:
        audit_log_utils.record_event(
            event="abstract.submit.missing",
            user_id=actor_id,
            detail=f"Abstract not found ID: {abstract_id}",
        )
        abort(404, description="Abstract not found.")

    try:
        abstract_utils.update_abstract(
            abstract,
            actor_id=actor_id,
            context=context,
            status=Status.UNDER_REVIEW,
        )
        audit_log_utils.record_event(
            event="abstract.submit.success",
            user_id=actor_id,
            detail=f"Abstract submitted ID: {abstract_id}",
        )
        return jsonify({"message": "Abstract submitted for review"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error submitting abstract")
        audit_log_utils.record_event(
            event="abstract.submit.failure",
            user_id=actor_id,
            detail=f"Failed to submit abstract ID {abstract_id}: {exc}",
        )
        return jsonify({"error": str(exc)}), 400
    

@research_bp.route('/abstracts/status', methods=['GET'])
@jwt_required()
def get_abstract_submission_status():
    """Get submission status of abstracts for the current user."""
    actor_id, context = _resolve_actor_context("get_abstract_submission_status")
    user = User.query.get(actor_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    try:
        if user.has_role(Role.ADMIN.value) or user.has_role(Role.SUPERADMIN.value):
            abstracts = abstract_utils.list_abstracts(
                actor_id=actor_id,
                context=context,
            )
        elif user.has_role(Role.VERIFIER.value):
            current_app.logger.info("Fetching abstracts for verifier user ID: %s", actor_id)
            abstracts = abstract_utils.list_abstracts(
                filters=[Abstracts.verifiers.any(User.id == actor_id)],
                actor_id=actor_id,
                context={**context, "scope": "verifier"},
            )
        else:
            abstracts = abstract_utils.list_abstracts(
                filters=[Abstracts.created_by_id == actor_id],
                actor_id=actor_id,
                context={**context, "scope": "owner"},
            )

        pending_abstracts = sum(1 for abstract in abstracts if abstract.status == Status.PENDING)
        under_review_abstracts = sum(1 for abstract in abstracts if abstract.status == Status.UNDER_REVIEW)
        accepted_abstracts = sum(1 for abstract in abstracts if abstract.status == Status.ACCEPTED)
        rejected_abstracts = sum(1 for abstract in abstracts if abstract.status == Status.REJECTED)

        payload = {
            "pending": pending_abstracts,
            "under_review": under_review_abstracts,
            "accepted": accepted_abstracts,
            "rejected": rejected_abstracts,
        }

        audit_log_utils.record_event(
            event="abstract.status.success",
            user_id=actor_id,
            detail=json.dumps(payload),
        )
        return jsonify(payload), 200
    except Exception as exc:
        current_app.logger.exception("Error retrieving abstract submission status")
        audit_log_utils.record_event(
            event="abstract.status.failure",
            user_id=actor_id,
            detail=f"Failed to retrieve status: {exc}",
        )
        return jsonify({"error": str(exc)}), 400


# Verifier Management Routes

@research_bp.route('/abstracts/<abstract_id>/verifiers/<user_id>', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def assign_verifier_to_abstract(abstract_id, user_id):
    """Assign a verifier to an abstract."""
    actor_id, context = _resolve_actor_context("assign_verifier_to_abstract")
    try:
        abstract = abstract_utils.get_abstract_by_id(
            abstract_id,
            actor_id=actor_id,
            context=context,
        )
        if abstract is None:
            audit_log_utils.record_event(
                event="abstract.verifier.assign.missing_abstract",
                user_id=actor_id,
                detail=f"Abstract not found ID: {abstract_id}",
            )
            abort(404, description="Abstract not found.")

        user = User.query.get(user_id)
        if user is None:
            audit_log_utils.record_event(
                event="abstract.verifier.assign.missing_user",
                user_id=actor_id,
                detail=f"Verifier not found ID: {user_id}",
            )
            abort(404, description="User not found.")

        if not user.has_role(Role.VERIFIER.value):
            return jsonify({"error": "User is not a verifier"}), 400

        if any(verifier.id == user.id for verifier in abstract.verifiers):
            return jsonify({"message": "Verifier already assigned to this abstract"}), 200

        abstract_utils.assign_verifier(
            abstract,
            user,
            actor_id=actor_id,
            context={**context, "verifier_id": str(user_id)},
        )

        audit_log_utils.record_event(
            event="abstract.verifier.assign.success",
            user_id=actor_id,
            target_user_id=str(user.id),
            detail=f"Assigned verifier {user_id} to abstract {abstract_id}",
        )

        return jsonify({"message": "Verifier assigned successfully"}), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error assigning verifier to abstract")
        audit_log_utils.record_event(
            event="abstract.verifier.assign.failure",
            user_id=actor_id,
            detail=f"Failed to assign verifier {user_id} to abstract {abstract_id}: {exc}",
        )
        return jsonify({"error": str(exc)}), 400


@research_bp.route('/abstracts/<abstract_id>/verifiers/<user_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def unassign_verifier_from_abstract(abstract_id, user_id):
    """Unassign a verifier from an abstract."""
    actor_id, context = _resolve_actor_context("unassign_verifier_from_abstract")
    try:
        abstract = abstract_utils.get_abstract_by_id(
            abstract_id,
            actor_id=actor_id,
            context=context,
        )
        if abstract is None:
            audit_log_utils.record_event(
                event="abstract.verifier.unassign.missing_abstract",
                user_id=actor_id,
                detail=f"Abstract not found ID: {abstract_id}",
            )
            abort(404, description="Abstract not found.")

        user = User.query.get(user_id)
        if user is None:
            audit_log_utils.record_event(
                event="abstract.verifier.unassign.missing_user",
                user_id=actor_id,
                detail=f"Verifier not found ID: {user_id}",
            )
            abort(404, description="User not found.")

        if not any(verifier.id == user.id for verifier in abstract.verifiers):
            return jsonify({"error": "Verifier not assigned to this abstract"}), 404

        abstract_utils.remove_verifier(
            abstract,
            user,
            actor_id=actor_id,
            context={**context, "verifier_id": str(user_id)},
        )

        audit_log_utils.record_event(
            event="abstract.verifier.unassign.success",
            user_id=actor_id,
            target_user_id=str(user.id),
            detail=f"Unassigned verifier {user_id} from abstract {abstract_id}",
        )

        return jsonify({"message": "Verifier unassigned successfully"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error unassigning verifier from abstract")
        audit_log_utils.record_event(
            event="abstract.verifier.unassign.failure",
            user_id=actor_id,
            detail=f"Failed to unassign verifier {user_id} from abstract {abstract_id}: {exc}",
        )
        return jsonify({"error": str(exc)}), 400


@research_bp.route('/abstracts/<abstract_id>/verifiers', methods=['GET'])
@jwt_required()
def get_verifiers_for_abstract(abstract_id):
    """Get all verifiers assigned to an abstract."""
    actor_id, context = _resolve_actor_context("get_verifiers_for_abstract")
    try:
        abstract = abstract_utils.get_abstract_by_id(
            abstract_id,
            actor_id=actor_id,
            context=context,
        )
        if abstract is None:
            audit_log_utils.record_event(
                event="abstract.verifier.list.missing_abstract",
                user_id=actor_id,
                detail=f"Abstract not found ID: {abstract_id}",
            )
            abort(404, description="Abstract not found.")

        verifiers_data = [
            {
                'id': str(verifier.id),
                'username': verifier.username,
                'email': verifier.email,
                'employee_id': verifier.employee_id,
            }
            for verifier in abstract.verifiers
        ]

        audit_log_utils.record_event(
            event="abstract.verifier.list.success",
            user_id=actor_id,
            detail=f"Verifier count {len(verifiers_data)} for abstract {abstract_id}",
        )
        return jsonify(verifiers_data), 200
    except Exception as exc:
        current_app.logger.exception("Error getting verifiers for abstract")
        audit_log_utils.record_event(
            event="abstract.verifier.list.failure",
            user_id=actor_id,
            detail=f"Failed to get verifiers for abstract {abstract_id}: {exc}",
        )
        return jsonify({"error": str(exc)}), 400


@research_bp.route('/verifiers/<user_id>/abstracts', methods=['GET'])
@jwt_required()
def get_abstracts_for_verifier(user_id):
    """Get all abstracts assigned to a verifier."""
    actor_id, context = _resolve_actor_context("get_abstracts_for_verifier")
    try:
        user = User.query.get(user_id)
        if user is None:
            audit_log_utils.record_event(
                event="abstract.verifier.abstracts.missing_user",
                user_id=actor_id,
                detail=f"Verifier not found ID: {user_id}",
            )
            abort(404, description="User not found.")

        abstracts = abstract_utils.list_abstracts(
            filters=[Abstracts.verifiers.any(User.id == user_id)],
            actor_id=actor_id,
            context={**context, "target_verifier": str(user_id)},
        )

        audit_log_utils.record_event(
            event="abstract.verifier.abstracts.success",
            user_id=actor_id,
            detail=f"Returned {len(abstracts)} abstracts for verifier {user_id}",
        )

        return jsonify(abstracts_schema.dump(abstracts)), 200
    except Exception as exc:
        current_app.logger.exception("Error getting abstracts for verifier")
        audit_log_utils.record_event(
            event="abstract.verifier.abstracts.failure",
            user_id=actor_id,
            detail=f"Failed to fetch abstracts for verifier {user_id}: {exc}",
        )
        return jsonify({"error": str(exc)}), 400


@research_bp.route('/abstracts/bulk-assign-verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_assign_verifiers():
    """Bulk assign verifiers to multiple abstracts."""
    actor_id, context = _resolve_actor_context("bulk_assign_verifiers")
    try:
        data = request.get_json() or {}
        abstract_ids = data.get('abstract_ids')
        user_ids = data.get('user_ids')

        if not abstract_ids or not user_ids:
            return jsonify({"error": "Missing abstract_ids or user_ids in request"}), 400

        abstract_ids = [str(abstract_id) for abstract_id in abstract_ids]
        user_ids = [str(user_id) for user_id in user_ids]

        abstracts = abstract_utils.list_abstracts(
            filters=[Abstracts.id.in_(abstract_ids)],
            actor_id=actor_id,
            context={**context, "operation": "bulk_assign"},
        )
        abstracts_by_id = {str(abstract.id): abstract for abstract in abstracts}
        missing_abstracts = [abstract_id for abstract_id in abstract_ids if abstract_id not in abstracts_by_id]
        if missing_abstracts:
            return jsonify({"error": f"Abstracts not found: {', '.join(missing_abstracts)}"}), 404

        users = User.query.filter(User.id.in_(user_ids)).all()
        if len(users) != len(set(user_ids)):
            found_ids = {str(user.id) for user in users}
            missing_ids = [uid for uid in user_ids if uid not in found_ids]
            return jsonify({"error": f"Users not found: {', '.join(missing_ids)}"}), 404

        non_verifiers = [user for user in users if not user.has_role(Role.VERIFIER.value)]
        if non_verifiers:
            return jsonify({"error": "Some users are not verifiers"}), 400

        assignments_created = 0
        for abstract_id in abstract_ids:
            abstract = abstracts_by_id[str(abstract_id)]
            for user in users:
                if any(verifier.id == user.id for verifier in abstract.verifiers):
                    continue
                abstract_utils.assign_verifier(
                    abstract,
                    user,
                    actor_id=actor_id,
                    context={**context, "verifier_id": str(user.id), "abstract_id": str(abstract.id)},
                )
                assignments_created += 1

        audit_log_utils.record_event(
            event="abstract.verifier.bulk_assign.success",
            user_id=actor_id,
            detail=json.dumps(
                {
                    "abstract_ids": abstract_ids,
                    "user_ids": user_ids,
                    "created": assignments_created,
                }
            ),
        )
        return jsonify({
            "message": f"Successfully created {assignments_created} assignments",
            "assignments_created": assignments_created
        }), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error in bulk assigning verifiers")
        audit_log_utils.record_event(
            event="abstract.verifier.bulk_assign.failure",
            user_id=actor_id,
            detail=f"Bulk assign failed: {exc}",
        )
        return jsonify({"error": str(exc)}), 400


@research_bp.route('/abstracts/bulk-unassign-verifiers', methods=['POST'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def bulk_unassign_verifiers():
    """Bulk unassign verifiers from multiple abstracts."""
    actor_id, context = _resolve_actor_context("bulk_unassign_verifiers")
    try:
        data = request.get_json() or {}

        abstract_ids = data.get('abstract_ids')
        user_ids = data.get('user_ids')

        if not abstract_ids or not user_ids:
            return jsonify({"error": "Missing abstract_ids or user_ids in request"}), 400

        abstract_ids = [str(abstract_id) for abstract_id in abstract_ids]
        user_ids = [str(user_id) for user_id in user_ids]

        abstracts = abstract_utils.list_abstracts(
            filters=[Abstracts.id.in_(abstract_ids)],
            actor_id=actor_id,
            context={**context, "operation": "bulk_unassign"},
        )
        abstracts_by_id = {str(abstract.id): abstract for abstract in abstracts}
        missing_abstracts = [abstract_id for abstract_id in abstract_ids if abstract_id not in abstracts_by_id]
        if missing_abstracts:
            return jsonify({"error": f"Abstracts not found: {', '.join(missing_abstracts)}"}), 404

        users = User.query.filter(User.id.in_(user_ids)).all()
        if len(users) != len(set(user_ids)):
            found_ids = {str(user.id) for user in users}
            missing_ids = [uid for uid in user_ids if uid not in found_ids]
            return jsonify({"error": f"Users not found: {', '.join(missing_ids)}"}), 404

        assignments_deleted = 0
        for abstract_id in abstract_ids:
            abstract = abstracts_by_id[str(abstract_id)]
            for user in users:
                if any(verifier.id == user.id for verifier in abstract.verifiers):
                    abstract_utils.remove_verifier(
                        abstract,
                        user,
                        actor_id=actor_id,
                        context={**context, "verifier_id": str(user.id), "abstract_id": str(abstract.id)},
                    )
                    assignments_deleted += 1

        audit_log_utils.record_event(
            event="abstract.verifier.bulk_unassign.success",
            user_id=actor_id,
            detail=json.dumps(
                {
                    "abstract_ids": abstract_ids,
                    "user_ids": user_ids,
                    "deleted": assignments_deleted,
                }
            ),
        )

        return jsonify({
            "message": f"Successfully deleted {assignments_deleted} assignments",
            "assignments_deleted": assignments_deleted
        }), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error in bulk unassigning verifiers")
        audit_log_utils.record_event(
            event="abstract.verifier.bulk_unassign.failure",
            user_id=actor_id,
            detail=f"Bulk unassign failed: {exc}",
        )
        return jsonify({"error": str(exc)}), 400
