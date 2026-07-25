from email_validator import validate_email, EmailNotValidError

from app.config.settings import FRONTEND_URL
from app.services.token_service import TokenService
from app.tasks.email_tasks import send_async_email_task

async def is_email(email: str) -> bool:
    try:
        email_info = validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


async def send_verification(
    user_id: str, 
    email: str, 
    name: str, 
    token_service: TokenService
):
    token = await token_service.generate_token(identifier=user_id, ttl=1800)
    verify_link = f"https://{FRONTEND_URL}/verify-email?token={token}"

    send_async_email_task.delay( # type: ignore
        to_email=email,
        subject="Verify your email",
        body={"username": name, "verify_link": verify_link, "expiry_minutes": 30},
        template_name="verify_email.html",
    )