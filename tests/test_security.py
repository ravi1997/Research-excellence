import pytest
import json
from app.models.User import User, Role
from app.extensions import db

class TestSecurity:
    """Test security features."""

    def test_password_strength(self, client, create_user):
        """Test password strength requirements."""
        # Try to register with weak password
        response = client.post('/api/v1/auth/register',
                               data=json.dumps({
                                   'username': 'testuser',
                                   'email': 'test@example.com',
                                   'password': 'weak',  # Weak password
                                   'mobile': '9876543210'
                               }),
                               content_type='application/json')
        
        # Should fail due to weak password
        assert response.status_code == 400

    def test_account_lockout(self, client, create_user):
        """Test account lockout after failed login attempts."""
        # Create user
        create_user(email='test@example.com', password='correctpassword')
        
        # Try to login with wrong password multiple times
        for i in range(6):  # MAX_FAILED_ATTEMPTS is 5
            response = client.post('/api/v1/auth/login',
                                   data=json.dumps({
                                       'identifier': 'test@example.com',
                                       'password': 'wrongpassword'
                                   }),
                                   content_type='application/json')
        
        # After 5 failed attempts, account should be locked
        assert response.status_code == 401
        
        # Try to login with correct password (should still fail due to lockout)
        response = client.post('/api/v1/auth/login',
                               data=json.dumps({
                                   'identifier': 'test@example.com',
                                   'password': 'correctpassword'
                               }),
                               content_type='application/json')
        
        # Should still fail due to lockout
        assert response.status_code == 401

    def test_otp_resend_limit(self, client, create_user):
        """Test OTP resend limit."""
        # Create user
        user = create_user(email='test@example.com', password='test123')
        
        # Try to resend OTP multiple times
        for i in range(6):  # MAX_OTP_RESENDS is 5
            response = client.post('/api/v1/auth/resend-otp',
                                   data=json.dumps({
                                       'mobile': '9876543210'
                                   }),
                                   content_type='application/json')
        
        # After 5 attempts, account should be locked
        assert response.status_code in [403, 429]  # Locked or rate limited

    def test_password_expiration(self, client, create_user):
        """Test password expiration."""
        # Create user
        user = create_user(email='test@example.com', password='test123')
        
        # Manually expire password in database
        with client.application.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            from datetime import datetime, timedelta, timezone
            user.password_expiration = datetime.now(timezone.utc) - timedelta(days=1)
            db.session.commit()
        
        # Try to login with expired password
        response = client.post('/api/v1/auth/login',
                               data=json.dumps({
                                   'identifier': 'test@example.com',
                                   'password': 'test123'
                               }),
                               content_type='application/json')
        
        # Should require password change
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['error'] == 'password_change_required'

    def test_role_protection(self, client, create_user):
        """Test role-based access protection."""
        # Create regular user
        user = create_user(email='user@example.com', password='user123')
        
        # Login as regular user
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'user@example.com',
                                         'password': 'user123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Try to access admin-only endpoint
        response = client.get('/api/v1/user/users',
                              headers={'Authorization': f'Bearer {access_token}'})
        
        # Should be forbidden
        assert response.status_code == 403

    def test_jwt_token_revocation(self, client, create_user):
        """Test JWT token revocation on logout."""
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
        
        # Logout
        response = client.post('/api/v1/auth/logout',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        
        # Try to use the same token again
        response = client.get('/api/v1/auth/me',
                              headers={'Authorization': f'Bearer {access_token}'})
        
        # Should be unauthorized
        assert response.status_code == 401