from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl


class MonitorUrlBase(BaseModel):
    url: HttpUrl


class MonitorUrlCreate(MonitorUrlBase):
    group_id: UUID | None = None


class MonitorUrlUpdate(MonitorUrlBase):
    status: bool


class MonitorUrlResponse(MonitorUrlBase):
    id: UUID
    is_up: bool
    owner_user_id: UUID | None = None
    owner_group_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)
