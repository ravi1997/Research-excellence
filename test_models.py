#!/usr/bin/env python3
"""
Test script to validate the enhanced academic submission system models
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import db
from app.models.Cycle import AcademicCycle, Abstracts, Awards, BestPaper, Grading, GradingType
from app.models.enumerations import Status, CyclePhase, GradingFor, AbstractType, AwardType, PaperType, GradeCategory, GradeStatus, CycleStatus


class TestAcademicSubmissionModels(unittest.TestCase):
    """Test class for academic submission system models"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # This would normally connect to a test database
        pass

    def test_academic_cycle_model(self):
        """Test AcademicCycle model with multi-period support"""
        from datetime import datetime, timedelta, timezone
        
        now = datetime.now(timezone.utc)
        submission_start = now
        submission_end = now + timedelta(days=7)
        verification_start = submission_end + timedelta(days=1)
        verification_end = verification_start + timedelta(days=7)
        final_start = verification_end + timedelta(days=1)
        final_end = final_start + timedelta(days=7)
        
        cycle = AcademicCycle(
            cycle_name="Test Cycle 2025",
            submission_start_date=submission_start,
            submission_end_date=submission_end,
            verification_start_date=verification_start,
            verification_end_date=verification_end,
            final_start_date=final_start,
            final_end_date=final_end,
            status=CycleStatus.ACTIVE
        )
        
        # Test period methods
        self.assertTrue(cycle.is_currently_in_submission_period())
        self.assertFalse(cycle.is_currently_in_verification_period())
        self.assertFalse(cycle.is_currently_in_final_period())
        
        self.assertTrue(cycle.can_submit_now())
        self.assertFalse(cycle.can_verify_now())
        self.assertFalse(cycle.can_finalize_now())
        
        # Test phase identification
        self.assertEqual(cycle.get_current_phase(), CyclePhase.SUBMISSION)
        self.assertTrue(cycle.is_period_active(CyclePhase.SUBMISSION))
        
        print("✓ AcademicCycle model tests passed")

    def test_abstract_model_enhancements(self):
        """Test Abstract model with all required enhancements"""
        from datetime import datetime, timezone
        
        # Create a test abstract
        abstract = Abstracts(
            title="Test Abstract Title",
            category_id="123e4567-e89b-12d3-a456-426614174000",
            cycle_id="123e4567-e89b-12d3-a456-42614174001",
            created_by_id="123e4567-e89b-12d3-a456-426614174002",
            submitted_by_id="123e4567-e89b-12d3-a456-426614174002",
            abstract_type=AbstractType.RESEARCH,
            word_count=1500,
            keywords=["keyword1", "keyword2", "keyword3"],
            consent=True,
            content_body="This is the content body of the abstract",
            pdf_attachment="/path/to/abstract.pdf",
            authors_list=[
                {
                    "name": "John Doe",
                    "affiliation": "Test Institution",
                    "email": "john.doe@example.com",
                    "is_presenter": True
                }
            ],
            status=Status.DRAFT
        )
        
        # Test required fields
        self.assertEqual(abstract.title, "Test Abstract Title")
        self.assertEqual(abstract.abstract_type, AbstractType.RESEARCH)
        self.assertEqual(abstract.status, Status.DRAFT)
        self.assertEqual(abstract.word_count, 1500)
        self.assertEqual(len(abstract.keywords), 3)
        self.assertTrue(abstract.consent)
        
        print("✓ Abstract model tests passed")

    def test_award_model_enhancements(self):
        """Test Award model with all required enhancements"""
        from datetime import datetime, timezone
        
        # Create a test award
        award = Awards(
            title="Test Award Title",
            author_id="123e4567-e89b-12d3-a456-426614174003",
            cycle_id="123e4567-e89b-12d3-a456-426614174001",
            created_by_id="123e4567-e89b-12d3-a456-426614174002",
            submitted_by_id="123e4567-e89b-12d3-a456-426614174002",
            award_type=AwardType.BEST_PAPER_AWARD,
            eligibility_criteria="Must be original research",
            supporting_documents=["/path/to/doc1.pdf", "/path/to/doc2.pdf"],
            covering_letter_pdf="/path/to/covering_letter.pdf",
            complete_pdf_submission="/path/to/complete_paper.pdf",
            is_aiims_work=True,
            aiims_work_documentation="/path/to/aiims_doc.pdf",
            status=Status.DRAFT
        )
        
        # Test required fields
        self.assertEqual(award.title, "Test Award Title")
        self.assertEqual(award.award_type, AwardType.BEST_PAPER_AWARD)
        self.assertEqual(award.status, Status.DRAFT)
        self.assertEqual(len(award.supporting_documents), 2)
        self.assertTrue(award.is_aiims_work)
        
        print("✓ Award model tests passed")

    def test_best_paper_model_enhancements(self):
        """Test BestPaper model with all required enhancements"""
        from datetime import datetime, timezone
        
        # Create a test best paper
        paper = BestPaper(
            title="Test Best Paper Title",
            author_id="123e4567-e89b-12d3-a456-426614174004",
            cycle_id="123e4567-e89b-12d3-a456-426614174001",
            created_by_id="123e4567-e89b-12d3-a456-426614174002",
            submitted_by_id="123e4567-e89b-12d3-a456-426614174002",
            paper_type=PaperType.ORIGINAL_RESEARCH,
            research_area="Computer Science",
            methodology_details="Experimental methodology",
            results_summary="Significant results achieved",
            references_list=["Ref 1", "Ref 2", "Ref 3"],
            covering_letter_pdf="/path/to/covering_letter.pdf",
            complete_pdf_submission="/path/to/complete_paper.pdf",
            is_aiims_work=True,
            aiims_work_documentation="/path/to/aiims_doc.pdf",
            status=Status.DRAFT
        )
        
        # Test required fields
        self.assertEqual(paper.title, "Test Best Paper Title")
        self.assertEqual(paper.paper_type, PaperType.ORIGINAL_RESEARCH)
        self.assertEqual(paper.status, Status.DRAFT)
        self.assertEqual(paper.research_area, "Computer Science")
        self.assertEqual(len(paper.references_list), 3)
        self.assertTrue(paper.is_aiims_work)
        
        print("✓ BestPaper model tests passed")

    def test_grading_model_enhancements(self):
        """Test Grading model with type-specific criteria"""
        from decimal import Decimal
        
        # Create a grading type
        grading_type = GradingType(
            criteria="Originality",
            min_score=Decimal('0.00'),
            max_score=Decimal('100.00'),
            grading_for=GradingFor.ABSTRACT,
            grade_weight=Decimal('1.00'),
            grade_category=GradeCategory.ORIGINALITY
        )
        
        # Create a grading
        grading = Grading(
            grade_value=Decimal('85.50'),
            comments="Excellent originality",
            grade_status=GradeStatus.COMPLETED,
            grading_type_id="123e4567-e89b-12d3-a456-426614174005",
            abstract_id="123e4567-e89b-12d3-a456-426614174006",
            graded_by_id="123e4567-e89b-12d3-a456-426614174007",
            grade_category=GradeCategory.ORIGINALITY,
            maximum_possible_score=Decimal('100.00'),
            grade_weight=Decimal('1.00')
        )
        
        # Test required fields
        self.assertEqual(grading.grade_value, Decimal('85.50'))
        self.assertEqual(grading.grade_status, GradeStatus.COMPLETED)
        self.assertEqual(grading.grade_category, GradeCategory.ORIGINALITY)
        self.assertEqual(grading.maximum_possible_score, Decimal('100.00'))
        self.assertEqual(grading.comments, "Excellent originality")
        
        print("✓ Grading model tests passed")

    def test_validation_methods(self):
        """Test validation methods in models"""
        from datetime import datetime, timezone
        
        # Test abstract validation
        abstract = Abstracts(
            title="Test Abstract",
            category_id="123e4567-e89b-12d3-a456-426614174000",
            cycle_id="123e4567-e89b-12d3-a456-426614174001",
            created_by_id="123e4567-e89b-12d3-a456-426614174002",
            submitted_by_id="123e4567-e89b-12d3-a456-426614174002",
            content_body="This is a test content with multiple words",
            word_count=8,
            consent=True,
            status=Status.SUBMITTED
        )
        
        # Test clean method
        try:
            abstract.clean()  # Should not raise an exception
            print("✓ Abstract validation passed")
        except ValueError as e:
            self.fail(f"Abstract validation failed: {e}")
        
        # Test grading validation
        grading = Grading(
            grade_value=Decimal('150.00'),  # This should be invalid
            grading_type_id="123e4567-e89b-12d3-a456-426614174005",
            abstract_id="123e4567-e89b-12d3-a456-426614174006",
            graded_by_id="123e4567-e89b-12d3-a456-426614174007",
            maximum_possible_score=Decimal('100.00')
        )
        
        # This should raise a validation error
        try:
            grading.clean()
            self.fail("Grading validation should have failed but didn't")
        except ValueError:
            print("✓ Grading validation correctly caught invalid grade value")
        
        print("✓ Validation methods tests passed")

    def test_model_managers(self):
        """Test the model managers"""
        # Just verify the classes exist
        from app.models.Cycle import SubmissionPeriodManager, VerificationPeriodManager, FinalPeriodManager
        
        self.assertTrue(hasattr(SubmissionPeriodManager, 'get_submittable_cycles'))
        self.assertTrue(hasattr(VerificationPeriodManager, 'get_verifiable_cycles'))
        self.assertTrue(hasattr(FinalPeriodManager, 'get_finalizable_cycles'))
        
        print("✓ Model managers tests passed")


def run_tests():
    """Run all tests"""
    print("Running tests for enhanced academic submission system models...\n")
    
    # Create a test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAcademicSubmissionModels)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print(f"{'='*50}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)