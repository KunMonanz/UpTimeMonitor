from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response

from app.config.limiter import limiter
from app.routes.group_routes import router as group_router
from app.routes.monitor_url_routes import router as monitor_router
from app.routes.user_routes import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def rate_limit_exception_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))


app = FastAPI(
    lifespan=lifespan,
    title="URL Monitoring API",
    description="API for monitoring URLs",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

app.include_router(group_router)
app.include_router(monitor_router)
app.include_router(user_router)
