"""
Test script to verify the complete abstract workflow implementation
"""
import os
import sys
import uuid
from datetime import datetime, timedelta

# Add the project root to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.extensions import db
from app.models.User import User
from app.models.Cycle import Abstracts, Category, Cycle, Grading, GradingType
from app.models.enumerations import Role, Status, GradingFor
from app import create_app
from app.utils.model_utils import abstract_utils, user_utils

def setup_test_data():
    """Set up test data for the workflow"""
    app = create_app()
    
    with app.app_context():
        # Create a test cycle
        cycle = Cycle(
            name="Test Cycle",
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=30)).date()
        )
        db.session.add(cycle)
        db.session.commit()
        
        # Create a test category
        category = Category(name="Test Category")
        db.session.add(category)
        db.session.commit()
        
        # Create test users with different roles
        admin_user = User(
            username="admin_test",
            email="admin@test.com",
            employee_id="ADMIN001",
            user_type="employee"
        )
        admin_user.set_password("Password123!")
        admin_user.roles = [Role.ADMIN]
        db.session.add(admin_user)
        
        coordinator_user = User(
            username="coordinator_test",
            email="coordinator@test.com",
            employee_id="COORD001",
            user_type="employee"
        )
        coordinator_user.set_password("Password123!")
        coordinator_user.roles = [Role.COORDINATOR]
        db.session.add(coordinator_user)
        
        verifier_user = User(
            username="verifier_test",
            email="verifier@test.com",
            employee_id="VERIF001",
            user_type="employee"
        )
        verifier_user.set_password("Password123!")
        verifier_user.roles = [Role.VERIFIER]
        db.session.add(verifier_user)
        
        user = User(
            username="user_test",
            email="user@test.com",
            employee_id="USER001",
            user_type="employee"
        )
        user.set_password("Password123!")
        user.roles = [Role.USER]
        db.session.add(user)
        
        db.session.commit()
        
        # Create grading types for abstracts
        grading_type1 = GradingType(
            criteria="Originality",
            min_score=0,
            max_score=10,
            grading_for=GradingFor.ABSTRACT
        )
        grading_type2 = GradingType(
            criteria="Clarity",
            min_score=0,
            max_score=10,
            grading_for=GradingFor.ABSTRACT
        )
        grading_type3 = GradingType(
            criteria="Impact",
            min_score=0,
            max_score=10,
            grading_for=GradingFor.ABSTRACT
        )
        
        db.session.add_all([grading_type1, grading_type2, grading_type3])
        db.session.commit()
        
        print("Test data created successfully")
        print(f"Created cycle: {cycle.name}")
        print(f"Created category: {category.name}")
        print(f"Created users: {admin_user.username}, {coordinator_user.username}, {verifier_user.username}, {user.username}")
        print(f"Created grading types: {grading_type1.criteria}, {grading_type2.criteria}, {grading_type3.criteria}")
        
        return {
            'cycle': cycle,
            'category': category,
            'admin_user': admin_user,
            'coordinator_user': coordinator_user,
            'verifier_user': verifier_user,
            'user': user,
            'grading_types': [grading_type1, grading_type2, grading_type3]
        }

