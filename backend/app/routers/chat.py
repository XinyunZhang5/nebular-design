"""Public chatroom — REST history + WebSocket real-time."""

import json
import logging
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models import Message, User
from app.schemas import MessageOut
from app.dependencies import get_current_user, get_optional_user
from app.ws.manager import manager
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


def _msg_to_out(msg: Message, sender: User) -> dict:
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "sender_username": sender.username,
        "sender_avatar": sender.avatar,
        "receiver_id": msg.receiver_id,
        "content": msg.content,
        "msg_type": msg.msg_type,
        "created_at": msg.created_at.isoformat(),
    }


@router.get("/messages", response_model=list[MessageOut])
async def get_public_messages(
    limit: int = 60,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(Message.msg_type == "public")
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    msgs = list(reversed(result.scalars().all()))
    out = []
    for m in msgs:
        await db.refresh(m, ["sender"])
        out.append(MessageOut(
            id=m.id,
            sender_id=m.sender_id,
            sender_username=m.sender.username,
            sender_avatar=m.sender.avatar,
            receiver_id=m.receiver_id,
            content=m.content,
            msg_type=m.msg_type,
            created_at=m.created_at,
        ))
    return out


# ---- WebSocket ----

async def _resolve_ws_user(token: str | None) -> User | None:
    if not token:
        return None
    try:
        from app.dependencies import decode_token
        payload = decode_token(token)
        user_id = payload.get("sub", "")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    except Exception:
        return None


@router.websocket("/ws/chatroom")
async def chatroom_websocket(websocket: WebSocket, token: str | None = None):
    user = await _resolve_ws_user(token)
    await manager.chatroom_connect(websocket)

    # Send history on connect
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Message)
            .where(Message.msg_type == "public")
            .order_by(Message.created_at.desc())
            .limit(60)
        )
        msgs = list(reversed(result.scalars().all()))
        history = []
        for m in msgs:
            await db.refresh(m, ["sender"])
            history.append(_msg_to_out(m, m.sender))

    await websocket.send_text(json.dumps({"type": "history", "messages": history}, default=str))

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            content = (data.get("content") or "").strip()[:500]
            if not content:
                continue

            # Persist to DB
            sender_id = user.id if user else None
            if not sender_id:
                # Guest: create ephemeral sender info in broadcast only
                guest_payload = {
                    "type": "message",
                    "message": {
                        "id": "guest",
                        "sender_id": "guest",
                        "sender_username": data.get("username", "Guest"),
                        "sender_avatar": data.get("avatar", "⚪"),
                        "receiver_id": None,
                        "content": content,
                        "msg_type": "public",
                        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
                    },
                }
                await manager.chatroom_broadcast(guest_payload)
                continue

            async with AsyncSessionLocal() as db:
                msg = Message(sender_id=sender_id, content=content, msg_type="public")
                db.add(msg)
                await db.commit()
                await db.refresh(msg)
                await db.refresh(msg, ["sender"])
                broadcast_payload = {
                    "type": "message",
                    "message": _msg_to_out(msg, msg.sender),
                }

            await manager.chatroom_broadcast(broadcast_payload)

    except WebSocketDisconnect:
        await manager.chatroom_disconnect(websocket)
    except Exception as exc:
        logger.exception("Chatroom WS error: %s", exc)
        await manager.chatroom_disconnect(websocket)
