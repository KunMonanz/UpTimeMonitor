from dns.tokenizer import IDENTIFIER
from email_validator import EmailNotValidError, validate_email
from uuid6 import UUID

from app.config.settings import BACKEND_URL
from app.services.token_service import TokenService
from app.tasks.email_tasks import send_async_email_task


async def is_email(email: str) -> bool:
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


async def send_verification(
    user_id: str, email: str, name: str, token_service: TokenService
):
    token = await token_service.generate_token(identifier=user_id, ttl=1800)
    verify_link = f"https://{BACKEND_URL}/api/v1/users/verify-email?token={token}"
    send_async_email_task.delay(  # type: ignore
        to_email=email,
        subject="Verify your email",
        body={"username": name, "verify_link": verify_link, "expiry_minutes": 30},
        template_name="verify_email.html",
    )


async def send_invitation_email(
    email: str,
    inviter_name: str,
    token_service: TokenService,
    group_id: UUID,
    inviter_id: UUID,
):
    identifier = f"{email}:{group_id!s}:{inviter_id!s}"
    token = await token_service.generate_token(identifier=identifier, ttl=86400)
    invite_link = f"https://{BACKEND_URL}/api/v1/groups/accept-invite?token={token}"
    send_async_email_task.delay(  # type: ignore
        to_email=email,
        subject="You're invited to join UpTimeMonitor",
        body={
            "inviter_name": inviter_name,
            "invite_link": invite_link,
            "expiry_hours": 24,
        },
        template_name="invite_email.html",
    )
