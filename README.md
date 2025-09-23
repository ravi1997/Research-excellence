# AIIMS Research Excellence Portal

A comprehensive web application for managing research activities, publications, and achievements at AIIMS.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- User authentication and authorization with role-based access control
- Research project management
- Publication tracking and citation monitoring
- Research metrics dashboard
- Collaboration tools for researchers
- Admin panel for user and system management
- Audit logging for security and compliance
- Responsive web interface with modern UI

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Node.js 14 or higher (for frontend asset building)
- Redis (for caching and session management)

## Installation

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

## Configuration

1. Copy the example environment file:
   ```bash
   cp app/.env.example app/.env
   ```

2. Edit the `.env` file to configure your environment variables:
   ```bash
   # Flask Configuration
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-secret-key
   
   # Database Configuration
   DATABASE_URI=postgresql://username:password@localhost/research_excellence
   
   # SMS Service Configuration
   SMS_API_URL=https://your-sms-provider/api
   SMS_API_TOKEN=your-sms-api-token
   
   # Email Configuration
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-email-password
   ```

## Database Setup

1. Make sure your PostgreSQL server is running.

2. Create the database:
   ```bash
   createdb research_excellence
   ```

3. Run database migrations:
   ```bash
   flask db upgrade
   ```

## Running the Application

1. Build the CSS assets:
   ```bash
   npm run build-css
   ```

2. Start the Flask development server:
   ```bash
   python run.py
   ```

3. Visit `http://localhost:5500` in your browser.

## Development

### Frontend Development

To watch for CSS changes during development:
```bash
npm run watch-css
```

### Database Migrations

To create a new migration:
```bash
flask db migrate -m "Description of changes"
```

To apply migrations:
```bash
flask db upgrade
```

To rollback migrations:
```bash
flask db downgrade
```

## Testing

Run the test suite:
```bash
python -m pytest
```

Run tests with coverage:
```bash
python -m pytest --cov=app
```

## Deployment

### Production Configuration

1. Set the environment to production:
   ```bash
   export FLASK_ENV=production
   ```

2. Configure production-specific environment variables in `.env`.

3. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5500 run:my_app
   ```

### Docker Deployment

Build the Docker image:
```bash
docker build -t research-excellence .
```

Run the container:
```bash
docker run -p 5500:5500 research-excellence
```

## API Documentation

The API documentation is available at `/api/docs` when the application is running.

### Authentication

Most API endpoints require authentication via JWT tokens. Obtain a token by logging in:
```
POST /api/v1/auth/login
{
  "identifier": "username_or_email",
  "password": "your_password"
}
```

Include the token in subsequent requests:
```
Authorization: Bearer <your_token>
```

### User Management

- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and obtain a token
- `POST /api/v1/auth/logout` - Logout and invalidate token
- `GET /api/v1/auth/me` - Get current user information

### Admin Endpoints

Admin-only endpoints require the `admin` or `superadmin` role:

- `GET /api/v1/user/users` - List all users
- `POST /api/v1/user/users` - Create a new user
- `GET /api/v1/user/users/<user_id>` - Get a specific user
- `PUT /api/v1/user/users/<user_id>` - Update a user
- `DELETE /api/v1/user/users/<user_id>` - Delete a user

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature-name`
5. Create a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.