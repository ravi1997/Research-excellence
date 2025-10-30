from datetime import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Enum as SqlEnum,
    Identity,
    Index,
    UniqueConstraint,
    and_,
    event,
    select,
)
from sqlalchemy.dialects.postgresql import DATERANGE, ExcludeConstraint, UUID
from sqlalchemy.orm import synonym, validates

from ..extensions import db
from app.models.enumerations import CyclePhase, GradingFor, Status


class Cycle(db.Model):
    __tablename__ = "cycles"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    best_papers = db.relationship("BestPaper", back_populates="cycle", lazy=True)
    abstracts = db.relationship("Abstracts", back_populates="cycle", lazy=True)
    awards = db.relationship("Awards", back_populates="cycle", lazy=True)

    windows = db.relationship(
        "CycleWindow",
        back_populates="cycle",
        cascade="all, delete-orphan",
        lazy=True,
    )

    submission_windows = db.relationship(
        "CycleWindow",
        primaryjoin=lambda: and_(
            Cycle.id == CycleWindow.cycle_id,
            CycleWindow.phase == CyclePhase.SUBMISSION,
        ),
        viewonly=True,
        lazy=True,
    )

    verification_windows = db.relationship(
        "CycleWindow",
        primaryjoin=lambda: and_(
            Cycle.id == CycleWindow.cycle_id,
            CycleWindow.phase == CyclePhase.VERIFICATION,
        ),
        viewonly=True,
        lazy=True,
    )

    final_windows = db.relationship(
        "CycleWindow",
        primaryjoin=lambda: and_(
            Cycle.id == CycleWindow.cycle_id,
            CycleWindow.phase == CyclePhase.FINAL,
        ),
        viewonly=True,
        lazy=True,
    )


class CycleWindow(db.Model):
    __tablename__ = "cycle_windows"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    cycle_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cycles.id", ondelete="CASCADE"),
        nullable=False,
    )
    cycle = db.relationship("Cycle", back_populates="windows")

    phase = db.Column(SqlEnum(CyclePhase, name="cycle_phase"), nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    win = db.Column(
        DATERANGE,
        Computed("daterange(start_date, end_date, '[]')", persisted=True),
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

class Author(db.Model):
    __tablename__ = "authors"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    affiliation = db.Column(db.String(500), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    is_presenter = db.Column(db.Boolean, default=False)
    is_corresponding = db.Column(db.Boolean, default=False)

    abstracts = db.relationship(
        "Abstracts",
        secondary="abstract_authors",
        back_populates="authors",
    )
    awards = db.relationship("Awards", back_populates="author", lazy=True)
    best_papers = db.relationship("BestPaper", back_populates="author", lazy=True)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)

    abstracts = db.relationship("Abstracts", back_populates="category", lazy=True)
    users = db.relationship("User", back_populates="category", lazy=True)


class Abstracts(db.Model):
    __tablename__ = "abstracts"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(500), nullable=False)

    category_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("categories.id"),
        nullable=False,
    )
    category = db.relationship("Category", back_populates="abstracts")

    authors = db.relationship(
        "Author",
        secondary="abstract_authors",
        back_populates="abstracts",
    )

    content = db.Column(db.Text, nullable=False)
    pdf_path = db.Column(db.String(500), nullable=True)

    cycle_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cycles.id"),
        nullable=False,
    )
    cycle = db.relationship("Cycle", back_populates="abstracts")

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    status = db.Column(
        SqlEnum(Status),
        nullable=False,
        default=Status.PENDING.value,
    )

    created_by_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        nullable=False,
    )
    created_by = db.relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="abstracts_submitted",
    )

    updated_by_id = db.Column(
        "updated_by",
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        nullable=True,
    )
    updated_by = db.relationship(
        "User",
        foreign_keys=[updated_by_id],
        back_populates="abstracts_updated",
    )

    abstract_number = db.Column(
        db.Integer,
        Identity(start=10000),
        nullable=False,
        unique=True,
    )

    consent = db.Column(db.Boolean, default=False, nullable=False)

    verifiers = db.relationship(
        "User",
        secondary="abstract_verifiers",
        back_populates="abstracts_to_verify",
    )

    coordinators = db.relationship(
        "User",
        secondary="abstract_coordinators",
        back_populates="abstracts_to_coordinate",
    )

    grades = db.relationship(
        "Grading",
        back_populates="abstract",
        lazy=True,
        cascade="all, delete-orphan",
    )
    gradings = synonym("grades")

    pdf = synonym("pdf_path")
    submitted_on = synonym("created_at")
    updated_on = synonym("updated_at")
    submitted_by = synonym("created_by")
    submitted_by_id = synonym("created_by_id")


