import abc
import os

from fastapi_mail import FastMail, MessageSchema, MessageType

from app.config.email_config import mail_config

class EmailEngine(abc.ABC):
    @abc.abstractmethod
    async def send_email(
        self, to_email: str | list[str], 
        subject: str, body: dict, 
        template_name: str
    ) -> None:
        pass


class SMTPEngine(EmailEngine):
    async def send_email(
        self, 
        to_email: str | list[str], 
        subject: str, 
        body: dict, 
        template_name: str
    ) -> None:
        recipients = [to_email] if isinstance(to_email, str) else to_email
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=body,
            subtype=MessageType.html,
        )
        fm = FastMail(mail_config)
        await fm.send_message(message, template_name=template_name)
        
def get_email_client() -> EmailEngine:
    engine_type = os.getenv("EMAIL_ENGINE", "smtp")
    match engine_type:
        case "smtp":
            return SMTPEngine()
        case _:
            raise ValueError(f"Unknown EMAIL_ENGINE: {engine_type}")
