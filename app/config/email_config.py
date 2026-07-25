from pathlib import Path

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import SecretStr

from app.config.settings import MAIL_PASSWORD, MAIL_SERVER, MAIL_USERNAME

if not MAIL_PASSWORD:
    raise ValueError("MAIL_PASSWORD not set")

if not MAIL_SERVER:
    raise ValueError("MAIL_SERVER not set")

if not MAIL_USERNAME:
    raise ValueError("MAIL_USERNAME not set")


mail_config = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=SecretStr(MAIL_PASSWORD),
    MAIL_FROM=MAIL_USERNAME,
    MAIL_PORT=587,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER = Path(__file__).resolve().parent.parent / "templates" / "emails"
)