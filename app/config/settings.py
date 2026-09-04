import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
BACKEND_URL = os.getenv("BACKEND_URL", "uptime.lilyshops.com")
FRONTEND_URL = os.getenv("FRONTEND_URL")
EMAIL_ENGINE = os.getenv("EMAIL_ENGINE")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_SERVER = os.getenv("MAIL_SERVER")

TOKEN_TTL_SECONDS = 60 * 30
