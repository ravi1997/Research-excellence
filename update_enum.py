#!/usr/bin/env python3
"""
Script to update the cycle_phase enum in the database with new values.
This addresses the issue where the database enum doesn't contain all the values
defined in the Python CyclePhase enum.
"""

import os
import sys
from app import create_app
from app.extensions import db

def update_cycle_phase_enum():
    """Update the cycle_phase enum with new values."""
    app = create_app()
    
    with app.app_context():
        print("Connecting to database...")
        
        # Check current enum values
        print("Checking current enum values...")
        result = db.session.execute(
            "SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'cycle_phase') ORDER BY enumsortorder;"
        )
        current_values = [row[0] for row in result.fetchall()]
        print(f"Current enum values: {current_values}")
        
        # Define the new values that need to be added
        new_values = [
            'ABSTRACT_SUBMISSION',
            'BEST_PAPER_SUBMISSION', 
            'AWARD_SUBMISSION',
            'ABSTRACT_VERIFICATION',
            'BEST_PAPER_VERIFICATION',
            'AWARD_VERIFICATION',
            'ABSTRACT_FINAL',
            'BEST_PAPER_FINAL',
            'AWARD_FINAL'
        ]
        
        # Check which values are missing
        missing_values = [v for v in new_values if v not in current_values]
        
        if not missing_values:
            print("All required enum values are already present in the database.")
            return
        
        print(f"Missing enum values: {missing_values}")
        
        # Add missing enum values
        for value in missing_values:
            try:
                # Use autocommit for enum additions
                db.session.execute(db.text(f"ALTER TYPE cycle_phase ADD VALUE IF NOT EXISTS '{value}'"))
                print(f"Added enum value: {value}")
            except Exception as e:
                print(f"Error adding enum value '{value}': {str(e)}")
                # Continue with other values even if one fails
        
        # Commit the changes
        try:
            db.session.commit()
            print("Successfully updated the cycle_phase enum with new values.")
        except Exception as e:
            print(f"Error committing changes: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    update_cycle_phase_enum()