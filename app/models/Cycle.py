from sqlalchemy import Enum as SqlEnum, Identity, Index, Computed
from sqlalchemy import func, and_
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, DATERANGE
from sqlalchemy import Identity
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from ..extensions import db
from app.models.enumerations import CyclePhase, GradingFor, Status
import uuid


class Cycle(db.Model):
    __tablename__ = "cycles"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)

    # Keep these existing columns (backward compatible)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    best_papers = db.relationship(
        "BestPaper", back_populates="cycle", lazy=True)
    abstracts = db.relationship("Abstracts", back_populates="cycle", lazy=True)
    awards = db.relationship("Awards", back_populates="cycle", lazy=True)

    # NEW: windows relationship
    windows = db.relationship(
        "CycleWindow",
        back_populates="cycle",
        cascade="all, delete-orphan",
        lazy=True
    )

    # Convenience filtered relationships
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

    cycle_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        "cycles.id", ondelete="CASCADE"), nullable=False)
    cycle = db.relationship("Cycle", back_populates="windows")

    phase = db.Column(SqlEnum(CyclePhase, name="cycle_phase"), nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # Generated (stored) daterange for robust constraints
    # Inclusive bounds: '[]' (both start & end inclusive)
    win = db.Column(
        DATERANGE,
        Computed("daterange(start_date, end_date, '[]')", persisted=True),
        nullable=False
    )

    created_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp(
    ), onupdate=db.func.current_timestamp())


class Author(db.Model):
    __tablename__ = "authors"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    affiliation = db.Column(db.String(500), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    is_presenter = db.Column(db.Boolean, default=False)
    is_corresponding = db.Column(db.Boolean, default=False)

    abstracts = db.relationship(
        "Abstracts", secondary="abstract_authors", back_populates="authors")
    awards = db.relationship("Awards", back_populates="author", lazy=True)
    best_papers = db.relationship(
        "BestPaper", back_populates="author", lazy=True)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)

    abstracts = db.relationship(
        "Abstracts", back_populates="category", lazy=True)
    users = db.relationship("User", back_populates="category", lazy=True)


class Abstracts(db.Model):
    __tablename__ = "abstracts"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(500), nullable=False)

    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'categories.id'), nullable=False)
    category = db.relationship("Category", back_populates="abstracts")

    authors = db.relationship(
        "Author", secondary="abstract_authors", back_populates="abstracts")

    content = db.Column(db.Text, nullable=False)
    pdf_path = db.Column(db.String(500), nullable=True)  # Path to uploaded PDF

    cycle_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'cycles.id'), nullable=False)
    cycle = db.relationship("Cycle", back_populates="abstracts")

    created_at = db.Column(db.DateTime, nullable=False,
                           default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(
    ), onupdate=db.func.current_timestamp())

    status = db.Column(SqlEnum(Status), nullable=False,
                       default=Status.PENDING.value)
    created_by_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)

    abstract_number = db.Column(
        db.Integer,
        # GENERATED BY DEFAULT AS IDENTITY (START WITH 10000)
        Identity(start=10000),
        nullable=False,
        unique=True
    )

    consent = db.Column(db.Boolean, default=False, nullable=False)

    # Relationship to verifiers (users who can verify this abstract)
    verifiers = db.relationship(
        "User", secondary="abstract_verifiers", back_populates="abstracts_to_verify")
    gradings = db.relationship("Grading", back_populates="abstract", lazy=True)


class AbstractAuthors(db.Model):
    __tablename__ = "abstract_authors"
    abstract_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'abstracts.id'), primary_key=True)
    author_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'authors.id'), primary_key=True)
    # To maintain the order of authors
    author_order = db.Column(db.Integer, nullable=False)


class AbstractVerifiers(db.Model):
    __tablename__ = "abstract_verifiers"
    abstract_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'abstracts.id'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, nullable=False,
                            default=db.func.current_timestamp())


class PaperCategory(db.Model):
    __tablename__ = "paper_categories"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)

    awards = db.relationship(
        "Awards", back_populates="paper_category", lazy=True)
    best_papers = db.relationship(
        "BestPaper", back_populates="paper_category", lazy=True)


