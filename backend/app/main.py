import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import auth, images, friends, chat, dm

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Nebular Design backend…")
    await init_db()
    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Nebular Design API",
    description="LEGO brick creator platform — Python FastAPI backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve locally-uploaded files (when USE_S3=false)
uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(uploads_dir)), name="static")

# Routers
app.include_router(auth.router)
app.include_router(images.router)
app.include_router(friends.router)
app.include_router(chat.router)
app.include_router(dm.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nebular-design-api"}