class AbstractAuthors(db.Model):
    __tablename__ = "abstract_authors"

    abstract_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("abstracts.id"),
        primary_key=True,
    )
    author_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("authors.id"),
        primary_key=True,
    )
    author_order = db.Column(db.Integer, nullable=False)


class AbstractVerifiers(db.Model):
    __tablename__ = "abstract_verifiers"

    abstract_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("abstracts.id"),
        primary_key=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        primary_key=True,
    )
    verification_level = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    cycle_window_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cycle_windows.id"),
        nullable=True,
    )
    cycle_window = db.relationship("CycleWindow")
    assigned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )

class AbstractCoordinators(db.Model):
    __tablename__ = "abstract_coordinators"

    abstract_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("abstracts.id"),
        primary_key=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        primary_key=True,
    )
    assigned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )


class PaperCategory(db.Model):
    __tablename__ = "paper_categories"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)

    awards = db.relationship("Awards", back_populates="paper_category", lazy=True)
    best_papers = db.relationship(
        "BestPaper",
        back_populates="paper_category",
        lazy=True,
    )


class Awards(db.Model):
    __tablename__ = "awards"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(500), nullable=False)

    author_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("authors.id"),
        nullable=False,
    )
    author = db.relationship("Author", back_populates="awards")

    cycle_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cycles.id"),
        nullable=False,
    )
    cycle = db.relationship("Cycle", back_populates="awards")

    forwarding_letter_path = db.Column(db.String(500), nullable=True)
    full_paper_path = db.Column(db.String(500), nullable=True)
    is_aiims_work = db.Column(db.Boolean, default=False)

    paper_category_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("paper_categories.id"),
        nullable=False,
    )
    paper_category = db.relationship("PaperCategory", back_populates="awards")

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    status = db.Column(
        SqlEnum(Status),
        nullable=False,
        default=Status.PENDING.value,
    )

    created_by_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        nullable=False,
    )
    created_by = db.relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="awards_submitted",
    )

    updated_by_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        nullable=True,
    )
    updated_by = db.relationship(
        "User",
        foreign_keys=[updated_by_id],
        back_populates="awards_updated",
    )

    verifiers = db.relationship(
        "User",
        secondary="award_verifiers",
        back_populates="awards_to_verify",
    )

    coordinators = db.relationship(
        "User",
        secondary="award_coordinators",
        back_populates="awards_to_coordinate",
    )

    grades = db.relationship(
        "Grading",
        back_populates="award",
        lazy=True,
        cascade="all, delete-orphan",
    )
    gradings = synonym("grades")

    award_number = db.Column(
        db.Integer,
        Identity(start=30000),
        nullable=False,
        unique=True,
    )

    complete_pdf_path = synonym("full_paper_path")
    complete_pdf = synonym("full_paper_path")
    covering_letter_pdf_path = synonym("forwarding_letter_path")
    covering_letter_pdf = synonym("forwarding_letter_path")
    work_of_aiims = synonym("is_aiims_work")
    category = synonym("paper_category")
    category_id = synonym("paper_category_id")
    submitted_on = synonym("created_at")
    submitted_by = synonym("created_by")
    submitted_by_id = synonym("created_by_id")
    updated_on = synonym("updated_at")


