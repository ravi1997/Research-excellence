# Academic Submission System - Model Enhancement Plan

## Overview
This document outlines the plan to enhance the existing models in the `app/models` folder to implement a comprehensive academic submission system with multi-period cycle management.

## Current Architecture Analysis

### Existing Models:
- `Cycle` - manages cycles with start/end dates
- `CycleWindow` - handles period-specific windows
- `Author` - author information
- `Category` - submission categories
- `Abstracts` - abstract submissions
- `Awards` - award submissions
- `BestPaper` - best paper submissions
- `Grading` - grading system
- `GradingType` - grading criteria
- `User` - user management
- `enumerations` - status and phase enums

## Requirements Analysis

### 1. Multi-Period Cycle Management
- **Submission Period**: Only abstracts, awards, and best papers can be submitted with full editing capabilities
- **Verification Period**: Multi-tiered validation process with initial screening and assignment to verification levels
- **Final Period**: Comprehensive final screening for selection, acceptance, rejection, and ranking

### 2. Abstract Model Requirements
- Unique title with validation per cycle
- Sequential abstract_number with auto-generation
- Comprehensive authors_list (JSON field)
- Mandatory pdf_attachment with file validation
- Timestamps with timezone awareness
- User references with foreign keys
- Category classification
- Assigned_verifiers relationship
- Grades collection
- Status field with defined transitions
- Content_body with rich text support
- Mandatory consent_documentation
- Abstract_type field
- Word_count validation
- Keywords field

### 3. Award Model Requirements
- Unique title with validation per cycle
- Sequential award_number with auto-generation
- Author references with foreign keys
- Mandatory complete_pdf_submission
- Required covering_letter_pdf
- Timestamps with timezone awareness
- User references with foreign keys
- Category classification
- Assigned_verifiers relationship
- Grades collection
- Status field with defined transitions
- AIIMS work documentation
- Award_type classification
- Eligibility_criteria validation
- Supporting_documents field

### 4. Best Paper Model Requirements
- Unique title with validation per cycle
- Sequential paper_number with auto-generation
- Author references with foreign keys
- Mandatory complete_pdf_submission
- Required covering_letter_pdf
- Timestamps with timezone awareness
- User references with foreign keys
- Category classification
- Assigned_verifiers relationship
- Grades collection
- Status field with defined transitions
- AIIMS work documentation
- Paper_type classification
- Research_area specification
- Methodology_details field
- Results_summary field
- References_list field

### 5. Grade Model Requirements
- Type-specific grading criteria
- Weighted scoring systems
- Grade_value validation (0 to maximum_value)
- Comment fields with validation
- Graded_by references with verifier validation
- Timestamps with timezone awareness
- Grade_category for evaluation aspects
- Maximum_possible_score
- Grade_weight for calculations
- Grade_status for completion tracking

### 6. Cycle Management Requirements
- AcademicCycle model with comprehensive period management
- Validation ensuring no temporal overlap between periods
- Extension capabilities
- Period-specific constraints

## Implementation Plan

### Phase 1: Enhanced Cycle Management
1. Enhance `Cycle` model with submission_start_date, submission_end_date, verification_start_date, verification_end_date, final_start_date, final_end_date
2. Add status field and extension_days field
3. Implement period validation methods
4. Add constraints to prevent temporal overlap

### Phase 2: Enhanced Abstract Model
1. Add authors_list as JSON field
2. Add abstract_type field
3. Add word_count field
4. Add keywords field
5. Add content_body field (rich text)
6. Add consent_documentation with signature capabilities
7. Enhance status field with additional states
8. Add submitted_timestamp field
9. Add submitted_by reference
10. Add category validation
11. Add file validation for pdf_attachment

### Phase 3: Enhanced Award Model
1. Add award_type field
2. Add eligibility_criteria field
3. Add supporting_documents field
4. Add covering_letter_pdf field
5. Add complete_pdf_submission field
6. Add aiims_work_documentation field
7. Enhance status field with additional states
8. Add submitted_timestamp field
9. Add submitted_by reference
10. Add file validation for PDF fields

### Phase 4: Enhanced Best Paper Model
1. Add paper_type field
2. Add research_area field
3. Add methodology_details field
4. Add results_summary field
5. Add references_list field
6. Add covering_letter_pdf field
7. Add complete_pdf_submission field
8. Add aiims_work_documentation field
9. Enhance status field with additional states
10. Add submitted_timestamp field
11. Add submitted_by reference
12. Add file validation for PDF fields

### Phase 5: Enhanced Grade Model
1. Add grade_category field
2. Add maximum_possible_score field
3. Add grade_weight field
4. Add grade_status field
5. Add grade_value validation
6. Add comment field validation
7. Add type-specific grading criteria
8. Implement weighted scoring systems

