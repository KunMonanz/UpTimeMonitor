from celery import Celery

from app.config.settings import REDIS_URL
from app.errors.environment_errors import EnvironmentVariableMissingError

if not REDIS_URL:
    raise EnvironmentVariableMissingError("REDIS_URL")

celery_app = Celery(
    "worker", broker=REDIS_URL, backend=REDIS_URL, include=["app.tasks.monitor_tasks"]
)
