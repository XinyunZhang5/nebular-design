import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Bumped whenever every existing session for this user has to stop working:
    # a password change, or "log out everywhere". A JWT carries the value it was
    # signed with, so a token minted before the bump no longer matches and is
    # rejected. Without it there is no way to revoke a token at all — logging out
    # only forgets the token client-side, and anyone who copied it beforehand
    # keeps full access for the remaining seven days.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avatar: Mapped[str] = mapped_column(String(10), default="🟡")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sent_requests: Mapped[list["Friendship"]] = relationship(
        foreign_keys="Friendship.requester_id", back_populates="requester"
    )
    received_requests: Mapped[list["Friendship"]] = relationship(
        foreign_keys="Friendship.receiver_id", back_populates="receiver"
    )
    sent_messages: Mapped[list["Message"]] = relationship(
        foreign_keys="Message.sender_id", back_populates="sender"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # The builder's own title. NULL means "never renamed" — fall back to the name
    # Claude gave the build in result_json. Kept out of result_json so a re-analysis
    # cannot overwrite something the user typed.
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    depth_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="projects")


class Friendship(Base):
    __tablename__ = "friendships"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    requester_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "accepted", "rejected", name="friendship_status"), default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    requester: Mapped["User"] = relationship(foreign_keys=[requester_id], back_populates="sent_requests")
    receiver: Mapped["User"] = relationship(foreign_keys=[receiver_id], back_populates="received_requests")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    sender_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    msg_type: Mapped[str] = mapped_column(
        SAEnum("public", "dm", name="message_type"), default="public"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sender: Mapped["User"] = relationship(foreign_keys=[sender_id], back_populates="sent_messages")
