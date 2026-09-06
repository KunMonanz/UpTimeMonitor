from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GroupBase(BaseModel):
    name: str
    description: str | None = None


class GroupCreate(GroupBase):
    pass


class GroupResponse(GroupBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class AddMemberToGroup(BaseModel):
    email: str
