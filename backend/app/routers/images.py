import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Project
from app.schemas import ProjectOut
from app.dependencies import get_current_user
from app.services.s3 import upload_image
from app.services.depth import estimate_depth
from app.services.bricks import analyze_image

router = APIRouter(prefix="/api/images", tags=["images"])

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 15 * 1024 * 1024  # 15 MB


@router.post("/upload", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def upload_and_analyze(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content_type = image.content_type or "image/jpeg"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")

    file_bytes = await image.read()
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 15 MB)")

    # Run S3 upload and depth estimation in parallel
    image_url, s3_key = await upload_image(file_bytes, image.filename or "upload.jpg", content_type)

    # DepthAnything: estimate 3D structure
    depth_data = await estimate_depth(file_bytes)

    # Claude AI: match LEGO bricks using image + depth
    result_json = await analyze_image(file_bytes, content_type, depth_data)

    project = Project(
        user_id=current_user.id,
        image_url=image_url,
        s3_key=s3_key,
        result_json=result_json,
        depth_data=depth_data,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectOut.model_validate(project)


@router.get("/status/{project_id}", response_model=ProjectOut)
async def get_project_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut.model_validate(project)


@router.get("/history", response_model=list[ProjectOut])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .limit(50)
    )
    return [ProjectOut.model_validate(p) for p in result.scalars().all()]
