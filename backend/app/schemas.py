from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, field_validator


# ---- Auth ----

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    avatar: str = "🟡"

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 20:
            raise ValueError("Username must be 3–20 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    avatar: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- Projects ----

class ProjectOut(BaseModel):
    id: str
    user_id: str
    image_url: str
    result_json: dict[str, Any] | None
    depth_data: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Friends ----

class FriendRequestBody(BaseModel):
    target_username: str


class FriendshipOut(BaseModel):
    id: str
    status: str
    is_requester: bool
    friend: UserOut

    model_config = {"from_attributes": True}


# ---- Messages ----

class MessageOut(BaseModel):
    id: str
    sender_id: str
    sender_username: str
    sender_avatar: str
    receiver_id: str | None
    content: str
    msg_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageBody(BaseModel):
    content: str
    receiver_id: str | None = None


# ---- Depth / Analysis ----

class DepthData(BaseModel):
    width: int
    height: int
    mean_depth: float
    depth_variance: float
    edge_strength: float
    layer_distribution: list[float]
    foreground_ratio: float
    background_ratio: float
    dominant_depth_zone: str
    error: str | None = None
