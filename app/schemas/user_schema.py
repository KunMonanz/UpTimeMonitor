from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    username: str



class UserCreate(UserBase):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)
    

class Token(BaseModel):
    access_token: str
    token_type: str


class UserLogin(BaseModel):
    username_or_email: str | EmailStr
    password: str


class UserUsernameUpdate(UserBase):
    password: str