### Phase 6: Enumerations and Status Updates
1. Add new status values to Status enum
2. Add abstract_type, award_type, paper_type enums
3. Add grade_status enum

### Phase 7: Validation and Business Logic
1. Implement period-aware validation methods
2. Add clean methods for business rule validation
3. Add custom validators for complex constraints
4. Add pre-save validation
5. Implement model managers for period-specific queries

### Phase 8: Relationships and Constraints
1. Ensure proper foreign key constraints
2. Add proper indexing for performance
3. Add database constraints (check, unique)
4. Implement audit trails
5. Add cascading operations
6. Add soft delete capabilities

## Implementation Details

### Enhanced Cycle Model
```python
class AcademicCycle(db.Model):
    __tablename__ = "academic_cycles"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_name = db.Column(db.String(100), nullable=False, unique=True)
    submission_start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    submission_end_date = db.Column(db.DateTime(timezone=True), nullable=False)
    verification_start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    verification_end_date = db.Column(db.DateTime(timezone=True), nullable=False)
    final_start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    final_end_date = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(SqlEnum(CycleStatus), nullable=False, default=CycleStatus.ACTIVE)
    extension_days = db.Column(db.Integer, default=0)
    
    # Add check constraints to prevent temporal overlap
    __table_args__ = (
        CheckConstraint('submission_start_date < submission_end_date', name='check_submission_dates'),
        CheckConstraint('verification_start_date < verification_end_date', name='check_verification_dates'),
        CheckConstraint('final_start_date < final_end_date', name='check_final_dates'),
        CheckConstraint('submission_end_date <= verification_start_date', name='check_submission_verification_no_overlap'),
        CheckConstraint('verification_end_date <= final_start_date', name='check_verification_final_no_overlap'),
        # Additional constraints for period validation
    )
```

### Enhanced Abstract Model
```python
class Abstracts(db.Model):
    # Existing fields...
    
    # New fields for enhanced functionality
    abstract_type = db.Column(SqlEnum(AbstractType), nullable=True)
    word_count = db.Column(db.Integer, nullable=True)
    keywords = db.Column(db.JSON, nullable=True) # JSON array of keywords
    content_body = db.Column(db.Text, nullable=True)  # Rich text content
    consent_documentation = db.Column(db.String(500), nullable=True)  # Path to consent document
    submitted_timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    submitted_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id])
    authors_list = db.Column(db.JSON, nullable=True)  # JSON field for authors details
    
    # Enhanced status with more states
    status = db.Column(SqlEnum(Status), nullable=False, default=Status.DRAFT)
    
    # Add indexes for performance
    __table_args__ = (
        Index('idx_abstract_cycle_title', 'cycle_id', 'title', unique=True),  # Unique title per cycle
        Index('idx_abstract_status', 'status'),
        Index('idx_abstract_created_at', 'created_at'),
    )
```

### Enhanced Award Model
```python
class Awards(db.Model):
    # Existing fields...
    
    # New fields for enhanced functionality
    award_type = db.Column(SqlEnum(AwardType), nullable=True)
    eligibility_criteria = db.Column(db.Text, nullable=True)
    supporting_documents = db.Column(db.JSON, nullable=True)  # JSON array of supporting document paths
    covering_letter_pdf = db.Column(db.String(500), nullable=True)
    complete_pdf_submission = db.Column(db.String(500), nullable=True)
    aiims_work_documentation = db.Column(db.String(500), nullable=True)
    submitted_timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    submitted_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id])
    
    # Enhanced status with more states
    status = db.Column(SqlEnum(Status), nullable=False, default=Status.DRAFT)
    
    # Add indexes for performance
    __table_args__ = (
        Index('idx_award_cycle_title', 'cycle_id', 'title', unique=True),  # Unique title per cycle
        Index('idx_award_status', 'status'),
        Index('idx_award_created_at', 'created_at'),
    )
```

### Enhanced Best Paper Model
```python
class BestPaper(db.Model):
    # Existing fields...
    
    # New fields for enhanced functionality
    paper_type = db.Column(SqlEnum(PaperType), nullable=True)
    research_area = db.Column(db.String(200), nullable=True)
    methodology_details = db.Column(db.Text, nullable=True)
    results_summary = db.Column(db.Text, nullable=True)
    references_list = db.Column(db.JSON, nullable=True)  # JSON array of references
    covering_letter_pdf = db.Column(db.String(500), nullable=True)
    complete_pdf_submission = db.Column(db.String(500), nullable=True)
    aiims_work_documentation = db.Column(db.String(500), nullable=True)
    submitted_timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    submitted_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id])
    
    # Enhanced status with more states
    status = db.Column(SqlEnum(Status), nullable=False, default=Status.DRAFT)
    
    # Add indexes for performance
    __table_args__ = (
        Index('idx_bestpaper_cycle_title', 'cycle_id', 'title', unique=True),  # Unique title per cycle
        Index('idx_bestpaper_status', 'status'),
        Index('idx_bestpaper_created_at', 'created_at'),
    )
```

