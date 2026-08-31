import asyncio
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.models import User, Project
from app.schemas import ProjectOut, ProjectRenameBody
from app.dependencies import get_current_user
from app.services.storage import fetch_bytes, signed_url, upload_image, upload_text
from app.services.depth import estimate_depth_with_map
from app.services.bricks import describe_build
from app.services.ldraw import to_ldraw
from app.services.legolize import refine_plan, render_facade, render_massing
from app.services.reconstruct import reconstruct
from app.services.solid_plan import plan_from_solid, render_isometric
from app.services.voxel import voxelise
from app.services.segment import crop_to_building, segment_building

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/images", tags=["images"])

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
# Straight off a phone or DSLR, a photo can run tens of megabytes. The original is what
# gets stored; services/bricks.py shrinks a copy down to what the vision API accepts.
MAX_SIZE = 50 * 1024 * 1024  # 50 MB

# The longest edge the analysis runs at. The original is what gets stored and
# shown; this bounds only the copy the models see.
#
# Nothing downstream wants more. The mask and the depth map are both reduced to
# a stud grid a few dozen cells across, and the depth model already resizes to a
# 1024 pixel edge of its own accord — so past this point the extra pixels are
# carried through several full-frame float arrays and then thrown away. A
# 4000 x 3000 phone photo is 12 megapixels of that, on a machine with 2 GB.
MAX_WORKING_EDGE = 1600

# Resolution and relief are no longer set here. They used to be constants with a
# paragraph of justification attached, and the justification was wrong for half of
# the photographs that came in — see generate_best_plan, which now measures.


# Every image URL the client is handed. The bucket is private, so these have to be
# signed on the way out or the browser just shows a broken icon.
_IMAGE_KEYS = ("previewUrl", "isometricUrl")


def _out(project: Project) -> ProjectOut:
    """Serialise a project with browser-loadable image URLs, minus the model.

    The LDraw source is 80 KB of the 111 KB a finished plan occupies, and the two
    places it is wanted — the 3D viewer and the download button — are both on a
    detail page. Leaving it in meant /history shipped four megabytes to draw a
    list of thumbnails, and Postgres carried the same 80 KB in every row. It now
    lives in object storage and is fetched from GET /{id}/ldraw on demand.

    Rows written before that change still hold it inline; those are stripped here
    too, and the same endpoint serves them from the row. The client only ever sees
    `hasLdraw`.
    """
    out = ProjectOut.model_validate(project)
    out.image_url = signed_url(out.image_url)
    if out.result_json:
        # A shallow copy: signing must not write short-lived URLs back into the
        # SQLAlchemy instance, from where they could be flushed to the database.
        result = dict(out.result_json)
        for key in _IMAGE_KEYS:
            if result.get(key):
                result[key] = signed_url(result[key])
        # Both popped unconditionally — `a or b` would short-circuit past the
        # second pop and leave the key in the payload on new rows.
        inline = result.pop("ldraw", None)
        stored = result.pop("ldrawKey", None)
        result["hasLdraw"] = bool(inline or stored)
        out.result_json = result
    return out


def _png_bytes(image: Image.Image, backdrop=(24, 25, 30)) -> bytes:
    """Flatten an RGBA render onto a solid backdrop and encode it."""
    flat = Image.new("RGB", image.size, backdrop)
    flat.paste(image, (0, 0), image if image.mode == "RGBA" else None)
    buf = io.BytesIO()
    flat.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# Longest we will hold a finished plan back waiting for prose. The description is
# the one step that depends on a third party, and a plan with no name is a far
# better outcome than a request that never returns — the build page renders
# "Untitled Structure" and everything else about the model is intact.
DESCRIPTION_TIMEOUT = 25.0


