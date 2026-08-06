"""Email and password sign-in, kept in our own database.

Why not a provider: the objection to storing users yourself is usually "storing
passwords is unsafe", and that is not what happens here or anywhere else. What is
stored is a bcrypt hash with a per-user salt — the same thing WorkOS, Clerk and
Auth0 store, in their database instead of ours. The hash is not reversible and a
database dump does not yield anybody's password.

What a provider actually sells is the surrounding work: email verification,
password reset, breach-list checks, MFA, and an audit trail. Of those, the two
that matter here are reset and verification, and both need an outbound mail
service, which is the one piece that genuinely cannot be self-hosted for free.
Everything else in that list is code that belongs in this file, and most of it is
now here.

Still missing, and deliberately, because each needs an account this project does
not have yet:
  * email verification and password reset — need a sender (Resend's free tier is
    3,000/month, which is far past what this will use)
  * MFA
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.ratelimit import client_key, login_limiter, register_limiter
from app.schemas import (
    ChangePasswordRequest, LoginRequest, RegisterRequest, TokenOut, UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    # bcrypt hashes at most 72 bytes and silently ignores the rest, so a
    # 200-character passphrase is no stronger than its first 72 bytes. The schema
    # rejects anything longer rather than accepting it and quietly truncating,
    # which would let two different passwords open the same account.
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        # `tv` is what makes revocation possible: get_current_user compares it
        # against the row, so bumping the row invalidates every token already out
        # there. Without it a leaked token is valid for its full seven days and
        # there is nothing anyone can do about it.
        {"sub": user.id, "tv": user.token_version, "exp": expire},
        settings.secret_key,
        algorithm="HS256",
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not register_limiter.allow(client_key(request)):
        raise HTTPException(status_code=429, detail="Too many sign-ups from this address. Try again shortly.")

    existing_email = await db.execute(select(User).where(User.email == body.email))
    if existing_email.scalar_one_or_none():
        # This does tell a caller that an address has an account. That is a real
        # disclosure, and it is the deliberate trade every consumer product makes:
        # the alternative is to accept the registration silently and mail the
        # owner, which needs a mail service and turns a typo into a dead end. The
        # rate limit above is what stops it being usable for bulk enumeration.
        raise HTTPException(status_code=409, detail="Email already registered")

    existing_username = await db.execute(select(User).where(User.username == body.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=_hash_password(body.password),
        avatar=body.avatar,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenOut(access_token=_create_token(user), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Two buckets. Per-address stops one machine grinding through a word list;
    # per-account stops a botnet spread across many addresses converging on one
    # inbox. Either alone leaves the other attack wide open.
    if not login_limiter.allow(f"ip:{client_key(request)}") or not login_limiter.allow(
        f"email:{body.email.lower()}"
    ):
        raise HTTPException(
            status_code=429, detail="Too many attempts. Wait a minute and try again."
        )

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(body.password, user.password_hash):
        # One message for both cases, so the response cannot be used to check
        # whether an address has an account.
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenOut(access_token=_create_token(user), user=UserOut.model_validate(user))


@router.post("/change-password", response_model=TokenOut)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the password, and cut off every session signed under the old one.

    The current password is required even though the caller is already
    authenticated: a token found on a shared computer should not be enough to
    take the account away from its owner.
    """
    if not _verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="That is the password you already have")

    current_user.password_hash = _hash_password(body.new_password)
    current_user.token_version += 1
    await db.commit()
    await db.refresh(current_user)
    # A fresh token, so the caller is not logged out of the device they just used
    # to change it.
    return TokenOut(access_token=_create_token(current_user), user=UserOut.model_validate(current_user))


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_everywhere(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invalidate every token for this user, including the one making the call.

    Ordinary logout is a client-side act — the browser forgets the token. That is
    fine for leaving a machine you trust and useless for one you do not, because
    anyone who copied the token still holds a working credential. This is the
    version that actually revokes.
    """
    current_user.token_version += 1
    await db.commit()
