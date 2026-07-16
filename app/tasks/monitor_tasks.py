import requests
from app.tasks import celery_config
from app.tasks.celery_worker import celery_app
from app.repositories.url_monitor_repository import URLMonitorRepository

celery_app.conf.beat_schedule = celery_config.beat_schedule
celery_app.conf.timezone = "UTC"

@celery_app.task
async def monitor_urls():
    """Celery task to monitor URLs."""
    url_monitor_repo = URLMonitorRepository()
    urls = await url_monitor_repo.get_all_urls()

    for url_monitor in urls:
        response = requests.get(url_monitor.url)
        if response.status_code == 200:
            await url_monitor_repo.update_url_status(url_monitor.id, True)
        else:
            await url_monitor_repo.update_url_status(url_monitor.id, False)