class AwardVerifiers(db.Model):
    __tablename__ = "award_verifiers"

    award_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("awards.id"),
        primary_key=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        primary_key=True,
    )
    verification_level = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    cycle_window_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cycle_windows.id"),
        nullable=True,
    )
    cycle_window = db.relationship("CycleWindow")
    assigned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )

class AwardCoordinators(db.Model):
    __tablename__ = "award_coordinators"

    award_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("awards.id"),
        primary_key=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        primary_key=True,
    )
    assigned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )


class BestPaper(db.Model):
    __tablename__ = "best_papers"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(500), nullable=False)

    author_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("authors.id"),
        nullable=False,
    )
    author = db.relationship("Author", back_populates="best_papers")

    cycle_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cycles.id"),
        nullable=False,
    )
    cycle = db.relationship("Cycle", back_populates="best_papers")

    forwarding_letter_path = db.Column(db.String(500), nullable=True)
    full_paper_path = db.Column(db.String(500), nullable=True)
    is_aiims_work = db.Column(db.Boolean, default=False)

    paper_category_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("paper_categories.id"),
        nullable=False,
    )
    paper_category = db.relationship(
        "PaperCategory",
        back_populates="best_papers",
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    status = db.Column(
        SqlEnum(Status),
        nullable=False,
        default=Status.PENDING.value,
    )

    created_by_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        nullable=False,
    )
    created_by = db.relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="best_papers_submitted",
    )

    updated_by_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        nullable=True,
    )
    updated_by = db.relationship(
        "User",
        foreign_keys=[updated_by_id],
        back_populates="best_papers_updated",
    )

    verifiers = db.relationship(
        "User",
        secondary="best_paper_verifiers",
        back_populates="best_papers_to_verify",
    )

    coordinators = db.relationship(
        "User",
        secondary="best_paper_coordinators",
        back_populates="best_papers_to_coordinate",
    )

    grades = db.relationship(
        "Grading",
        back_populates="best_paper",
        lazy=True,
        cascade="all, delete-orphan",
    )
    gradings = synonym("grades")

    bestpaper_number = db.Column(
        db.Integer,
        Identity(start=50000),
        nullable=False,
        unique=True,
    )

    complete_pdf_path = synonym("full_paper_path")
    complete_pdf = synonym("full_paper_path")
    covering_letter_pdf_path = synonym("forwarding_letter_path")
    covering_letter_pdf = synonym("forwarding_letter_path")
    work_of_aiims = synonym("is_aiims_work")
    category = synonym("paper_category")
    category_id = synonym("paper_category_id")
    submitted_on = synonym("created_at")
    submitted_by = synonym("created_by")
    submitted_by_id = synonym("created_by_id")
    updated_on = synonym("updated_at")
    paper_number = synonym("bestpaper_number")


class BestPaperVerifiers(db.Model):
    __tablename__ = "best_paper_verifiers"

    best_paper_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("best_papers.id"),
        primary_key=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        primary_key=True,
    )
    verification_level = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    cycle_window_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cycle_windows.id"),
        nullable=True,
    )
    cycle_window = db.relationship("CycleWindow")
    assigned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )


class BestPaperCoordinators(db.Model):
    __tablename__ = "best_paper_coordinators"

    best_paper_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("best_papers.id"),
        primary_key=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        primary_key=True,
    )
    assigned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )


class GradingType(db.Model):
    __tablename__ = "grading_types"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    criteria = db.Column(db.String(100), nullable=False)
    min_score = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    max_score = db.Column(db.Integer, nullable=False)
    grading_for = db.Column(SqlEnum(GradingFor), nullable=False)
    verification_level = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    grades = db.relationship(
        "Grading",
        back_populates="grading_type",
        lazy=True,
        cascade="all, delete-orphan",
    )

