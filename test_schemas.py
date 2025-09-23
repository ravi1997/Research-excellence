#!/usr/bin/env python3

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, '.')

# Mock the missing modules
import types
import sys

# Create a mock tasks module
mock_tasks = types.ModuleType('app.tasks')
mock_tasks.start_hls_worker = lambda app: None
sys.modules['app.tasks'] = mock_tasks

# Test importing the schemas
try:
    from app.schemas import (
        UserSchema, LoginSchema, CycleSchema, AuthorSchema, CategorySchema, 
        AbstractSchema, PaperCategorySchema, AwardsSchema, AuditLogSchema, 
        TokenSchema, DepartmentSchema, UserRoleSchema
    )
    print("✅ All schemas imported successfully!")
    
    # Test creating instances of the schemas
    schemas = [
        UserSchema(),
        LoginSchema(),
        CycleSchema(),
        AuthorSchema(),
        CategorySchema(),
        AbstractSchema(),
        PaperCategorySchema(),
        AwardsSchema(),
        AuditLogSchema(),
        TokenSchema(),
        DepartmentSchema(),
        UserRoleSchema()
    ]
    
    print("✅ All schema instances created successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()