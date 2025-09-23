import pytest
import json
from app.models.User import User, Role
from app.extensions import db

class TestAdminUnverifiedUsers:
    """Test admin unverified users functionality."""

    def test_list_unverified_users(self, client, create_admin_user):
        """Test listing unverified users."""
        # Create admin user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        
        # Create unverified user
        with client.application.app_context():
            unverified_user = User(
                username='unverified',
                email='unverified@example.com',
                mobile='9876543210',
                is_verified=False
            )
            unverified_user.set_password('unverified123')
            db.session.add(unverified_user)
            db.session.commit()
        
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
        
        # List unverified users
        response = client.get('/api/v1/auth/unverified',
                              headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'users' in data
        assert len(data['users']) >= 1

    def test_verify_user(self, client, create_admin_user):
        """Test verifying a user."""
        # Create admin user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        
        # Create unverified user
        with client.application.app_context():
            unverified_user = User(
                username='unverified',
                email='unverified@example.com',
                mobile='9876543210',
                is_verified=False
            )
            unverified_user.set_password('unverified123')
            db.session.add(unverified_user)
            db.session.commit()
            user_id = unverified_user.id
        
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
        
        # Verify user
        response = client.post('/api/v1/auth/verify-user',
                               data=json.dumps({
                                   'user_id': str(user_id)
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['msg'] == 'verified'
        
        # Verify user was marked as verified in database
        with client.application.app_context():
            verified_user = User.query.filter_by(id=user_id).first()
            assert verified_user.is_verified is True

    def test_bulk_verify_users(self, client, create_admin_user):
        """Test bulk verifying users."""
        # Create admin user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        
        # Create unverified users
        user_ids = []
        with client.application.app_context():
            for i in range(3):
                unverified_user = User(
                    username=f'unverified{i}',
                    email=f'unverified{i}@example.com',
                    mobile=f'987654321{i}',
                    is_verified=False
                )
                unverified_user.set_password(f'unverified{i}123')
                db.session.add(unverified_user)
                db.session.commit()
                user_ids.append(str(unverified_user.id))
        
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
        
        # Bulk verify users
        response = client.post('/api/v1/auth/bulk/verify-users',
                               data=json.dumps({
                                   'user_ids': user_ids
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['msg'] == 'ok'
        assert data['verified'] == 3
        
        # Verify users were marked as verified in database
        with client.application.app_context():
            for user_id in user_ids:
                verified_user = User.query.filter_by(id=user_id).first()
                assert verified_user.is_verified is True

    def test_discard_user(self, client, create_admin_user):
        """Test discarding an unverified user."""
        # Create admin user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        
        # Create unverified user
        with client.application.app_context():
            unverified_user = User(
                username='unverified',
                email='unverified@example.com',
                mobile='9876543210',
                is_verified=False
            )
            unverified_user.set_password('unverified123')
            db.session.add(unverified_user)
            db.session.commit()
            user_id = unverified_user.id
        
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
        
        # Discard user
        response = client.post('/api/v1/auth/discard-user',
                               data=json.dumps({
                                   'user_id': str(user_id)
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['msg'] == 'discarded'
        
        # Verify user was deleted from database
        with client.application.app_context():
            discarded_user = User.query.filter_by(id=user_id).first()
            assert discarded_user is None

    def test_bulk_discard_users(self, client, create_admin_user):
        """Test bulk discarding users."""
        # Create admin user
        admin = create_admin_user(email='admin@example.com', password='admin123')
        
        # Create unverified users
        user_ids = []
        with client.application.app_context():
            for i in range(3):
                unverified_user = User(
                    username=f'unverified{i}',
                    email=f'unverified{i}@example.com',
                    mobile=f'987654321{i}',
                    is_verified=False
                )
                unverified_user.set_password(f'unverified{i}123')
                db.session.add(unverified_user)
                db.session.commit()
                user_ids.append(str(unverified_user.id))
        
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
        
        # Bulk discard users
        response = client.post('/api/v1/auth/bulk/discard-users',
                               data=json.dumps({
                                   'user_ids': user_ids
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['msg'] == 'ok'
        assert data['discarded'] == 3
        
        # Verify users were deleted from database
        with client.application.app_context():
            for user_id in user_ids:
                discarded_user = User.query.filter_by(id=user_id).first()
                assert discarded_user is None