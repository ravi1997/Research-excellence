from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.v1.research import research_bp
from app.models.Cycle import Grading, GradingType, Abstracts, BestPaper, Awards
from app.schemas.grading_schema import GradingSchema
from app.extensions import db
from app.utils.decorator import require_roles
from app.models.enumerations import Role
from app.utils.model_utils import audit_log_utils
import json

grading_schema = GradingSchema()
gradings_schema = GradingSchema(many=True)

def log_audit_event(event_type, user_id, details, ip_address=None, target_user_id=None):
    """Helper function to create audit logs with proper transaction handling"""
    try:
        # Create audit log without committing to avoid transaction issues
        audit_log_utils.create_audit_log(
            event=event_type,
            user_id=user_id,
            target_user_id=target_user_id,
            ip=ip_address,
            detail=json.dumps(details) if isinstance(details, dict) else details,
            actor_id=user_id,
            commit=False  # Don't commit here to avoid transaction issues
        )
        db.session.commit() # Commit only this specific operation
    except Exception as e:
        current_app.logger.error(f"Failed to create audit log: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass  # Ignore rollback errors in error handling

@research_bp.route('/gradings', methods=['POST'])
@jwt_required()
@require_roles(Role.VERIFIER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def create_grading():
    """Create a new grading."""
    actor_id = get_jwt_identity()
    try:
        data = request.get_json()
        
        # Verify that the grading_type exists
        grading_type_id = data.get('grading_type_id')
        if grading_type_id:
            grading_type = GradingType.query.get(grading_type_id)
            if not grading_type:
                error_msg = "Grading type not found"
                log_audit_event(
                    event_type="grading.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "grading_type_id": grading_type_id},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 404
        
        # Validate that only one of the target entities is provided
        abstract_id = data.get('abstract_id')
        best_paper_id = data.get('best_paper_id')
        award_id = data.get('award_id')
        
        target_count = sum(1 for x in [abstract_id, best_paper_id, award_id] if x)
        if target_count != 1:
            error_msg = "Exactly one of abstract_id, best_paper_id, or award_id must be provided"
            log_audit_event(
                event_type="grading.create.failed",
                user_id=actor_id,
                details={"error": error_msg, "target_count": target_count},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400
        
        # Validate that the target entity exists
        if abstract_id:
            abstract = Abstracts.query.get(abstract_id)
            if not abstract:
                error_msg = "Abstract not found"
                log_audit_event(
                    event_type="grading.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "abstract_id": abstract_id},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 404
        elif best_paper_id:
            best_paper = BestPaper.query.get(best_paper_id)
            if not best_paper:
                error_msg = "Best paper not found"
                log_audit_event(
                    event_type="grading.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "best_paper_id": best_paper_id},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 404
        elif award_id:
            award = Awards.query.get(award_id)
            if not award:
                error_msg = "Award not found"
                log_audit_event(
                    event_type="grading.create.failed",
                    user_id=actor_id,
                    details={"error": error_msg, "award_id": award_id},
                    ip_address=request.remote_addr
                )
                return jsonify({"error": error_msg}), 404

        # Get the current user ID from JWT
        current_user_id = get_jwt_identity()
        data['graded_by_id'] = current_user_id

        # Marshmallow Schema (non SQLAlchemy) returns a dict; instantiate ORM model explicitly
        payload = grading_schema.load(data)
        grading = Grading(**payload)
        db.session.add(grading)
        db.session.commit()
        
        # Log successful creation
        log_audit_event(
            event_type="grading.create.success",
            user_id=actor_id,
            details={
                "grading_id": str(grading.id),
                "grading_type_id": grading_type_id,
                "score": grading.score,
                "review_phase": grading.review_phase,
                "target_entity": "abstract" if abstract_id else "best_paper" if best_paper_id else "award"
            },
            ip_address=request.remote_addr
        )
        
        return jsonify(grading_schema.dump(grading)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error creating grading")
        error_msg = str(e)
        log_audit_event(
            event_type="grading.create.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(e).__name__},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400

@research_bp.route('/gradings', methods=['GET'])
@jwt_required()
def get_gradings():
    """Get all gradings with optional filtering."""
    actor_id = get_jwt_identity()
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
        
        # Log successful retrieval
        log_audit_event(
            event_type="grading.list.success",
            user_id=actor_id,
            details={
                "grading_count": len(gradings),
                "filters_applied": {
                    "grading_type_id": grading_type_id,
                    "abstract_id": abstract_id,
                    "best_paper_id": best_paper_id,
                    "award_id": award_id,
                    "graded_by_id": graded_by_id
                }
            },
            ip_address=request.remote_addr
        )
        
        return jsonify(gradings_schema.dump(gradings)), 200
    except Exception as e:
        current_app.logger.exception("Error getting gradings")
        error_msg = str(e)
        log_audit_event(
            event_type="grading.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "exception_type": type(e).__name__},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400

@research_bp.route('/gradings/<grading_id>', methods=['GET'])
@jwt_required()
def get_grading(grading_id):
    """Get a specific grading."""
    actor_id = get_jwt_identity()
    try:
        grading = Grading.query.get_or_404(grading_id)
        
        # Log successful retrieval
        log_audit_event(
            event_type="grading.get.success",
            user_id=actor_id,
            details={
                "grading_id": grading_id,
                "grading_type_id": str(grading.grading_type_id),
                "score": grading.score,
                "review_phase": grading.review_phase
            },
            ip_address=request.remote_addr
        )
        
        return jsonify(grading_schema.dump(grading)), 200
    except Exception as e:
        current_app.logger.exception("Error getting grading")
        error_msg = str(e)
        log_audit_event(
            event_type="grading.get.failed",
            user_id=actor_id,
            details={"error": error_msg, "grading_id": grading_id, "exception_type": type(e).__name__},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400

@research_bp.route('/gradings/<grading_id>', methods=['PUT'])
@jwt_required()
@require_roles(Role.VERIFIER.value, Role.ADMIN.value, Role.SUPERADMIN.value)
def update_grading(grading_id):
    """Update a grading."""
    actor_id = get_jwt_identity()
    try:
        grading = Grading.query.get_or_404(grading_id)
        data = request.get_json()
        
        # Prevent changing the target entity or grading type
        if 'abstract_id' in data and data['abstract_id'] != str(grading.abstract_id):
            error_msg = "Cannot change target entity"
            log_audit_event(
                event_type="grading.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "grading_id": grading_id, "field": "abstract_id"},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400
        if 'best_paper_id' in data and data['best_paper_id'] != str(grading.best_paper_id):
            error_msg = "Cannot change target entity"
            log_audit_event(
                event_type="grading.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "grading_id": grading_id, "field": "best_paper_id"},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400
        if 'award_id' in data and data['award_id'] != str(grading.award_id):
            error_msg = "Cannot change target entity"
            log_audit_event(
                event_type="grading.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "grading_id": grading_id, "field": "award_id"},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400
        if 'grading_type_id' in data and data['grading_type_id'] != str(grading.grading_type_id):
            error_msg = "Cannot change grading type"
            log_audit_event(
                event_type="grading.update.failed",
                user_id=actor_id,
                details={"error": error_msg, "grading_id": grading_id, "field": "grading_type_id"},
                ip_address=request.remote_addr
            )
            return jsonify({"error": error_msg}), 400

        # Since GradingSchema is minimal and not SQLAlchemy-bound, apply allowed fields manually
        allowed = {'score', 'comments'}
        old_values = {}
        for k, v in data.items():
            if k in allowed:
                old_values[k] = getattr(grading, k)
                setattr(grading, k, v)
        db.session.commit()
        
        # Log successful update
        log_audit_event(
            event_type="grading.update.success",
            user_id=actor_id,
            details={
                "grading_id": grading_id,
                "old_values": old_values,
                "new_values": {k: v for k, v in data.items() if k in allowed}
            },
            ip_address=request.remote_addr
        )
        
        return jsonify(grading_schema.dump(grading)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error updating grading")
        error_msg = str(e)
        log_audit_event(
            event_type="grading.update.failed",
            user_id=actor_id,
            details={"error": error_msg, "grading_id": grading_id, "exception_type": type(e).__name__},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400

@research_bp.route('/gradings/<grading_id>', methods=['DELETE'])
@jwt_required()
@require_roles(Role.ADMIN.value, Role.SUPERADMIN.value)
def delete_grading(grading_id):
    """Delete a grading."""
    actor_id = get_jwt_identity()
    try:
        grading = Grading.query.get_or_404(grading_id)
        old_values = {
            "grading_type_id": str(grading.grading_type_id),
            "score": grading.score,
            "comments": grading.comments,
            "review_phase": grading.review_phase
        }
        db.session.delete(grading)
        db.session.commit()
        
        # Log successful deletion
        log_audit_event(
            event_type="grading.delete.success",
            user_id=actor_id,
            details={
                "grading_id": grading_id,
                "old_values": old_values
            },
            ip_address=request.remote_addr
        )
        
        return jsonify({"message": "Grading deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting grading")
        error_msg = str(e)
        log_audit_event(
            event_type="grading.delete.failed",
            user_id=actor_id,
            details={"error": error_msg, "grading_id": grading_id, "exception_type": type(e).__name__},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400

# Additional endpoints for getting gradings for specific entities
@research_bp.route('/abstracts/<abstract_id>/gradings', methods=['GET'])
@jwt_required()
def get_abstract_gradings(abstract_id):
    """Get all gradings for a specific abstract."""
    actor_id = get_jwt_identity()
    try:
        gradings = Grading.query.filter_by(abstract_id=abstract_id).all()
        
        # Log successful retrieval
        log_audit_event(
            event_type="abstract.gradings.list.success",
            user_id=actor_id,
            details={
                "abstract_id": abstract_id,
                "gradings_count": len(gradings)
            },
            ip_address=request.remote_addr
        )
        
        return jsonify(gradings_schema.dump(gradings)), 200
    except Exception as e:
        current_app.logger.exception("Error getting abstract gradings")
        error_msg = str(e)
        log_audit_event(
            event_type="abstract.gradings.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "abstract_id": abstract_id, "exception_type": type(e).__name__},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400

@research_bp.route('/best-papers/<best_paper_id>/gradings', methods=['GET'])
@jwt_required()
def get_best_paper_gradings(best_paper_id):
    """Get all gradings for a specific best paper."""
    actor_id = get_jwt_identity()
    try:
        gradings = Grading.query.filter_by(best_paper_id=best_paper_id).all()
        
        # Log successful retrieval
        log_audit_event(
            event_type="best_paper.gradings.list.success",
            user_id=actor_id,
            details={
                "best_paper_id": best_paper_id,
                "gradings_count": len(gradings)
            },
            ip_address=request.remote_addr
        )
        
        return jsonify(gradings_schema.dump(gradings)), 200
    except Exception as e:
        current_app.logger.exception("Error getting best paper gradings")
        error_msg = str(e)
        log_audit_event(
            event_type="best_paper.gradings.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "best_paper_id": best_paper_id, "exception_type": type(e).__name__},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400

@research_bp.route('/awards/<award_id>/gradings', methods=['GET'])
@jwt_required()
def get_award_gradings(award_id):
    """Get all gradings for a specific award."""
    actor_id = get_jwt_identity()
    try:
        gradings = Grading.query.filter_by(award_id=award_id).all()
        
        # Log successful retrieval
        log_audit_event(
            event_type="award.gradings.list.success",
            user_id=actor_id,
            details={
                "award_id": award_id,
                "gradings_count": len(gradings)
            },
            ip_address=request.remote_addr
        )
        
        return jsonify(gradings_schema.dump(gradings)), 20
    except Exception as e:
        current_app.logger.exception("Error getting award gradings")
        error_msg = str(e)
        log_audit_event(
            event_type="award.gradings.list.failed",
            user_id=actor_id,
            details={"error": error_msg, "award_id": award_id, "exception_type": type(e).__name__},
            ip_address=request.remote_addr
        )
        return jsonify({"error": error_msg}), 400