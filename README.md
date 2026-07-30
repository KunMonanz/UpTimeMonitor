# UpTimeMonitor

UpTimeMonitor is a FastAPI-based URL monitoring service. Users can register accounts, add URLs to monitor, and receive email alerts when an endpoint becomes unavailable. Periodic checks are executed in the background using Celery.

## Features

- User registration, email verification and JWT authentication
- Create, list and update monitored URLs
- Periodic uptime checks via Celery + Redis
- Email notifications for status changes (templates under `app/templates/emails`)
- Async database access with SQLAlchemy (async drivers supported)

## Project Structure

- `app/config` — application configuration and environment settings
- `app/models` — SQLAlchemy models for users and URL monitors
- `app/repositories` — database access layer
- `app/routes` — FastAPI endpoints (see `app/routes/user_routes.py` and `app/routes/monitor_url_routes.py`)
- `app/services` — email, token and helper services
- `app/tasks` — Celery configuration and monitoring tasks
- `tests` — test suite

## Requirements

- Python 3.10+
- Redis (for Celery/beat and as a task broker)
- An async-compatible database (e.g. SQLite with `aiosqlite` for local development or PostgreSQL for production)

## Installation

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies:

```bash
pip install -r requirements.txt
```

Optionally run Redis locally using Docker:

```bash
docker run -p 6379:6379 --name uptime-redis -d redis:latest
```

## Environment Variables

Create a `.env` file in the project root with the following values (example):

```env
DATABASE_URL=sqlite+aiosqlite:///uptime.db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key
FRONTEND_URL=http://localhost:3000
EMAIL_ENGINE=smtp
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_SERVER=smtp.example.com
```

Generate a secure JWT secret with:

```bash
python secrets_generator.py
```

## Running the API (development)

Start the FastAPI application (from the project root):

```bash
uvicorn main:app --reload
```

Open the interactive API docs at:

- http://127.0.0.1:8000/docs

## Running Background Monitoring (Celery)

Start the Celery worker with beat scheduling (from project root):

```bash
celery -A app.tasks.celery_worker worker --beat -l info
```

If you prefer to run worker and beat separately:

```bash
celery -A app.tasks.celery_worker beat -l info
celery -A app.tasks.celery_worker worker -l info
```

## API Overview

### Authentication

- `POST /api/v1/users/` — Create a user account
- `POST /api/v1/users/login` — Log in and retrieve a JWT token
- `GET /api/v1/users/verify-email?token=<token>` — Verify a user's email (link sent via email)

### Monitors

- `POST /api/v1/monitors/` — Create a monitored URL
- `GET /api/v1/monitors/` — List monitored URLs for the authenticated user
- `GET /api/v1/monitors/{url_id}` — Get a specific monitor
- `PATCH /api/v1/monitors/{url_id}` — Update a monitor

Refer to `app/routes` for implementation details and request/response schemas.

## Testing

Run the test suite with:

```bash
pytest -q
```

## Notes

- The default monitoring cadence is configured in the Celery tasks (typically every 5 minutes). See `app/tasks/monitor_tasks.py` for scheduling and behaviour.
- Email templates are in `app/templates/emails`.
- Use the `secrets_generator.py` helper to create strong secrets for `JWT_SECRET_KEY`.
