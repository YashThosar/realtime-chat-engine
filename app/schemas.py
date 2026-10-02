import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RoomCreate(BaseModel):
    name: str


class RoomOut(BaseModel):
    id: uuid.UUID
    name: str
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class RoomMemberOut(BaseModel):
    user_id: uuid.UUID
    username: str
    joined_at: datetime

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    client_msg_id: str


class MessageOut(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    seq: int
    created_at: datetime

    class Config:
        from_attributes = True