def test_workflow():
    """Test the complete workflow"""
    app = create_app()
    
    with app.app_context():
        # Get test data
        test_data = setup_test_data()
        
        print("\n--- Testing Abstract Workflow ---")
        
        # Step 1: User creates an abstract
        print("\n1. Creating abstract...")
        abstract = abstract_utils.create_abstract(
            title="Test Abstract",
            content="This is a test abstract content.",
            category_id=test_data['category'].id,
            cycle_id=test_data['cycle'].id,
            created_by_id=test_data['user'].id,
            status=Status.PENDING
        )
        print(f"   Abstract created with ID: {abstract.id}, Status: {abstract.status.name}")
        
        # Step 2: User submits abstract for review
        print("\n2. Submitting abstract for review...")
        abstract = abstract_utils.submit_abstract_for_review(abstract, actor_id=test_data['user'].id)
        print(f"   Abstract submitted, Status: {abstract.status.name}")
        
        # Step 3: Coordinator assigns verifier to abstract
        print("\n3. Assigning verifier to abstract...")
        abstract = abstract_utils.assign_verifier(
            abstract,
            test_data['verifier_user'],
            actor_id=test_data['coordinator_user'].id
        )
        print(f"   Verifier assigned: {test_data['verifier_user'].username}")
        
        # Step 4: Verifier grades the abstract
        print("\n4. Verifier grading abstract...")
        grading1 = Grading(
            score=8,
            comments="Good originality",
            grading_type_id=test_data['grading_types'][0].id,
            abstract_id=abstract.id,
            review_phase=abstract.review_phase,
            graded_by_id=test_data['verifier_user'].id
        )
        grading2 = Grading(
            score=7,
            comments="Clear presentation",
            grading_type_id=test_data['grading_types'][1].id,
            abstract_id=abstract.id,
            review_phase=abstract.review_phase,
            graded_by_id=test_data['verifier_user'].id
        )
        grading3 = Grading(
            score=9,
            comments="High impact research",
            grading_type_id=test_data['grading_types'][2].id,
            abstract_id=abstract.id,
            review_phase=abstract.review_phase,
            graded_by_id=test_data['verifier_user'].id
        )
        
        db.session.add_all([grading1, grading2, grading3])
        db.session.commit()
        print(f"   Grading completed with scores: {grading1.score}, {grading2.score}, {grading3.score}")
        
        # Step 5: Coordinator accepts the abstract
        print("\n5. Coordinator accepting abstract...")
        abstract = abstract_utils.accept_abstract(abstract, actor_id=test_data['coordinator_user'].id)
        print(f"   Abstract accepted, Status: {abstract.status.name}")
        
        # Step 6: Test second phase (if needed)
        print("\n6. Testing second phase workflow...")
        # Create a new abstract for second phase test
        abstract2 = abstract_utils.create_abstract(
            title="Test Abstract 2",
            content="This is a test abstract content for phase 2.",
            category_id=test_data['category'].id,
            cycle_id=test_data['cycle'].id,
            created_by_id=test_data['user'].id,
            status=Status.PENDING
        )
        print(f"   Second abstract created with ID: {abstract2.id}, Status: {abstract2.status.name}")
        
        # Submit for review
        abstract2 = abstract_utils.submit_abstract_for_review(abstract2, actor_id=test_data['user'].id)
        print(f"   Second abstract submitted, Status: {abstract2.status.name}")
        
        # Assign to same verifier for first phase
        abstract2 = abstract_utils.assign_verifier(
            abstract2,
            test_data['verifier_user'],
            actor_id=test_data['coordinator_user'].id,
            review_phase=1
        )
        print(f"   Verifier assigned to phase 1")
        
        # Grade in phase 1
        grading4 = Grading(
            score=5, # Lower score
            comments="Needs improvement",
            grading_type_id=test_data['grading_types'][0].id,
            abstract_id=abstract2.id,
            review_phase=1,
            graded_by_id=test_data['verifier_user'].id
        )
        grading5 = Grading(
            score=4,  # Lower score
            comments="Unclear presentation",
            grading_type_id=test_data['grading_types'][1].id,
            abstract_id=abstract2.id,
            review_phase=1,
            graded_by_id=test_data['verifier_user'].id
        )
        grading6 = Grading(
            score=6,
            comments="Moderate impact",
            grading_type_id=test_data['grading_types'][2].id,
            abstract_id=abstract2.id,
            review_phase=1,
            graded_by_id=test_data['verifier_user'].id
        )
        
        db.session.add_all([grading4, grading5, grading6])
        db.session.commit()
        print(f"   Phase 1 grading completed")
        
        # Coordinator decides to advance to next phase
        abstract2 = abstract_utils.advance_to_next_phase(abstract2, actor_id=test_data['coordinator_user'].id)
        print(f"   Abstract advanced to phase {abstract2.review_phase}, Status: {abstract2.status.name}")
        
        # Assign different verifier for phase 2
        admin_user = test_data['admin_user']
        abstract2 = abstract_utils.assign_verifier(
            abstract2,
            admin_user,
            actor_id=test_data['coordinator_user'].id,
            review_phase=2
        )
        print(f"   New verifier assigned for phase 2: {admin_user.username}")
        
        # Grade in phase 2
        grading7 = Grading(
            score=9,
            comments="Significant improvements made",
            grading_type_id=test_data['grading_types'][0].id,
            abstract_id=abstract2.id,
            review_phase=2,
            graded_by_id=admin_user.id
        )
        grading8 = Grading(
            score=8,
            comments="Now clear and well presented",
            grading_type_id=test_data['grading_types'][1].id,
            abstract_id=abstract2.id,
            review_phase=2,
            graded_by_id=admin_user.id
        )
        grading9 = Grading(
            score=7,
            comments="Good impact research",
            grading_type_id=test_data['grading_types'][2].id,
            abstract_id=abstract2.id,
            review_phase=2,
            graded_by_id=admin_user.id
        )
        
        db.session.add_all([grading7, grading8, grading9])
        db.session.commit()
        print(f"   Phase 2 grading completed")
        
        # Coordinator accepts the abstract after second phase
        abstract2 = abstract_utils.accept_abstract(abstract2, actor_id=test_data['coordinator_user'].id)
        print(f"   Second abstract accepted after phase 2, Status: {abstract2.status.name}")
        
        print("\n--- Workflow Test Completed Successfully ---")
        
        # Verify all data is as expected
        print(f"\nFinal State:")
        print(f" Abstract 1 - ID: {abstract.id}, Status: {abstract.status.name}, Phase: {abstract.review_phase}")
        print(f"  Abstract 2 - ID: {abstract2.id}, Status: {abstract2.status.name}, Phase: {abstract2.review_phase}")
        
        # Count gradings
        all_gradings = Grading.query.all()
        print(f" Total gradings created: {len(all_gradings)}")
        
        # Verify gradings by phase
        phase1_gradings = Grading.query.filter_by(review_phase=1).all()
        phase2_gradings = Grading.query.filter_by(review_phase=2).all()
        print(f"  Phase 1 gradings: {len(phase1_gradings)}")
        print(f"  Phase 2 gradings: {len(phase2_gradings)}")

if __name__ == "__main__":
    test_workflow()