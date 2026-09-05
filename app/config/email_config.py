from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import SecretStr

from app.config.settings import MAIL_PASSWORD, MAIL_SERVER, MAIL_USERNAME
from app.errors.environment_errors import EnvironmentVariableMissingError

if not MAIL_PASSWORD:
    raise EnvironmentVariableMissingError("MAIL_PASSWORD")

if not MAIL_SERVER:
    raise EnvironmentVariableMissingError("MAIL_SERVER")

if not MAIL_USERNAME:
    raise EnvironmentVariableMissingError("MAIL_USERNAME")


mail_config = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=SecretStr(MAIL_PASSWORD),
    MAIL_FROM=MAIL_USERNAME,
    MAIL_PORT=465,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=Path(__file__).resolve().parent.parent / "templates" / "emails",
)
