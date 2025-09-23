import pytest
import os
import sys
from app import create_app
from app.extensions import db
from app.models.User import User, Role

@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    # Use testing configuration
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'
    
    app = create_app('testing')
    
    with app.app_context():
        # Create all tables
        db.create_all()
        yield app
        # Drop all tables
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def auth_headers():
    """Return headers for authenticated requests."""
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
    }

@pytest.fixture(scope='function')
def create_user(app):
    """Create a test user."""
    def _create_user(username='testuser', email='test@example.com', password='test123', role=Role.USER):
        with app.app_context():
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user
    return _create_user

@pytest.fixture(scope='function')
def create_admin_user(app):
    """Create a test admin user."""
    def _create_admin_user(username='admin', email='admin@example.com', password='admin123'):
        with app.app_context():
            user = User(username=username, email=email, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user
    return _create_admin_user