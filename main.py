from fastapi import FastAPI

from app.routes.monitor_url_routes import router  as monitor_router

app = FastAPI(prefix="/api", title="URL Monitoring API", description="API for monitoring URLs", version="1.0.0")

app.include_router(monitor_router)