### Enhanced Grade Model
```python
class Grading(db.Model):
    # Existing fields...
    
    # New fields for enhanced functionality
    grade_value = db.Column(db.Numeric(precision=5, scale=2), nullable=False)  # For decimal precision
    grade_category = db.Column(SqlEnum(GradeCategory), nullable=True)
    maximum_possible_score = db.Column(db.Numeric(precision=5, scale=2), nullable=False)
    grade_weight = db.Column(db.Numeric(precision=3, scale=2), nullable=False, default=1.00)  # Weight for weighted calculations
    grade_status = db.Column(SqlEnum(GradeStatus), nullable=False, default=GradeStatus.PENDING)
    graded_on = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Add validation to ensure grade_value is between 0 and maximum_value
    __table_args__ = (
        CheckConstraint('grade_value >= 0', name='check_grade_value_positive'),
        CheckConstraint('grade_value <= maximum_possible_score', name='check_grade_value_not_exceed_max'),
    )
```

## Period Validation Implementation

### Period Validation Methods
```python
def is_currently_in_submission_period(self):
    now = datetime.now(timezone.utc)
    return self.submission_start_date <= now <= self.submission_end_date

def is_currently_in_verification_period(self):
    now = datetime.now(timezone.utc)
    return self.verification_start_date <= now <= self.verification_end_date

def is_currently_in_final_period(self):
    now = datetime.now(timezone.utc)
    return self.final_start_date <= now <= self.final_end_date

def can_submit_now(self):
    return self.is_currently_in_submission_period()

def can_verify_now(self):
    return self.is_currently_in_verification_period()

def can_finalize_now(self):
    return self.is_currently_in_final_period()
```

## Status Transitions

### Status Enum Updates
```python
class Status(str, Enum):
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    UNDER_REVIEW = 'under_review'
    VERIFIED = 'verified'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    WITHDRAWN = 'withdrawn'
    FINAL_ACCEPTED = 'final_accepted'
    FINAL_REJECTED = 'final_rejected'
```

## Model Managers

### Period-Specific Query Managers
```python
class SubmissionPeriodManager:
    @staticmethod
    def get_submittable_cycles():
        now = datetime.now(timezone.utc)
        return Cycle.query.filter(
            Cycle.submission_start_date <= now,
            Cycle.submission_end_date >= now
        ).all()

class VerificationPeriodManager:
    @staticmethod
    def get_verifiable_cycles():
        now = datetime.now(timezone.utc)
        return Cycle.query.filter(
            Cycle.verification_start_date <= now,
            Cycle.verification_end_date >= now
        ).all()

class FinalPeriodManager:
    @staticmethod
    def get_finalizable_cycles():
        now = datetime.now(timezone.utc)
        return Cycle.query.filter(
            Cycle.final_start_date <= now,
            Cycle.final_end_date >= now
        ).all()
```

## Validation Implementation

### Clean Methods for Business Rules
```python
def validate_no_temporal_overlap(self):
    # Ensure periods don't overlap
    if self.submission_end_date > self.verification_start_date:
        raise ValidationError("Submission period cannot overlap with verification period")
    if self.verification_end_date > self.final_start_date:
        raise ValidationError("Verification period cannot overlap with final period")

def validate_grade_value(self):
    # Ensure grade value is within bounds
    if self.grade_value < 0 or self.grade_value > self.maximum_possible_score:
        raise ValidationError(f"Grade value must be between 0 and {self.maximum_possible_score}")
```

## File Validation

### PDF and Document Validation
```python
def validate_pdf_file(file_path, max_size_mb=10):
    if not file_path:
        return False
    if not file_path.lower().endswith('.pdf'):
        return False
    if os.path.getsize(file_path) > max_size_mb * 1024 * 1024:
        return False
    return True
```

## Migration Strategy

1. Create new enhanced models while maintaining backward compatibility
2. Update existing models gradually with new fields
3. Implement data migration scripts if needed
4. Test thoroughly to ensure no data loss
5. Deploy in phases to minimize disruption

This comprehensive plan addresses all the requirements specified in the task while maintaining the existing functionality and ensuring proper data integrity.