class Grading(db.Model):
    __tablename__ = "gradings"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    score = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=True)

    grading_type_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("grading_types.id"),
        nullable=False,
    )
    grading_type = db.relationship("GradingType", back_populates="grades")

    abstract_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("abstracts.id"),
        nullable=True,
    )
    abstract = db.relationship("Abstracts", back_populates="grades")

    best_paper_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("best_papers.id"),
        nullable=True,
    )
    best_paper = db.relationship("BestPaper", back_populates="grades")

    award_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("awards.id"),
        nullable=True,
    )
    award = db.relationship("Awards", back_populates="grades")

    verification_level = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    cycle_window_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cycle_windows.id"),
        nullable=True,
    )
    cycle_window = db.relationship("CycleWindow")

    graded_by_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id"),
        nullable=False,
    )
    graded_by = db.relationship(
        "User",
        foreign_keys=[graded_by_id],
        back_populates="grades_given",
    )

    graded_on = db.Column(
        "created_at",
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
    )
    updated_on = db.Column(
        "updated_at",
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    created_at = synonym("graded_on")
    updated_at = synonym("updated_on")

    @validates("score")
    def validate_score(self, key, value):
        if value is None:
            raise ValueError("A score must be supplied for the grade.")
        if value < 0:
            raise ValueError("A grade score cannot be negative.")

        max_score = None
        grading_type = getattr(self, "grading_type", None)
        if grading_type is not None:
            max_score = grading_type.max_score
        elif self.grading_type_id is not None:
            grading_type = db.session.get(GradingType, self.grading_type_id)
            if grading_type is not None:
                max_score = grading_type.max_score

        if max_score is not None and value > max_score:
            raise ValueError("A grade score cannot exceed the configured maximum.")

        return value

    @validates("verification_level")
    def validate_level(self, key, value):
        if value is None or value <= 0:
            raise ValueError("A verification level must be a positive integer.")

        grading_type = getattr(self, "grading_type", None)
        if grading_type is None and self.grading_type_id is not None:
            grading_type = db.session.get(GradingType, self.grading_type_id)

        if grading_type is not None and grading_type.verification_level != value:
            raise ValueError(
                "The grade level must match the verification level of the grading criteria.",
            )

        return value


def _ensure_submission_window(connection, submission_model):
    cycle_id = getattr(submission_model, "cycle_id", None)
    if cycle_id is None:
        raise ValueError("A submission must belong to a cycle.")

    submitted_on = getattr(submission_model, "created_at", None)
    if submitted_on is None:
        submitted_on = datetime.utcnow()

    submission_date = submitted_on.date()
    
    # Determine the required phase based on the model type
    if isinstance(submission_model, Abstracts):
        required_phase = CyclePhase.ABSTRACT_SUBMISSION
    elif isinstance(submission_model, Awards):
        required_phase = CyclePhase.AWARD_SUBMISSION
    elif isinstance(submission_model, BestPaper):
        required_phase = CyclePhase.BEST_PAPER_SUBMISSION
    else:
        # Fallback to general submission for other types
        required_phase = CyclePhase.SUBMISSION

    stmt = select(CycleWindow.id).where(
        CycleWindow.cycle_id == cycle_id,
        CycleWindow.phase == required_phase,
        CycleWindow.start_date <= submission_date,
        CycleWindow.end_date >= submission_date,
    )

    if connection.execute(stmt).first() is None:
        # If specific phase window is not found, check if general submission window exists
        general_stmt = select(CycleWindow.id).where(
            CycleWindow.cycle_id == cycle_id,
            CycleWindow.phase == CyclePhase.SUBMISSION,
            CycleWindow.start_date <= submission_date,
            CycleWindow.end_date >= submission_date,
        )
        
        if connection.execute(general_stmt).first() is None:
            raise ValueError(
                f"Submissions are allowed only during the {required_phase} period for the cycle.",
            )
        else:
            # If general window exists but specific doesn't, allow submission
            # This maintains backward compatibility
            pass


@event.listens_for(Abstracts, "before_insert")
def enforce_abstract_submission_window(mapper, connection, target):
    _ensure_submission_window(connection, target)


@event.listens_for(Awards, "before_insert")
def enforce_award_submission_window(mapper, connection, target):
    _ensure_submission_window(connection, target)


@event.listens_for(BestPaper, "before_insert")
def enforce_best_paper_submission_window(mapper, connection, target):
    _ensure_submission_window(connection, target)
