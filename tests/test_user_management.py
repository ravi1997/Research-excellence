import pytest
import json
from app.models.User import User, Role
from app.extensions import db

class TestUserManagement:
    """Test user management endpoints."""

    def test_get_current_user(self, client, create_user):
        """Test getting current user information."""
        # Create user and login
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
        
        # Get current user
        response = client.get('/api/v1/auth/me',
                              headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['logged_in_as']['email'] == 'test@example.com'

    def test_change_password(self, client, create_user):
        """Test changing user password."""
        # Create user and login
        user = create_user(email='test@example.com', password='oldpassword')
        
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'test@example.com',
                                         'password': 'oldpassword'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Change password
        response = client.post('/api/v1/user/change-password',
                               data=json.dumps({
                                   'current_password': 'oldpassword',
                                   'new_password': 'newpassword123'
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Password changed'
        
        # Verify password was changed
        with client.application.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user.check_password('newpassword123') is True
            assert user.check_password('oldpassword') is False

    def test_admin_list_users(self, client, create_admin_user, create_user):
        """Test admin listing all users."""
        # Create admin user and regular user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        user = create_user(email='user@example.com', password='user123')
        
        # Login as admin
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'admin@example.com',
                                         'password': 'admin123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # List users
        response = client.get('/api/v1/user/users',
                              headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 2  # At least admin and user

    def test_admin_get_user(self, client, create_admin_user, create_user):
        """Test admin getting specific user."""
        # Create admin user and regular user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        user = create_user(email='user@example.com', password='user123')
        
        # Login as admin
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'admin@example.com',
                                         'password': 'admin123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Get specific user
        response = client.get(f'/api/v1/user/users/{user.id}',
                              headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['email'] == 'user@example.com'

    def test_admin_create_user(self, client, create_admin_user):
        """Test admin creating new user."""
        # Create admin user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        
        # Login as admin
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'admin@example.com',
                                         'password': 'admin123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Create new user
        response = client.post('/api/v1/user/users',
                               data=json.dumps({
                                   'username': 'newuser',
                                   'email': 'newuser@example.com',
                                   'password': 'newuser123'
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['email'] == 'newuser@example.com'
        
        # Verify user was created in database
        with client.application.app_context():
            user = User.query.filter_by(email='newuser@example.com').first()
            assert user is not None

    def test_admin_update_user(self, client, create_admin_user, create_user):
        """Test admin updating user."""
        # Create admin user and regular user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        user = create_user(email='user@example.com', password='user123')
        
        # Login as admin
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'admin@example.com',
                                         'password': 'admin123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Update user
        response = client.put(f'/api/v1/user/users/{user.id}',
                              data=json.dumps({
                                  'username': 'updateduser',
                                  'email': 'updated@example.com'
                              }),
                              content_type='application/json',
                              headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['username'] == 'updateduser'
        assert data['email'] == 'updated@example.com'
        
        # Verify user was updated in database
        with client.application.app_context():
            updated_user = User.query.filter_by(id=user.id).first()
            assert updated_user.username == 'updateduser'
            assert updated_user.email == 'updated@example.com'

    def test_admin_delete_user(self, client, create_admin_user, create_user):
        """Test admin deleting user."""
        # Create admin user and regular user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        user = create_user(email='user@example.com', password='user123')
        
        # Login as admin
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'admin@example.com',
                                         'password': 'admin123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Delete user
        response = client.delete(f'/api/v1/user/users/{user.id}',
                                 headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'User deleted'
        
        # Verify user was deleted from database
        with client.application.app_context():
            deleted_user = User.query.filter_by(id=user.id).first()
            assert deleted_user is None