async def _describe_within_budget(
    file_bytes: bytes, content_type: str, plan: dict
) -> dict:
    """describe_build, but it cannot hold the request open indefinitely."""
    try:
        return await asyncio.wait_for(
            describe_build(file_bytes, content_type, plan), DESCRIPTION_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.warning("Description timed out after %.0fs; shipping the plan without it.",
                       DESCRIPTION_TIMEOUT)
        return {}


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
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    try:
        source = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read that image")

    image_url, s3_key = await upload_image(
        file_bytes, image.filename or "upload.jpg", content_type
    )

    # Analyse a bounded copy. Uploaded straight off a phone, `source` is a dozen
    # megapixels, and every stage after this holds at least one full-frame array
    # of it. The stored image above is the original and is unaffected.
    if max(source.size) > MAX_WORKING_EDGE:
        before = source.size
        source.thumbnail((MAX_WORKING_EDGE, MAX_WORKING_EDGE), Image.Resampling.LANCZOS)
        logger.info("Analysing at %s rather than %s", source.size, before)

    # 1. Which pixels are the building. Without this the sky, being the largest flat
    #    region in most outdoor shots, takes the biggest share of the piece budget.
    segmentation = await segment_building(source)

    # 2. How far away each pixel is. One forward pass gives both the stats we store
    #    and the map the geometry needs.
    depth_stats, depth_map = await estimate_depth_with_map(source)

    # 3. Crop to the subject so the whole stud grid is spent on it, then compute the
    #    plan. Every part number, colour and quantity below is counted, not guessed.
    if segmentation["building_share"] > 0.01:
        work_img, work_depth, work_mask = crop_to_building(
            source, depth_map, segmentation["mask"]
        )
    else:
        logger.info("No building found; building the whole frame instead.")
        work_img, work_depth, work_mask = source, depth_map, None

    # Two geometries, one parts layer. The relief is what a depth map can carry;
    # the solid is a reconstruction, and the only reason it is not the default is
    # that it wants a GPU and 1.7 GB of weights that the deployed instance does
    # not have. Everything downstream — parts, colours, steps, LDraw — is shared.
    settings = get_settings()
    solid_render = None
    if settings.enable_reconstruction:
        mesh = await reconstruct(source, segmentation["mask"] if work_mask is not None else None)
        solid = voxelise(
            mesh,
            max_studs=settings.reconstruction_studs,
            box_coverage=settings.reconstruction_box_coverage,
        )
        plan = plan_from_solid(solid)
        cells = plan.pop("_cells")
        solid_render = (plan.pop("_solid"), plan.pop("_colours"))
        grids = None
    else:
        # Search for the settings, then spend the palette where the model scores
        # worst — under a wall-clock budget, because this is the part that does
        # not cost what it looks like it costs. It is about a second on a laptop
        # and was six minutes on the deployed machine, where one candidate plan
        # runs 5 to 14 seconds and the search enumerated seventy-five of them.
        plan = refine_plan(
            work_img, work_depth, building_mask=work_mask,
            budget=settings.plan_search_seconds,
        )
        grids = plan.pop("_grids")  # numpy — never goes near the database
        cells = grids["cells"]

    grid_w = plan["grid"]["width"]

    # Claude starts here and is collected at the end. It is the longest single
    # step in the request — nine or ten seconds against about three for
    # everything else put together — and it needs nothing that the rendering and
    # the three object-storage writes below produce. Run in sequence it was most
    # of the wait; run alongside them it costs what it costs minus what they do.
    #
    # It reads the plan's grid, palette and step count, and the code below only
    # adds keys to the plan, so there is nothing here for the two to disagree
    # about.
    prose_task = asyncio.create_task(
        _describe_within_budget(file_bytes, content_type, plan)
    )

    model = to_ldraw(
        cells, grid_w, plan["grid"]["courses"], plan["grid"]["depth"],
        name=f"Nebular build — {image.filename or 'upload'}",
    )
    # Out to object storage rather than into the row: see _out(). If the write
    # fails, keep it inline — an oversized row beats losing the model, and the
    # reader handles both shapes.
    try:
        plan["ldrawKey"] = await upload_text(model, "models", ".ldr", "text/plain")
    except Exception:
        logger.exception("Could not store the LDraw model; keeping it in the row.")
        plan["ldraw"] = model

    plan["segmentation"] = {
        "buildingShare": round(segmentation["building_share"], 4),
        "composition": segmentation["composition"],
    }

    # 4. Renders, stored beside the photo rather than inlined into the JSON.
    #    The scale is pixels per stud, not a target image width: pinning the output
    #    to a fixed width means a finer grid draws each stud smaller, and below about
    #    14px the stud's own shadow ring swallows its colour — so raising the stud
    #    count made the picture muddier instead of sharper.
    try:
        if solid_render is not None:
            # A solid is worth walking around, so the two renders are two corners
            # of it rather than a flat elevation and an angle on the same face.
            filled, colours = solid_render
            facade = render_isometric(filled, colours, cell=max(6, 900 // grid_w), azimuth=0)
            massing = render_isometric(filled, colours, cell=max(5, 700 // grid_w), azimuth=1)
        else:
            facade = render_facade(grids["depths"], grids["colours"], scale=max(8, 1600 // grid_w))
            massing = render_massing(grids["depths"], grids["colours"], scale=max(6, 1200 // grid_w))
        plan["previewUrl"], _ = await upload_image(
            _png_bytes(facade), "facade.png", "image/png"
        )
        plan["isometricUrl"], _ = await upload_image(
            _png_bytes(massing), "massing.png", "image/png"
        )
    except Exception:
        logger.exception("Could not store the renders; continuing without them.")

    # 5. Claude named and described what was built while the renders were being
    #    stored. It sees the original photo, not the mask — recognising a
    #    landmark needs the whole frame. Nothing it returns is allowed to alter a
    #    part, a quantity or a coordinate.
    prose = await prose_task
    if prose:
        plan["buildingName"] = prose.get("buildingName") or "Untitled Structure"
        if "description" in prose:
            plan["description"] = prose["description"]
        # Titles only. Each band already carries a description written from the
        # geometry, which says what to lay and in what order — the thing a builder
        # actually needs. Claude supplies the heading above it.
        notes = {n.get("level"): n for n in prose.get("levelNotes", []) if isinstance(n, dict)}
        for step in plan["steps"]:
            note = notes.get(step.get("level"))
            if note and note.get("title"):
                step["title"] = note["title"]
    else:
        plan["buildingName"] = "Untitled Structure"
        plan["descriptionUnavailable"] = True

    project = Project(
        user_id=current_user.id,
        image_url=image_url,
        s3_key=s3_key,
        result_json=plan,
        depth_data=depth_stats,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return _out(project)


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
    return _out(project)


@router.get("/{project_id}/ldraw", response_class=Response)
async def get_ldraw(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The LDraw source for one build, as plain text.

    Proxied through here rather than handed out as a presigned storage URL: the
    viewer reads it with fetch(), which is a cross-origin request that the bucket
    would have to be given its own CORS policy to allow. That policy is a separate
    thing to configure, in a separate dashboard, whose only failure mode is a
    blank viewer with a console error. Passing 80 KB through the API costs
    nothing measurable and keeps the ownership check on the same code path as
    everything else.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    plan = project.result_json or {}
    # Rows written before the model moved out of the database still hold it here.
    text = plan.get("ldraw")
    if text is None and plan.get("ldrawKey"):
        raw = await fetch_bytes(plan["ldrawKey"])
        text = raw.decode("utf-8") if raw else None
    if text is None:
        raise HTTPException(status_code=404, detail="No model stored for this build")

    return Response(
        content=text,
        media_type="text/plain; charset=utf-8",
        # Private: it is one user's build behind a bearer token, and a shared
        # cache holding it would serve it to the next person asking for that URL.
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.patch("/{project_id}", response_model=ProjectOut)
async def rename_project(
    project_id: str,
    body: ProjectRenameBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a build. Only the owner can, and only the title changes."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be blank")
    project.name = name
    await db.commit()
    await db.refresh(project)
    return _out(project)


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
    return [_out(p) for p in result.scalars().all()]
