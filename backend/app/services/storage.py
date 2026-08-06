"""Object storage: Cloudflare R2, AWS S3, or the local disk.

All three speak the same code path because R2 implements the S3 API, so boto3
drives it unchanged once it is pointed at a different endpoint. What actually
differs:

  * R2 has one global namespace, no regions — it wants `region_name="auto"` and
    a per-account endpoint host.
  * R2 addresses objects as `{endpoint}/{bucket}/{key}` (path style). Real S3
    wants the bucket in the hostname (virtual style) or presigned URLs break, so
    the style is chosen from whether an endpoint was configured rather than being
    a setting anybody has to know about.

Why R2 rather than S3, given the code is the same: S3 charges $0.09/GB to send
bytes to a browser, and every stored object here exists to be sent to a browser.
R2 charges nothing for egress. At this project's size both storage bills round to
zero; the egress one does not.

With no credentials configured (`USE_S3=false`, the local default) files go to
./uploads and are served by FastAPI's StaticFiles at /static/.
"""

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_executor = ThreadPoolExecutor(max_workers=4)

# Long enough to read a results page and come back to it, short enough that a
# link pasted elsewhere stops working.
PRESIGN_TTL = 6 * 60 * 60  # seconds

LOCAL_UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"
LOCAL_UPLOADS_DIR.mkdir(exist_ok=True)


def _endpoint() -> str:
    return settings.s3_endpoint_url.rstrip("/")


@lru_cache(maxsize=1)
def _client():
    """One shared client. boto3 clients are thread-safe for calls, and building
    one is slow enough that doing it per image made listing a history laggy.

    `addressing_style` is not cosmetic. Left to itself, boto3 presigns against the
    global `s3.amazonaws.com` host; S3 answers that with a 307 to the regional
    host, and the redirected request carries a signature computed for the old host
    — so the browser gets SignatureDoesNotMatch and shows a broken image, while
    every SDK call from the server keeps working. Pinning the style puts the right
    host in the string that actually gets signed.
    """
    import boto3
    from botocore.config import Config

    custom = bool(_endpoint())
    return boto3.client(
        "s3",
        endpoint_url=_endpoint() or None,
        region_name="auto" if custom else settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if custom else "virtual"},
        ),
    )


def _object_url(key: str) -> str:
    """The canonical stored URL for a key. Never handed to a browser as-is — the
    bucket is private, so `signed_url` rewrites it on the way out. It exists so
    that a row written under one backend can still be read after a move."""
    if _endpoint():
        return f"{_endpoint()}/{settings.s3_bucket_name}/{key}"
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"


def _key_from_url(url: str) -> str | None:
    """Recover the object key from a stored URL, or None if it is not ours.

    Both prefixes are tried, not just the configured one: rows written before a
    move from S3 to R2 still carry the old host, and the key inside is the same.
    """
    for prefix in (
        f"{_endpoint()}/{settings.s3_bucket_name}/" if _endpoint() else None,
        f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/",
    ):
        if prefix and url.startswith(prefix):
            return url[len(prefix):]
    return None


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #

def _put_sync(data: bytes, key: str, content_type: str) -> str:
    _client().put_object(
        Bucket=settings.s3_bucket_name, Key=key, Body=data, ContentType=content_type
    )
    return _object_url(key)


def _save_locally(data: bytes, key: str) -> str:
    path = LOCAL_UPLOADS_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/static/{key}"


async def _put(data: bytes, key: str, content_type: str) -> str:
    loop = asyncio.get_event_loop()
    if settings.use_s3:
        return await loop.run_in_executor(_executor, _put_sync, data, key, content_type)
    return await loop.run_in_executor(_executor, _save_locally, data, key)


async def upload_image(
    file_bytes: bytes, original_filename: str, content_type: str
) -> tuple[str, str]:
    """Upload an image and return (url, key)."""
    ext = Path(original_filename).suffix or ".jpg"
    key = f"images/{uuid.uuid4().hex}{ext}"
    return await _put(file_bytes, key, content_type), key


async def upload_text(text: str, prefix: str, ext: str, content_type: str) -> str:
    """Upload a text document and return its key — not its URL.

    The key is what gets stored, because these are read back through the API
    rather than linked to directly, and a key survives a change of storage
    backend where a hostname does not.
    """
    key = f"{prefix}/{uuid.uuid4().hex}{ext}"
    await _put(text.encode("utf-8"), key, content_type)
    return key


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #

def _get_sync(key: str) -> bytes:
    return _client().get_object(Bucket=settings.s3_bucket_name, Key=key)["Body"].read()


async def fetch_bytes(key: str) -> bytes | None:
    """Read an object back. None if it is not there — a missing render or model
    file should degrade the page, not fail the request."""
    loop = asyncio.get_event_loop()
    try:
        if settings.use_s3:
            return await loop.run_in_executor(_executor, _get_sync, key)
        path = LOCAL_UPLOADS_DIR / key
        if not path.exists():
            return None
        return await loop.run_in_executor(_executor, path.read_bytes)
    except Exception:
        logger.exception("Could not read %s from storage.", key)
        return None


def signed_url(url: str, expires_in: int = PRESIGN_TTL) -> str:
    """Turn a stored object URL into one a browser can actually load.

    The bucket is private, so the plain object URL answers 403 and an <img>
    pointing at it renders as a broken icon with no error anywhere — the failure
    is entirely inside the browser. Signing at response time (rather than storing
    a signed URL) keeps the link short-lived and the bucket closed.

    Anything that is not one of ours — a /static/ path in local mode, or an
    already-signed URL — is passed through untouched.
    """
    if not settings.use_s3 or not url:
        return url
    key = _key_from_url(url)
    if key is None or "?" in url:
        return url
    try:
        return _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except Exception:
        # A broken image beats a broken page.
        logger.exception("Could not sign %s; returning the unsigned URL.", key)
        return url


async def delete_image(key: str) -> None:
    if not key:
        return
    loop = asyncio.get_event_loop()
    if settings.use_s3:
        def _delete():
            _client().delete_object(Bucket=settings.s3_bucket_name, Key=key)
        await loop.run_in_executor(_executor, _delete)
    else:
        local = LOCAL_UPLOADS_DIR / key
        if local.exists():
            await loop.run_in_executor(_executor, local.unlink)
