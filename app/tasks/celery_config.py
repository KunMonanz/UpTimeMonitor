from celery.schedules import crontab

beat_schedule = {
    "monitor-urls-every-5-minutes": {
        "task": "app.tasks.monitor_tasks.monitor_urls",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}