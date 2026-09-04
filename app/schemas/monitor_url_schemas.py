from uuid import UUID

from pydantic import BaseModel, HttpUrl


class MonitorUrlBase(BaseModel):
    url: HttpUrl


class MonitorUrlCreate(MonitorUrlBase):
    pass


class MonitorUrlUpdate(MonitorUrlBase):
    status: bool


class MonitorUrlResponse(MonitorUrlBase):
    id: UUID
    is_up: bool

    class Config:
        from_attributes = True
