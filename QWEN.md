# AIIMS Research Excellence Portal

## Project Overview

The AIIMS Research Excellence Portal is a comprehensive web application built with Python Flask for managing research activities, publications, and achievements at AIIMS (All India Institute of Medical Sciences). It provides a platform for researchers to manage their research projects, track publications and citations, and access research metrics dashboards.

### Key Technologies
- **Backend**: Python Flask framework
- **Database**: PostgreSQL (with SQLAlchemy ORM)
- **Frontend**: HTML templates with Tailwind CSS styling
- **Authentication**: JWT-based with role-based access control
- **Deployment**: Docker containerization with Gunicorn WSGI server
- **Caching**: Redis for session management and caching
- **File Storage**: Local file system with upload validation

### Architecture Components
- **Models**: SQLAlchemy ORM models for user, research, and administrative entities
- **Routes**: RESTful API endpoints organized by version and functionality
- **Schemas**: Marshmallow-based serialization/deserialization schemas
- **Services**: Business logic separated into service modules
- **Utils**: General utilities for various application functions
- **Security**: Comprehensive security features including password policies, rate limiting, and access controls
- **Commands**: CLI commands for user management and system setup

### Features
- User authentication and authorization with role-based access control (SUPERADMIN, ADMIN, USER, VERIFIER)
- Research project management system
- Publication tracking and citation monitoring
- Research metrics dashboard
- Collaboration tools for researchers
- Admin panel for user and system management
- Audit logging for security and compliance
- Responsive web interface with modern UI
- File upload capabilities with type and size restrictions
- SMS and email notification services
- OTP-based authentication
- Account lockout protection against brute force attacks

## Building and Running
### Prerequisites
- Python 3.10 or higher
- PostgreSQL 12 or higher
- Node.js 14 or higher (for frontend asset building)
- Redis (for caching and session management)


### Installation and Configuration
1. Clone the repository:
   ```bash
   git clone https://github.com/aiims/research-excellence.git
   cd research-excellence
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Node.js dependencies:
   ```bash
   npm install
   ```

5. Configure environment variables:
   ```bash
   cp app/.env.example app/.env
   ```
   Edit the `.env` file to configure your environment variables including database connection, SMTP settings, and API keys.

### Database Setup and Running
1. Ensure PostgreSQL is running
2. Create the database:
   ```bash
   createdb research_excellence
   ```
3. Run database migrations:
   ```bash
   flask db upgrade
   ```
4. Build CSS assets:
   ```bash
   npm run build-css
   ```
5. Start the application:
   ```bash
   python run.py
   # Or use: flask run
   ```

### Development Commands
- Watch for CSS changes: `npm run watch-css`
- Run tests: `python -m pytest`
- Run tests with coverage: `python -m pytest --cov=app`
- Create database migration: `flask db migrate -m "Description of changes"`
- Apply migrations: `flask db upgrade`
- Rollback migrations: `flask db downgrade`

### Production Deployment
- Use Gunicorn for production: `gunicorn -w 4 -b 0.0.0.0:5500 run:my_app`
- Docker deployment supported: `docker build -t research-excellence .` followed by `docker run -p 5500:5500 research-excellence`

## Development Conventions

### Security Practices
- Password complexity enforcement (minimum 8 characters with mixed case, number, and special character)
- Account lockout after 5 failed login attempts
- Password expiration every 90 days
- JWT token-based authentication with configurable expiration
- Content Security Policy headers
- Rate limiting protection

### ResearchCycle Framework
The application now implements a ResearchCycle framework that manages three distinct phases:
- Submission phase: For submitting research abstracts, awards, and best papers
- Verification phase: For review and verification by designated reviewers
- Final phase: For final screening and selection

### Grading and Category Management
New features include:
- Grading system with customizable criteria and weights
- Category management for organizing research submissions
- Flexible cycle framework supporting independent time windows

### Code Structure
- Flask application initialized in `run.py` using application factory pattern
- Configuration separated by environment (development, testing, production)
- Models organized in `app/models/` with SQLAlchemy ORM
- Routes organized by API version in `app/routes/v1/`
- Schemas in `app/schemas/` using Marshmallow for serialization
- Services in `app/services/` for business logic separation
- Utilities in `app/utils/` for reusable functionality
- Security utilities in `app/security_utils.py`
- Database models with proper relationships and constraints

### Testing Approach
- Pytest for unit and integration testing
- Separate testing configuration in `TestingConfig`
- SQLite in-memory database for faster tests
- Coverage analysis available
- Multiple test files for different aspects of the application

### API Documentation
- API endpoints available at `/api/v1/` with versioning
- JWT token required for most endpoints (sent in headers or cookies)
- API documentation available at `/api/docs` when running
- Role-based authorization controls access to different endpoints
- Standard HTTP response codes and JSON format

### Authentication Flow
- Register: `POST /api/v1/auth/register`
- Login: `POST /api/v1/auth/login` (returns JWT token)
- Logout: `POST /api/v1/auth/logout`
- Current user info: `GET /api/v1/auth/me`

### ResearchCycle API Endpoints

The system now includes ResearchCycle-specific endpoints:

- `GET /api/v1/research/cycles` - List all research cycles
- `POST /api/v1/research/cycles` - Create a new research cycle
- `GET /api/v1/research/cycles/<cycle_id>` - Get a specific research cycle
- `PUT /api/v1/research/cycles/<cycle_id>` - Update a research cycle
- `DELETE /api/v1/research/cycles/<cycle_id>` - Delete a research cycle

### Research Entity Endpoints

Endpoints for managing research entities (abstracts, awards, best papers):

- `GET /api/v1/research/abstracts` - List all abstracts
- `POST /api/v1/research/abstracts` - Create a new abstract
- `GET /api/v1/research/abstracts/<abstract_id>` - Get a specific abstract
- `PUT /api/v1/research/abstracts/<abstract_id>` - Update an abstract
- `DELETE /api/v1/research/abstracts/<abstract_id>` - Delete an abstract

- `GET /api/v1/research/awards` - List all awards
- `POST /api/v1/research/awards` - Create a new award
- `GET /api/v1/research/awards/<award_id>` - Get a specific award
- `PUT /api/v1/research/awards/<award_id>` - Update an award
- `DELETE /api/v1/research/awards/<award_id>` - Delete an award

- `GET /api/v1/research/best-papers` - List all best papers
- `POST /api/v1/research/best-papers` - Create a new best paper
- `GET /api/v1/research/best-papers/<paper_id>` - Get a specific best paper
- `PUT /api/v1/research/best-papers/<paper_id>` - Update a best paper
- `DELETE /api/v1/research/best-papers/<paper_id>` - Delete a best paper

### Grading and Category Endpoints

Endpoints for managing grading and categories:

- `GET /api/v1/research/grading` - List all grades
- `POST /api/v1/research/grading` - Create a new grade
- `GET /api/v1/research/grading/<grade_id>` - Get a specific grade
- `PUT /api/v1/research/grading/<grade_id>` - Update a grade
- `DELETE /api/v1/research/grading/<grade_id>` - Delete a grade

- `GET /api/v1/research/categories` - List all categories
- `POST /api/v1/research/categories` - Create a new category
- `GET /api/v1/research/categories/<category_id>` - Get a specific category
- `PUT /api/v1/research/categories/<category_id>` - Update a category
- `DELETE /api/v1/research/categories/<category_id>` - Delete a category
