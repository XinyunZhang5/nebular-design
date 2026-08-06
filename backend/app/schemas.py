from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field, field_validator


# ---- Auth ----

# Eight, not six. Six lowercase letters is about three hundred million
# combinations, which a rented GPU works through in seconds if the hashes ever
# leak; the rate limiter protects the login endpoint but not a stolen database.
MIN_PASSWORD = 8

# bcrypt reads at most 72 bytes and silently ignores the rest, so "correct horse
# battery staple ..." past that length adds nothing. Rejecting is honest;
# truncating would mean two different passwords open the same account.
MAX_PASSWORD_BYTES = 72


def check_password(v: str) -> str:
    if len(v) < MIN_PASSWORD:
        raise ValueError(f"Password must be at least {MIN_PASSWORD} characters")
    if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long (72 bytes max)")
    return v

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
        return check_password(v)


class LoginRequest(BaseModel):
    email: EmailStr
    # Deliberately unvalidated. Applying the strength rules here would reject an
    # old password that no longer meets them, locking out the very accounts that
    # most need to sign in and change it.
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_valid(cls, v: str) -> str:
        return check_password(v)


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
    name: str | None = None
    result_json: dict[str, Any] | None
    depth_data: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectRenameBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)


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
