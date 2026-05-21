"""Direct messages — REST history + per-user WebSocket."""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.database import get_db, AsyncSessionLocal
from app.models import Message, User, Friendship
from app.schemas import MessageOut
from app.dependencies import get_current_user
from app.ws.manager import manager
from app.routers.chat import _resolve_ws_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dm", tags=["dm"])


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


async def _assert_friends(db: AsyncSession, user_a: str, user_b: str):
    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == user_a, Friendship.receiver_id == user_b),
                and_(Friendship.requester_id == user_b, Friendship.receiver_id == user_a),
            ),
            Friendship.status == "accepted",
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You can only DM friends")


@router.get("/history/{friend_id}", response_model=list[MessageOut])
async def dm_history(
    friend_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _assert_friends(db, current_user.id, friend_id)

    result = await db.execute(
        select(Message)
        .where(
            Message.msg_type == "dm",
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == friend_id),
                and_(Message.sender_id == friend_id, Message.receiver_id == current_user.id),
            ),
        )
        .order_by(Message.created_at.asc())
        .limit(100)
    )
    out = []
    for m in result.scalars().all():
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


@router.websocket("/ws/dm/{friend_id}")
async def dm_websocket(websocket: WebSocket, friend_id: str, token: str | None = None):
    user = await _resolve_ws_user(token)
    if not user:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Verify friendship
    async with AsyncSessionLocal() as db:
        try:
            await _assert_friends(db, user.id, friend_id)
        except HTTPException:
            await websocket.close(code=4003, reason="Not friends")
            return

    await manager.dm_connect(user.id, websocket)

    # Send history
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Message)
            .where(
                Message.msg_type == "dm",
                or_(
                    and_(Message.sender_id == user.id, Message.receiver_id == friend_id),
                    and_(Message.sender_id == friend_id, Message.receiver_id == user.id),
                ),
            )
            .order_by(Message.created_at.asc())
            .limit(100)
        )
        history = []
        for m in result.scalars().all():
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

            async with AsyncSessionLocal() as db:
                msg = Message(
                    sender_id=user.id,
                    receiver_id=friend_id,
                    content=content,
                    msg_type="dm",
                )
                db.add(msg)
                await db.commit()
                await db.refresh(msg)
                await db.refresh(msg, ["sender"])
                payload = {"type": "message", "message": _msg_to_out(msg, msg.sender)}

            # Deliver to both parties if online
            await manager.dm_send(user.id, payload)
            await manager.dm_send(friend_id, payload)

    except WebSocketDisconnect:
        await manager.dm_disconnect(user.id, websocket)
    except Exception as exc:
        logger.exception("DM WS error: %s", exc)
        await manager.dm_disconnect(user.id, websocket)
