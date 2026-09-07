# UpTimeMonitor

UpTimeMonitor is a FastAPI-based uptime monitoring API for individuals and teams. It lets users create personal monitors, organize shared monitors under groups, and receive email alerts when a monitored website or endpoint goes down.

The app is built around an async FastAPI backend, SQLAlchemy models and repositories, Redis-backed caching/rate limiting, and Celery workers for scheduled background checks.

## What the project does

UpTimeMonitor helps you:

- register and authenticate users with JWTs
- verify email addresses before allowing normal login flow
- create personal URL monitors
- create group-owned URL monitors for shared visibility
- invite users into groups
- notify the right owners when a site is down
- avoid duplicate HTTP checks when multiple monitors point to the same URL

## Key features

### Authentication and users

- User signup
- Login with username or email
- JWT-based authentication
- Email verification flow
- Logout with token blacklisting
- Cached user lookup endpoints

### Monitoring

- Personal monitors owned by a single user
- Group-owned monitors owned by a group
- Async HTTP checks with `httpx`
- Periodic monitoring via Celery Beat
- Per-monitor down-alert cooldowns to avoid repeated spam
- Shared URL deduplication per monitoring cycle
- URL normalization so equivalent URLs like `https://example.com` and `https://example.com/` are checked once in the same cycle

### Groups

- Create groups
- Invite users to groups by email
- Accept invitations through a tokenized link
- Group member and admin roles
- Group members can view group monitors
- Group admins can manage group monitors and membership
- Group members receive down-alert emails for group-owned monitors

### API quality and operational features

- Async SQLAlchemy repository layer
- Redis-backed response caching on common read endpoints
- Pagination on monitor and group list endpoints
- OpenAPI-documented error responses
- Rate limiting for spam-prone routes
- Test suite with `pytest`

## Ownership model

A monitor can be owned by exactly one of:

- a user via `owner_user_id`
- a group via `owner_group_id`

This gives the app dual ownership support:

- **user-owned monitor**: alerts go to that user
- **group-owned monitor**: alerts go to the group members

The database model enforces that a monitor cannot belong to both at once.

## How monitoring works

On each monitoring cycle:

1. all monitor rows are loaded
2. each stored URL is normalized
3. monitors are grouped by normalized URL
4. one HTTP request is made per unique URL
5. the result is applied to every monitor watching that URL
6. status changes are saved
7. down-alert emails are sent to the appropriate owners if cooldown rules allow it

This means if multiple users or groups monitor the same target, the system avoids duplicate outbound checks while still sending emails to the correct recipients.

## Tech stack

- **API framework:** FastAPI
- **ORM:** SQLAlchemy 2.x (async)
- **Database migrations:** Alembic
- **Task queue / scheduler:** Celery + Celery Beat
- **Cache / broker / cooldowns:** Redis
- **HTTP client:** `httpx`
- **Email delivery:** `fastapi-mail`
- **Rate limiting:** `slowapi`
- **Tests:** `pytest`

## Project structure

```text
app/
  config/         Application settings, DB config, JWT, limiter, mail config
  errors/         Custom error types
  models/         SQLAlchemy models
  repositories/   Data access layer
  routes/         FastAPI route handlers
  schemas/        Pydantic request/response models
  services/       Redis, mailer, token services
  tasks/          Celery config and scheduled monitoring/email tasks
  templates/      HTML email templates
  utils/          Shared helpers such as URL normalization
alembic/          Migration environment
tests/            Pytest suite
main.py           FastAPI application entry point
Dockerfile        Container image definition
docker-compose.yaml
README.md
```

## API overview

Base route groups:

- `/api/v1/users`
- `/api/v1/monitors`
- `/api/v1/groups`

### User and auth endpoints

- `POST /api/v1/users/` — create a user account
- `POST /api/v1/users/login` — login and receive a bearer token
- `POST /api/v1/users/logout` — blacklist the current token
- `GET /api/v1/users/verify-email?token=...` — verify a user email
- `GET /api/v1/users/id/{user_id}` — fetch a user by id
- `GET /api/v1/users/username/{username}` — fetch a user by username

### Monitor endpoints

- `POST /api/v1/monitors/` — create a monitor
- `GET /api/v1/monitors/` — list monitors accessible to the current user
- `GET /api/v1/monitors/{url_id}` — fetch one monitor
- `PATCH /api/v1/monitors/{url_id}` — update a monitor
- `DELETE /api/v1/monitors/{url_id}` — delete a monitor

### Group endpoints

