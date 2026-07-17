from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.google import router as google_router
from app.api.listings import router as listings_router
from app.api.sync import router as sync_router
from app.core.auth import ensure_default_admin, get_current_user
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.models import *  # noqa: F401,F403
from app.api.exports import (
    router as exports_router,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_default_admin(db)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_protected = [Depends(get_current_user)]

app.include_router(auth_router, prefix=settings.api_prefix)
# Google callback must stay public (browser redirect from Google has no JWT).
app.include_router(google_router, prefix=settings.api_prefix)
app.include_router(sync_router, prefix=settings.api_prefix, dependencies=_protected)
app.include_router(listings_router, prefix=settings.api_prefix, dependencies=_protected)

app.include_router(
    exports_router,
    prefix=settings.api_prefix,
)


@app.get("/health")
def health():
    return {"status": "ok"}