class Awards(db.Model):
    __tablename__ = "awards"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(500), nullable=False)

    author_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'authors.id'), nullable=False)
    author = db.relationship("Author", back_populates="awards")

    cycle_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'cycles.id'), nullable=False)
    cycle = db.relationship("Cycle", back_populates="awards")

    forwarding_letter_path = db.Column(db.String(500), nullable=True)
    full_paper_path = db.Column(db.String(500), nullable=True)

    is_aiims_work = db.Column(db.Boolean, default=False)

    paper_category_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'paper_categories.id'), nullable=False)
    paper_category = db.relationship("PaperCategory", back_populates="awards")

    created_at = db.Column(db.DateTime, nullable=False,
                           default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(
    ), onupdate=db.func.current_timestamp())
    status = db.Column(SqlEnum(Status), nullable=False,
                       default=Status.PENDING.value)
    # Relationship to verifiers (users who can verify this abstract)
    created_by_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    verifiers = db.relationship(
        "User", secondary="award_verifiers", back_populates="awards_to_verify")
    gradings = db.relationship("Grading", back_populates="award", lazy=True)
    award_number = db.Column(
        db.Integer,
        # GENERATED BY DEFAULT AS IDENTITY (START WITH 30000)
        Identity(start=30000),
        nullable=False,
        unique=True
    )


class AwardVerifiers(db.Model):
    __tablename__ = "award_verifiers"
    award_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'awards.id'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, nullable=False,
                            default=db.func.current_timestamp())


class BestPaper(db.Model):
    __tablename__ = "best_papers"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(500), nullable=False)

    author_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'authors.id'), nullable=False)
    author = db.relationship("Author", back_populates="best_papers")

    cycle_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'cycles.id'), nullable=False)
    cycle = db.relationship("Cycle", back_populates="best_papers")

    forwarding_letter_path = db.Column(db.String(500), nullable=True)
    full_paper_path = db.Column(db.String(500), nullable=True)

    is_aiims_work = db.Column(db.Boolean, default=False)

    paper_category_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'paper_categories.id'), nullable=False)
    paper_category = db.relationship(
        "PaperCategory", back_populates="best_papers")

    created_at = db.Column(db.DateTime, nullable=False,
                           default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(
    ), onupdate=db.func.current_timestamp())
    status = db.Column(SqlEnum(Status), nullable=False,
                       default=Status.PENDING.value)
    created_by_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    # Relationship to verifiers (users who can verify this abstract)
    verifiers = db.relationship(
        "User", secondary="best_paper_verifiers", back_populates="best_papers_to_verify")
    gradings = db.relationship(
        "Grading", back_populates="best_paper", lazy=True)

    bestpaper_number = db.Column(
        db.Integer,
        # GENERATED BY DEFAULT AS IDENTITY (START WITH 50000)
        Identity(start=50000),
        nullable=False,
        unique=True
    )


class BestPaperVerifiers(db.Model):
    __tablename__ = "best_paper_verifiers"
    best_paper_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'best_papers.id'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, nullable=False,
                            default=db.func.current_timestamp())


class GradingType(db.Model):
    __tablename__ = "grading_types"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    criteria = db.Column(db.String(100), nullable=False, unique=True)
    min_score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    grading_for = db.Column(SqlEnum(GradingFor), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False,
                           default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(
    ), onupdate=db.func.current_timestamp())


class Grading(db.Model):
    __tablename__ = "gradings"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    score = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=True)

    grading_type_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'grading_types.id'), nullable=False)
    grading_type = db.relationship("GradingType")

    abstract_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'abstracts.id'), nullable=True)
    abstract = db.relationship("Abstracts")

    best_paper_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'best_papers.id'), nullable=True)
    best_paper = db.relationship("BestPaper")

    award_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'awards.id'), nullable=True)
    award = db.relationship("Awards")

    graded_by_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    graded_by = db.relationship("User", foreign_keys=[graded_by_id])

    created_at = db.Column(db.DateTime, nullable=False,
                           default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(
    ), onupdate=db.func.current_timestamp())
