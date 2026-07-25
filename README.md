# UpTimeMonitor

UpTimeMonitor is a FastAPI-based URL monitoring service that lets users register monitored URLs, receive periodic uptime checks, and get email alerts when a monitored endpoint goes down.

## Features

- User registration and authentication
- Create, view, and update monitored URLs
- Periodic URL checks using Celery tasks
- Email notifications for failed checks
- Async database support via SQLAlchemy

## Project Structure

- app/config: application configuration and environment settings
- app/models: SQLAlchemy models for users and URLs
- app/repositories: database access layer
- app/routes: FastAPI API endpoints
- app/services: email and notification helpers
- app/tasks: Celery worker and monitoring tasks
- tests: test suite scaffold

## Requirements

- Python 3.10+
- Redis
- An async-compatible database (for example SQLite with aiosqlite or PostgreSQL)

## Installation

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root with the following values:

```env
DATABASE_URL=sqlite+aiosqlite:///uptime.db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key
FRONTEND_URL=localhost:3000
EMAIL_ENGINE=smtp
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_SERVER=smtp.example.com
```

You can generate a secure JWT secret with:

```bash
python secrets_generator.py
```

## Running the API

Start the FastAPI application:

```bash
uvicorn main:app --reload
```

The API will be available at:

- http://127.0.0.1:8000/docs for Swagger UI

## Running Background Monitoring

This project uses Celery with Redis for periodic URL checks.

Start the Celery worker with beat scheduling:

```bash
celery -A app.tasks.celery_worker worker --beat -l info
```

## API Overview

### Authentication

- POST /api/v1/users/ - Create a user account
- POST /api/v1/users/login - Log in and retrieve a JWT token

### Monitors

- POST /api/v1/monitors/ - Create a monitored URL
- GET /api/v1/monitors/ - List monitored URLs
- GET /api/v1/monitors/{url_id} - Get a specific monitor
- PATCH /api/v1/monitors/{url_id} - Update a monitor

## Testing

Run tests with:

```bash
pytest
```

## Notes

The monitoring task runs every 5 minutes by default and sends alert emails when a URL changes from healthy to unhealthy.