- `POST /api/v1/groups/` — create a group
- `GET /api/v1/groups/{group_id}` — get a group
- `DELETE /api/v1/groups/{group_id}` — delete a group
- `POST /api/v1/groups/{group_id}/invite` — send a group invitation
- `GET /api/v1/groups/invites/accept?token=...` — accept a group invitation
- `GET /api/v1/groups/{group_id}/members` — list group members
- `DELETE /api/v1/groups/{group_id}/members/{member_id}` — remove a member
- `GET /api/v1/groups/{group_id}/monitors` — list group monitors

## Pagination

The following endpoints support `offset` and `limit`:

- `GET /api/v1/monitors/`
- `GET /api/v1/groups/{group_id}/members`
- `GET /api/v1/groups/{group_id}/monitors`

Paginated responses follow this shape:

```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "limit": 20
}
```

## Example requests

### Create a personal monitor

```json
{
  "url": "https://example.com"
}
```

### Create a group-owned monitor

```json
{
  "url": "https://example.com",
  "group_id": "your-group-uuid"
}
```

## Environment variables

Create a `.env` file in the project root.

Example:

```env
DATABASE_URL=sqlite+aiosqlite:///./monitor.db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=replace-with-a-long-random-secret
BACKEND_URL=localhost:8000
FRONTEND_URL=localhost:3000
EMAIL_ENGINE=smtp
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_SERVER=smtp.example.com
DOWN_ALERT_COOLDOWN_SECONDS=3600
VERIFY_EMAIL_COOLDOWN_SECONDS=300
GROUP_INVITE_COOLDOWN_SECONDS=900
```

### Variable notes

- `DATABASE_URL`: async SQLAlchemy database URL
- `REDIS_URL`: Redis connection used for caching, cooldowns, and Celery broker/backend-related usage
- `JWT_SECRET_KEY`: secret used to sign access tokens
- `BACKEND_URL`: base host used in backend-generated links such as verification/invite flows
- `FRONTEND_URL`: used in alert emails for dashboard/settings links
- `EMAIL_ENGINE`: currently `smtp`
- `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_SERVER`: SMTP configuration
- cooldown variables control anti-spam behavior for alerts and email flows

Generate a strong secret with:

```bash
python secrets_generator.py
```

## Local development setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
python -m venv venv
venv\Scripts\activate.bat
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Redis

If you already have Redis installed, run it normally.

Or run Redis with Docker:

```bash
docker run -p 6379:6379 --name uptime-redis -d redis:7-alpine
```

### 4. Run database migrations

This project expects schema changes to be applied through Alembic.

Create a migration after model changes:

```bash
alembic revision --autogenerate -m "describe your change"
```

Apply migrations:

```bash
alembic upgrade head
```

### 5. Start the API

```bash
uvicorn main:app --reload
```

Open the docs at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Running background workers

Start the Celery worker:

```bash
celery -A app.tasks.celery_worker worker --loglevel=info
```

Start Celery Beat:

```bash
celery -A app.tasks.celery_worker beat --loglevel=info
```

The default schedule checks monitors every 5 minutes.

## Running with Docker Compose

The Compose setup includes these services:

- `redis`
- `migrate`
- `web`
- `celery_worker`
- `celery_beat`

### Start everything

```bash
docker compose up --build
```

### Run only migrations in Docker

```bash
docker compose run --rm migrate
```

### What the `migrate` service does

It runs:

```bash
alembic upgrade head
```

The `web`, `celery_worker`, and `celery_beat` services wait for that migration step to complete successfully before starting.

## Caching and rate limiting

### Cached read endpoints

The app caches common read responses, including:

- user lookups
- group detail
- group members
- group monitors
- monitor list/detail

### Rate limiting and cooldowns

Spam-prone flows are limited using Redis-backed controls, including:

- account creation
- login
- logout
- verification link resend behavior
- group invitation sending
- down-alert email cooldowns per monitor

## Email templates

Email templates live in:

- `app/templates/emails/verify_email.html`
- `app/templates/emails/invite_email.html`
- `app/templates/emails/url_down_alert.html`

## Testing

Run all tests:

```bash
pytest -q
```

Or on Windows, if path/import issues come up with your shell setup:

```bash
./venv/Scripts/python.exe -m pytest -q
```

## Current status

The project currently includes test coverage for user, group, monitor, and monitoring-task behavior.

## Notes and assumptions

- The API is async-first.
- Redis is an important dependency for caching, cooldowns, and background processing.
- The app uses Alembic for schema migrations rather than creating tables on startup.
- Monitoring is optimized to avoid duplicate URL checks within a single cycle, but multiple monitor rows may still exist in the database for the same normalized URL under different owners.
- Swagger docs include documented exception responses for common failure cases.
