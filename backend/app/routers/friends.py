from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.database import get_db
from app.models import User, Friendship
from app.schemas import FriendRequestBody, FriendshipOut, UserOut
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/friends", tags=["friends"])


def _friendship_to_out(f: Friendship, current_user_id: str) -> FriendshipOut:
    is_req = f.requester_id == current_user_id
    friend_user = f.receiver if is_req else f.requester
    return FriendshipOut(
        id=f.id,
        status=f.status,
        is_requester=is_req,
        friend=UserOut.model_validate(friend_user),
    )


@router.post("/request", status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    body: FriendRequestBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.target_username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot add yourself")

    result = await db.execute(select(User).where(User.username == body.target_username))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.receiver_id == target.id),
                and_(Friendship.requester_id == target.id, Friendship.receiver_id == current_user.id),
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing and existing.status != "rejected":
        raise HTTPException(status_code=409, detail="Friend relationship already exists")

    if existing:
        # A rejected request may be sent again. Reuse the row instead of inserting a
        # second one for the same pair, and re-point the direction so whoever is asking
        # now becomes the requester — B can ask A after A's request to B was rejected.
        existing.requester_id = current_user.id
        existing.receiver_id = target.id
        existing.status = "pending"
        existing.created_at = datetime.utcnow()
        f = existing
    else:
        f = Friendship(requester_id=current_user.id, receiver_id=target.id, status="pending")
        db.add(f)

    await db.commit()
    await db.refresh(f)
    # Eager load relationships for response
    await db.refresh(f, ["requester", "receiver"])
    return _friendship_to_out(f, current_user.id)


@router.post("/accept/{friendship_id}")
async def accept_friend_request(
    friendship_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Friendship).where(Friendship.id == friendship_id))
    f = result.scalar_one_or_none()
    if not f or f.receiver_id != current_user.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if f.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    f.status = "accepted"
    await db.commit()
    await db.refresh(f, ["requester", "receiver"])
    return _friendship_to_out(f, current_user.id)


@router.post("/reject/{friendship_id}")
async def reject_friend_request(
    friendship_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Decline a pending request.

    The row is kept rather than deleted so the rejection is recorded, but it is hidden
    from both parties: it disappears from the receiver's inbox and from the requester's
    sent list, so the requester is never told they were turned down. The requester may
    send a new request later, which reuses this row (see send_friend_request).
    """
    result = await db.execute(select(Friendship).where(Friendship.id == friendship_id))
    f = result.scalar_one_or_none()
    if not f or f.receiver_id != current_user.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if f.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    f.status = "rejected"
    await db.commit()
    await db.refresh(f, ["requester", "receiver"])
    return _friendship_to_out(f, current_user.id)


@router.delete("/{friendship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friendship(
    friendship_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Friendship).where(Friendship.id == friendship_id))
    f = result.scalar_one_or_none()
    if not f or (f.requester_id != current_user.id and f.receiver_id != current_user.id):
        raise HTTPException(status_code=404, detail="Friendship not found")
    await db.delete(f)
    await db.commit()


@router.get("/list", response_model=list[FriendshipOut])
async def list_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(
            or_(Friendship.requester_id == current_user.id, Friendship.receiver_id == current_user.id),
            # Rejected requests stay in the table but are invisible to both sides.
            Friendship.status != "rejected",
        )
    )
    friendships = result.scalars().all()
    out = []
    for f in friendships:
        await db.refresh(f, ["requester", "receiver"])
        out.append(_friendship_to_out(f, current_user.id))
    return out
