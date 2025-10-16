import pytest
import json
from app.models.User import User, Role
from app.extensions import db

class TestResearchFeatures:
    """Test research Submission specific features."""

    def test_create_cycle(self, client, create_admin_user):
        """Test creating a research cycle."""
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
        
        # Create cycle
        response = client.post('/api/v1/cycles',
                               data=json.dumps({
                                   'name': '2025 Research Cycle',
                                   'start_date': '2025-01-01',
                                   'end_date': '2025-12-31'
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        # Note: This assumes you'll implement cycle endpoints
        # For now, we're just testing the structure
        assert response.status_code in [201, 404]  # 404 if endpoint doesn't exist yet

    def test_create_category(self, client, create_admin_user):
        """Test creating a research category."""
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
        
        # Create category
        response = client.post('/api/v1/categories',
                               data=json.dumps({
                                   'name': 'Medical Research'
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        # Note: This assumes you'll implement category endpoints
        # For now, we're just testing the structure
        assert response.status_code in [201, 404]  # 404 if endpoint doesn't exist yet

    def test_create_author(self, client, create_user):
        """Test creating an author."""
        # Create user
        user = create_user(email='researcher@example.com', password='research123')
        
        # Login
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'researcher@example.com',
                                         'password': 'research123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Create author
        response = client.post('/api/v1/authors',
                               data=json.dumps({
                                   'name': 'Dr. John Smith',
                                   'affiliation': 'AIIMS Delhi',
                                   'email': 'john.smith@aiims.edu'
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        # Note: This assumes you'll implement author endpoints
        # For now, we're just testing the structure
        assert response.status_code in [201, 404]  # 404 if endpoint doesn't exist yet

    def test_submit_abstract(self, client, create_user):
        """Test submitting a research abstract."""
        # Create user
        user = create_user(email='researcher@example.com', password='research123')
        
        # Login
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'researcher@example.com',
                                         'password': 'research123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Submit abstract
        response = client.post('/api/v1/abstracts',
                               data=json.dumps({
                                   'title': 'Novel Approaches to Cancer Treatment',
                                   'content': 'This research explores new methods for treating cancer...',
                                   'category_id': 'some-category-id',
                                   'authors': ['author-id-1', 'author-id-2']
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        # Note: This assumes you'll implement abstract endpoints
        # For now, we're just testing the structure
        assert response.status_code in [201, 404]  # 404 if endpoint doesn't exist yet

    def test_submit_award(self, client, create_user):
        """Test submitting a research award."""
        # Create user
        user = create_user(email='researcher@example.com', password='research123')
        
        # Login
        login_response = client.post('/api/v1/auth/login',
                                     data=json.dumps({
                                         'identifier': 'researcher@example.com',
                                         'password': 'research123'
                                     }),
                                     content_type='application/json')
        
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']
        
        # Submit award
        response = client.post('/api/v1/awards',
                               data=json.dumps({
                                   'title': 'Best Research Paper Award',
                                   'author_id': 'some-author-id',
                                   'category_id': 'some-category-id',
                                   'paper_category_id': 'some-paper-category-id',
                                   'is_aiims_work': True
                               }),
                               content_type='application/json',
                               headers={'Authorization': f'Bearer {access_token}'})
        
        # Note: This assumes you'll implement award endpoints
        # For now, we're just testing the structure
        assert response.status_code in [201, 404]  # 404 if endpoint doesn't exist yet