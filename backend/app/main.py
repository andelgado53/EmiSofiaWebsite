from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth as auth_router
from app.routers import cms_art as cms_art_router
from app.routers import cms_notes as cms_notes_router
from app.routers import cms_photos as cms_photos_router
from app.routers import cms_moments as cms_moments_router
from app.routers import cms_trips as cms_trips_router
from app.routers import public as public_router
from app.routers import public_art as public_art_router
from app.routers import public_moments as public_moments_router
from app.routers import public_trips as public_trips_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on first boot (if they don't already exist)."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Notes for Emi API", lifespan=lifespan)

# CORS middleware — allow origins from CORS_ORIGINS env var (default ["*"] for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router)
app.include_router(cms_art_router.router)
app.include_router(cms_notes_router.router)
app.include_router(cms_photos_router.router)
app.include_router(cms_moments_router.router)
app.include_router(cms_trips_router.router)
app.include_router(public_router.router)
app.include_router(public_art_router.router)
app.include_router(public_moments_router.router)
app.include_router(public_trips_router.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
