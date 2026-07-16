from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database_config import Base, engine
from app.routes.monitor_url_routes import router  as monitor_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    lifespan=lifespan, 
    title="URL Monitoring API", 
    description="API for monitoring URLs", 
    version="1.0.0"
)

app.include_router(monitor_router)


