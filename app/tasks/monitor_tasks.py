import asyncio
from datetime import datetime, timezone

import httpx

from app.config.database_config import SessionLocal
from app.config.settings import DOWN_ALERT_COOLDOWN_SECONDS, FRONTEND_URL
from app.models.url_monitor import URLMonitor
from app.repositories.url_monitor_repository import URLMonitorRepository
from app.services.redis_client import redis_client
from app.tasks import celery_config
from app.tasks.celery_worker import celery_app
from app.tasks.email_tasks import send_async_email_task

celery_app.conf.update(
    beat_schedule=celery_config.beat_schedule,
    timezone="UTC",
)


@celery_app.task
def monitor_urls():
    """Celery task to monitor URLs, tailored for FastAPI."""

    async def check_url(client: httpx.AsyncClient, url_monitor: URLMonitor):
        try:
            response = await client.get(url_monitor.url)
            is_up = response.status_code == 200
            status_code = response.status_code
            error_message = None
        except httpx.HTTPError as exc:
            is_up = False
            status_code = None
            error_message = str(exc)
        return url_monitor, is_up, status_code, error_message

    async def should_send_down_alert(monitor_id):
        cooldown_key = f"monitor:{monitor_id}:down_alert"
        return await redis_client.set(
            cooldown_key,
            "1",
            ex=DOWN_ALERT_COOLDOWN_SECONDS,
            nx=True,
        )

    async def run_monitoring():
        async with SessionLocal() as db:
            url_monitor_repo = URLMonitorRepository(db)
            urls = await url_monitor_repo.get_all_urls()

            async with httpx.AsyncClient(timeout=10.0) as client:
                results = await asyncio.gather(*(check_url(client, um) for um in urls))

            for url_monitor, is_up, status_code, error_message in results:
                recipient_emails: list[str] = []
                if url_monitor.owner_user is not None:
                    recipient_emails = [url_monitor.owner_user.email]
                elif url_monitor.owner_group is not None:
                    recipient_emails = list(
                        {member.email for member in url_monitor.owner_group.members}
                    )

                status_changed = await url_monitor_repo.update_url_status(
                    url_monitor.id, is_up, status_code
                )

                if (
                    recipient_emails
                    and status_changed
                    and not is_up
                    and await should_send_down_alert(url_monitor.id)
                ):
                    send_async_email_task.delay(  # type: ignore
                        to_email=recipient_emails,
                        subject=f"{url_monitor.name} is down",
                        body={
                            "monitor_name": url_monitor.name,
                            "url": url_monitor.url,
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                            "status_code": status_code or "Timeout",
                            "response_time": "N/A",
                            "error_message": error_message or "Non-200 response",
                            "dashboard_link": f"https://{FRONTEND_URL}/monitors/{url_monitor.id}",
                            "manage_alerts_link": f"https://{FRONTEND_URL}/settings/alerts",
                        },
                        template_name="url_down_alert.html",
                    )

    asyncio.run(run_monitoring())
