import pytest
import json
from app.models.User import User, Role
from app.extensions import db

class TestAuth:
    """Test authentication endpoints."""

    def test_register_user(self, client, app):
        """Test user registration."""
        response = client.post('/api/v1/auth/register', 
                               data=json.dumps({
                                   'username': 'testuser',
                                   'email': 'test@example.com',
                                   'password': 'Test123!@#',
                                   'mobile': '9876543210'
                               }),
                               content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['message'] == 'User registered'
        
        # Verify user was created in database
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user is not None
            assert user.username == 'testuser'
            assert user.has_role('viewer')  # Default role

    def test_register_user_missing_fields(self, client):
        """Test registration with missing required fields."""
        response = client.post('/api/v1/auth/register',
                               data=json.dumps({
                                   'username': 'testuser',
                                   'email': 'test@example.com'
                                   # Missing password
                               }),
                               content_type='application/json')
        
        assert response.status_code == 400

    def test_register_duplicate_email(self, client, create_user):
        """Test registration with duplicate email."""
        # Create user first
        create_user(email='test@example.com')
        
        # Try to register with same email
        response = client.post('/api/v1/auth/register',
                               data=json.dumps({
                                   'username': 'anotheruser',
                                   'email': 'test@example.com',
                                   'password': 'Test123!@#',
                                   'mobile': '9876543211'
                               }),
                               content_type='application/json')
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['message'] == 'Email already exists'

    def test_login_success(self, client, create_user):
        """Test successful login."""
        # Create user
        create_user(email='test@example.com', password='test123')
        
        # Login
        response = client.post('/api/v1/auth/login',
                               data=json.dumps({
                                   'identifier': 'test@example.com',
                                   'password': 'test123'
                               }),
                               content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'refresh_token' in data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post('/api/v1/auth/login',
                               data=json.dumps({
                                   'identifier': 'nonexistent@example.com',
                                   'password': 'wrongpassword'
                               }),
                               content_type='application/json')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['msg'] == 'Invalid credentials'

    def test_logout(self, client, create_user):
        """Test logout functionality."""
        # Create user and get tokens
        user = create_user(email='test@example.com', password='test123')
        
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'test@example.com',
                                         'password': 'test123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Logout
        response = client.post('/api/v1/auth/logout',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['msg'] == 'Successfully logged out'

    def test_forgot_password(self, client, create_user):
        """Test forgot password functionality."""
        # Create user
        create_user(email='test@example.com', mobile='9876543210')
        
        # Request password reset
        response = client.post('/api/v1/auth/forgot-password',
                               data=json.dumps({
                                   'email': 'test@example.com'
                               }),
                               content_type='application/json')
        
        # Should return success even if user doesn't exist (to prevent user enumeration)
        assert response.status_code == 200

    def test_reset_password(self, client, create_user):
        """Test password reset functionality."""
        # Create user
        user = create_user(email='test@example.com', password='oldpassword')
        
        # Generate reset token
        with client.application.app_context():
            token = user.generate_reset_token()
            db.session.commit()
        
        # Reset password
        response = client.post('/api/v1/auth/reset-password',
                               data=json.dumps({
                                   'email': 'test@example.com',
                                   'token': token,
                                   'password': 'newpassword123'
                               }),
                               content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['ok'] is True
        
        # Verify password was changed
        with client.application.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user.check_password('newpassword123') is True
            assert user.check_password('oldpassword') is False