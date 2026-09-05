import asyncio
import logging

from app.services.mailer import get_email_client

from .celery_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.send_async_email",
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_async_email_task(self, to_email: str, subject: str, body: dict, template_name):
    try:
        asyncio.run(_send_email(to_email, subject, body, template_name))
        logger.info(f"Email successfully sent to {to_email}")
    except Exception:
        logger.warning(
            f"Failed sending email to {to_email}. "
            f"Attempt {self.request.retries}/{self.max_retries}. Retrying..."
        )
        raise


async def _send_email(to_email: str, subject: str, body: dict, template):
    mail_client = get_email_client()
    await mail_client.send_email(
        to_email=to_email, subject=subject, body=body, template_name=template
    )
