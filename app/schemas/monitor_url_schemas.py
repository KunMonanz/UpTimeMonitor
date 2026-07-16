from pydantic import BaseModel, HttpUrl

class MonitorUrlBase(BaseModel):
    url: HttpUrl


class MonitorUrlCreate(MonitorUrlBase):
    pass

class MonitorUrlUpdate(MonitorUrlBase):
    status: bool

class MonitorUrlResponse(MonitorUrlBase):
    id: int
    status: bool

    class Config:
        orm_mode = True