"""S3 storage service.

When USE_S3=true, uploads go to real AWS S3.
When USE_S3=false (default for local dev), files are saved under ./uploads/ and
served by FastAPI's StaticFiles at /static/.
"""

import os
import uuid
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.config import get_settings

settings = get_settings()
_executor = ThreadPoolExecutor(max_workers=4)

LOCAL_UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"
LOCAL_UPLOADS_DIR.mkdir(exist_ok=True)


def _upload_to_s3_sync(file_bytes: bytes, key: str, content_type: str) -> str:
    import boto3
    s3 = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"


def _save_locally(file_bytes: bytes, key: str) -> str:
    path = LOCAL_UPLOADS_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(file_bytes)
    return f"/static/{key}"


async def upload_image(file_bytes: bytes, original_filename: str, content_type: str) -> tuple[str, str]:
    """Upload image and return (url, s3_key)."""
    ext = Path(original_filename).suffix or ".jpg"
    key = f"images/{uuid.uuid4().hex}{ext}"

    loop = asyncio.get_event_loop()
    if settings.use_s3:
        url = await loop.run_in_executor(_executor, _upload_to_s3_sync, file_bytes, key, content_type)
    else:
        url = await loop.run_in_executor(_executor, _save_locally, file_bytes, key)

    return url, key


async def delete_image(s3_key: str) -> None:
    if not s3_key:
        return
    loop = asyncio.get_event_loop()
    if settings.use_s3:
        def _delete():
            import boto3
            s3 = boto3.client(
                "s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            s3.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        await loop.run_in_executor(_executor, _delete)
    else:
        local = LOCAL_UPLOADS_DIR / s3_key
        if local.exists():
            await loop.run_in_executor(_executor, local.unlink)
