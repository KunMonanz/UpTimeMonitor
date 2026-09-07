import asyncio
from collections import defaultdict
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
from app.utils.monitor_url_utils import normalize_monitor_url

celery_app.conf.update(
    beat_schedule=celery_config.beat_schedule,
    timezone="UTC",
)


@celery_app.task
def monitor_urls():
    """Celery task to monitor URLs, tailored for FastAPI."""

    async def check_url(client: httpx.AsyncClient, url: str):
        try:
            response = await client.get(url)
            is_up = response.status_code == 200
            status_code = response.status_code
            error_message = None
        except httpx.HTTPError as exc:
            is_up = False
            status_code = None
            error_message = str(exc)
        return url, is_up, status_code, error_message

    async def should_send_down_alert(monitor_id):
        cooldown_key = f"monitor:{monitor_id}:down_alert"
        return await redis_client.set(
            cooldown_key,
            "1",
            ex=DOWN_ALERT_COOLDOWN_SECONDS,
            nx=True,
        )

    def get_recipient_emails(url_monitor: URLMonitor) -> list[str]:
        if url_monitor.owner_user is not None:
            return [url_monitor.owner_user.email]
        if url_monitor.owner_group is not None:
            return list({member.email for member in url_monitor.owner_group.members})
        return []

    async def run_monitoring():
        async with SessionLocal() as db:
            url_monitor_repo = URLMonitorRepository(db)
            monitors = await url_monitor_repo.get_all_urls()
            monitors_by_url: dict[str, list[URLMonitor]] = defaultdict(list)
            for monitor in monitors:
                monitors_by_url[normalize_monitor_url(monitor.url)].append(monitor)

            async with httpx.AsyncClient(timeout=10.0) as client:
                results = await asyncio.gather(
                    *(check_url(client, url) for url in monitors_by_url)
                )

            results_by_url = {
                url: (is_up, status_code, error_message)
                for url, is_up, status_code, error_message in results
            }
            down_alert_candidates: list[
                tuple[URLMonitor, list[str], int | None, str | None]
            ] = []

            for url, url_monitors in monitors_by_url.items():
                is_up, status_code, error_message = results_by_url[url]
                for url_monitor in url_monitors:
                    recipient_emails = get_recipient_emails(url_monitor)
                    status_changed = url_monitor_repo.apply_url_status_update(
                        url_monitor, is_up, status_code
                    )

                    if recipient_emails and status_changed and not is_up:
                        down_alert_candidates.append(
                            (
                                url_monitor,
                                recipient_emails,
                                status_code,
                                error_message,
                            )
                        )

            await url_monitor_repo.save_url_status_updates()

            for (
                url_monitor,
                recipient_emails,
                status_code,
                error_message,
            ) in down_alert_candidates:
                if await should_send_down_alert(url_monitor.id):
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
