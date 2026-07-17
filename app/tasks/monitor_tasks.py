import httpx
import asyncio

from app.config.database_config import SessionLocal
from app.tasks import celery_config
from app.tasks.celery_worker import celery_app
from app.repositories.url_monitor_repository import URLMonitorRepository

celery_app.conf.beat_schedule = celery_config.beat_schedule
celery_app.conf.timezone = "UTC"

@celery_app.task
def monitor_urls():
    """Celery task to monitor URLs tailored for FastAPI."""
    
    async def run_monitoring():

        url_monitor_repo = URLMonitorRepository()
        urls = await url_monitor_repo.get_all_urls()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url_monitor in urls:
                try:
                    response = await client.get(url_monitor.url)
                    is_up = response.status_code == 200
                except httpx.HTTPError:
                    is_up = False
                    
                await url_monitor_repo.update_url_status(url_monitor.id, is_up)


    asyncio.run(run_monitoring())