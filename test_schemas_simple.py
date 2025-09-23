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

# Mock the missing Role.VIEWER
from app.models.enumerations import Role
if not hasattr(Role, 'VIEWER'):
    Role.VIEWER = 'viewer'

# Set up a minimal Flask app for marshmallow
from flask import Flask
# Import extensions directly to avoid app initialization issues
from flask_marshmallow import Marshmallow

app = Flask(__name__)
ma = Marshmallow(app)

# Test importing the schemas
try:
    # Import models first to set up relationships
    from app.models.User import User, Department, UserRole
    from app.models.Cycle import Cycle, Author, Category, Abstracts, PaperCategory, Awards, AbstractAuthors
    from app.models.AuditLog import AuditLog
    from app.models.Token import Token
    
    # Import schemas
    from app.schemas.user_schema import UserSchema
    from app.schemas.login_schema import LoginSchema
    from app.schemas.cycle_schema import CycleSchema
    from app.schemas.author_schema import AuthorSchema
    from app.schemas.category_schema import CategorySchema
    from app.schemas.abstract_schema import AbstractSchema
    from app.schemas.paper_category_schema import PaperCategorySchema
    from app.schemas.awards_schema import AwardsSchema
    from app.schemas.audit_log_schema import AuditLogSchema
    from app.schemas.token_schema import TokenSchema
    from app.schemas.department_schema import DepartmentSchema
    from app.schemas.user_role_schema import UserRoleSchema
    
    print("✅ All schemas imported successfully!")
    
    # Test creating instances of the schemas within app context
    with app.app_context():
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