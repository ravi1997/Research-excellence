# Project Summary

## Overall Goal
Create a comprehensive QWEN.md file to document the AIIMS Research Excellence Portal, a Flask-based web application for managing research activities, publications, and achievements at AIIMS, providing guidance for future development sessions.

## Key Knowledge
- **Technology Stack**: Python Flask, PostgreSQL, SQLAlchemy ORM, Redis, Gunicorn, Docker, Tailwind CSS
- **Authentication**: JWT-based with role-based access control (SUPERADMIN, ADMIN, USER, VERIFIER)
- **Project Structure**: Application factory pattern in `app/__init__.py`, models in `app/models/`, routes organized by API version in `app/routes/v1/`
- **Configuration**: Environment-based configuration (development, testing, production) in `app/config.py`
- **Security Features**: Password complexity, account lockout after 5 failed attempts, OTP-based authentication, content security policies
- **Database**: PostgreSQL as primary database with SQLAlchemy ORM, with auto-migration support
- **Deployment**: Docker containerization with Gunicorn WSGI server, exposing port 5500
- **Frontend**: HTML templates with Tailwind CSS, built using npm scripts

## Recent Actions
- **[DONE]** Analyzed the project directory structure and examined key files
- **[DONE]** Identified the project as a Flask-based research management application for AIIMS
- **[DONE]** Examined configuration files (requirements.txt, package.json, Dockerfile, config.py)
- **[DONE]** Reviewed the main application initialization in run.py and app/__init__.py
- **[DONE]** Studied the User model to understand the data structure and security features
- **[DONE]** Created a comprehensive QWEN.md file with project overview, building/running instructions, and development conventions

## Current Plan
- **[DONE]** Create comprehensive QWEN.md file documenting the AIIMS Research Excellence Portal
- **[DONE]** Include detailed information about architecture, technologies, features, and development practices
- **[DONE]** Provide clear instructions for building, running, and deploying the application
- **[DONE]** Document security practices and code structure conventions

---

## Summary Metadata
**Update time**: 2025-10-09T05:40:35.640Z 
