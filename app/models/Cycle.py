import uuid

from app.models.enumerations import Status
from ..extensions import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum


class Cycle(db.Model):
    __tablename__ = "cycles"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    awards = db.relationship("Awards", back_populates="cycle", lazy=True)
    abstracts = db.relationship("Abstracts", back_populates="cycle", lazy=True)


class Author(db.Model):
    __tablename__ = "authors"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    affiliation = db.Column(db.String(500), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    is_presenter = db.Column(db.Boolean, default=False)
    is_corresponding = db.Column(db.Boolean, default=False)

    abstracts = db.relationship("Abstracts", secondary="abstract_authors", back_populates="authors")
    awards = db.relationship("Awards", back_populates="author", lazy=True)

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)

    abstracts = db.relationship("Abstracts", back_populates="category", lazy=True)
    awards = db.relationship("Awards", back_populates="category", lazy=True)
    users = db.relationship("User", back_populates="category", lazy=True)

class Abstracts(db.Model):
    __tablename__ = "abstracts"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(500), nullable=False)

    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey('categories.id'), nullable=False)
    category = db.relationship("Category", back_populates="abstracts")

    authors = db.relationship("Author", secondary="abstract_authors", back_populates="abstracts")

    content = db.Column(db.Text, nullable=False)
    pdf_path = db.Column(db.String(500), nullable=True)  # Path to uploaded PDF

    cycle_id = db.Column(UUID(as_uuid=True), db.ForeignKey('cycles.id'), nullable=False)
    cycle = db.relationship("Cycle", back_populates="abstracts")

    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    status = db.Column(SqlEnum(Status), nullable=False, default=Status.PENDING.value)
    created_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)

    # Relationship to verifiers (users who can verify this abstract)
    verifiers = db.relationship("User", secondary="abstract_verifiers", back_populates="abstracts_to_verify")


class AbstractAuthors(db.Model):
    __tablename__ = "abstract_authors"
    abstract_id = db.Column(UUID(as_uuid=True), db.ForeignKey('abstracts.id'), primary_key=True)
    author_id = db.Column(UUID(as_uuid=True), db.ForeignKey('authors.id'), primary_key=True)
    author_order = db.Column(db.Integer, nullable=False)  # To maintain the order of authors


class AbstractVerifiers(db.Model):
    __tablename__ = "abstract_verifiers"
    abstract_id = db.Column(UUID(as_uuid=True), db.ForeignKey('abstracts.id'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())


class PaperCategory(db.Model):
    __tablename__ = "paper_categories"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)

    awards = db.relationship("Awards", back_populates="paper_category", lazy=True)

class Awards(db.Model):
    __tablename__ = "awards"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(200), nullable=False)
    
    author_id = db.Column(UUID(as_uuid=True), db.ForeignKey('authors.id'), nullable=False)
    author = db.relationship("Author", back_populates="awards")

    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey('categories.id'), nullable=False)
    category = db.relationship("Category", back_populates="awards")

    forwarding_letter_path = db.Column(db.String(500), nullable=True)
    full_paper_path = db.Column(db.String(500), nullable=True)
    
    is_aiims_work = db.Column(db.Boolean, default=False)

    paper_category_id = db.Column(UUID(as_uuid=True), db.ForeignKey('paper_categories.id'), nullable=False)
    paper_category = db.relationship("PaperCategory", back_populates="awards")

    cycle_id = db.Column(UUID(as_uuid=True), db.ForeignKey('cycles.id'), nullable=False)
    cycle = db.relationship("Cycle", back_populates="awards")

    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    status = db.Column(SqlEnum(Status), nullable=False, default=Status.PENDING.value)