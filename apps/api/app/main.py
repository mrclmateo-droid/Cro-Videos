import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (registra las tablas)
from . import storage
from .config import get_settings
from .db import Base, engine
from .routers import clips, projects, renders, uploads, videos

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP: create_all. Antes de producción, migrar a Alembic.
    Base.metadata.create_all(engine)
    storage.ensure_bucket()
    yield


app = FastAPI(title="ReelForge API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (projects, uploads, videos, clips, renders):
    app.include_router(r.router)


@app.get("/health", tags=["meta"])
def health():
    return {"ok": True}
