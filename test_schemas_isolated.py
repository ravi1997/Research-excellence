#!/usr/bin/env python3

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, '.')

# Create a minimal test that doesn't load the full app
def test_schemas():
    try:
        # Test importing each schema file directly
        from app.schemas.user_schema import UserSchema
        print("✅ UserSchema imported successfully!")
        
        from app.schemas.user_settings_schema import UserSettingsSchema
        print("✅ UserSettingsSchema imported successfully!")
        
        from app.schemas.login_schema import LoginSchema
        print("✅ LoginSchema imported successfully!")
        
        from app.schemas.cycle_schema import CycleSchema
        print("✅ CycleSchema imported successfully!")
        
        from app.schemas.author_schema import AuthorSchema
        print("✅ AuthorSchema imported successfully!")
        
        from app.schemas.category_schema import CategorySchema
        print("✅ CategorySchema imported successfully!")
        
        from app.schemas.abstract_schema import AbstractSchema
        print("✅ AbstractSchema imported successfully!")
        
        from app.schemas.paper_category_schema import PaperCategorySchema
        print("✅ PaperCategorySchema imported successfully!")
        
        from app.schemas.awards_schema import AwardsSchema
        print("✅ AwardsSchema imported successfully!")
        
        from app.schemas.audit_log_schema import AuditLogSchema
        print("✅ AuditLogSchema imported successfully!")
        
        from app.schemas.token_schema import TokenSchema
        print("✅ TokenSchema imported successfully!")
        
        from app.schemas.department_schema import DepartmentSchema
        print("✅ DepartmentSchema imported successfully!")
        
        from app.schemas.user_role_schema import UserRoleSchema
        print("✅ UserRoleSchema imported successfully!")
        
        print("\n🎉 All schemas imported successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_schemas()