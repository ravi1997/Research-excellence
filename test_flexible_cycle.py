"""
Test script to verify the flexible cycle framework implementation
"""
from datetime import date, timedelta
from app.models.Cycle import Cycle, CycleWindow
from app.models.enumerations import CyclePhase
from app.extensions import db
from app import create_app
import unittest


class TestFlexibleCycleFramework(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def test_cycle_creation(self):
        """Test that cycles can be created with the new framework"""
        with self.app.app_context():
            # Create a cycle
            cycle = Cycle(
                name="Test Cycle 2025",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365)
            )
            db.session.add(cycle)
            db.session.commit()
            
            self.assertIsNotNone(cycle.id)
            self.assertEqual(cycle.name, "Test Cycle 2025")
    
    def test_cycle_window_creation(self):
        """Test that specific component windows can be created"""
        with self.app_context():
            # Create a cycle
            cycle = Cycle(
                name="Test Cycle 2025",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365)
            )
            db.session.add(cycle)
            db.session.commit()
            
            # Create an abstract submission window
            abstract_window = CycleWindow(
                cycle_id=cycle.id,
                phase=CyclePhase.ABSTRACT_SUBMISSION,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30)
            )
            db.session.add(abstract_window)
            db.session.commit()
            
            self.assertIsNotNone(abstract_window.id)
            self.assertEqual(abstract_window.phase, CyclePhase.ABSTRACT_SUBMISSION)
    
    def test_multiple_windows_per_cycle(self):
        """Test that a cycle can have multiple different windows"""
        with self.app_context():
            # Create a cycle
            cycle = Cycle(
                name="Test Cycle 2025",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365)
            )
            db.session.add(cycle)
            db.session.commit()
            
            # Create multiple windows for different components
            windows_data = [
                {
                    'phase': CyclePhase.ABSTRACT_SUBMISSION,
                    'start_date': date.today(),
                    'end_date': date.today() + timedelta(days=30)
                },
                {
                    'phase': CyclePhase.BEST_PAPER_SUBMISSION,
                    'start_date': date.today() + timedelta(days=10),
                    'end_date': date.today() + timedelta(days=40)
                },
                {
                    'phase': CyclePhase.AWARD_SUBMISSION,
                    'start_date': date.today() + timedelta(days=20),
                    'end_date': date.today() + timedelta(days=50)
                }
            ]
            
            for window_data in windows_data:
                window = CycleWindow(
                    cycle_id=cycle.id,
                    **window_data
                )
                db.session.add(window)
            
            db.session.commit()
            
            # Verify all windows were created
            cycle_windows = CycleWindow.query.filter_by(cycle_id=cycle.id).all()
            self.assertEqual(len(cycle_windows), 3)
            
            # Verify each phase exists
            phases = [w.phase for w in cycle_windows]
            self.assertIn(CyclePhase.ABSTRACT_SUBMISSION, phases)
            self.assertIn(CyclePhase.BEST_PAPER_SUBMISSION, phases)
            self.assertIn(CyclePhase.AWARD_SUBMISSION, phases)
    
    def test_enum_values_exist(self):
        """Test that all new enum values exist"""
        self.assertEqual(CyclePhase.ABSTRACT_SUBMISSION, "ABSTRACT_SUBMISSION")
        self.assertEqual(CyclePhase.BEST_PAPER_SUBMISSION, "BEST_PAPER_SUBMISSION")
        self.assertEqual(CyclePhase.AWARD_SUBMISSION, "AWARD_SUBMISSION")
        self.assertEqual(CyclePhase.ABSTRACT_VERIFICATION, "ABSTRACT_VERIFICATION")
        self.assertEqual(CyclePhase.BEST_PAPER_VERIFICATION, "BEST_PAPER_VERIFICATION")
        self.assertEqual(CyclePhase.AWARD_VERIFICATION, "AWARD_VERIFICATION")
        self.assertEqual(CyclePhase.ABSTRACT_FINAL, "ABSTRACT_FINAL")
        self.assertEqual(CyclePhase.BEST_PAPER_FINAL, "BEST_PAPER_FINAL")
        self.assertEqual(CyclePhase.AWARD_FINAL, "AWARD_FINAL")


if __name__ == '__main__':
    unittest.main()