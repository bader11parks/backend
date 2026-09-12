from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import settings
from app.db import SessionLocal, engine, sync_database_url
from app.services.seed import seed_products

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mazaj")


def run_migrations() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_database_url())
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_migrations()
    async with SessionLocal() as session:
        await seed_products(session)
    yield
    await engine.dispose()


app = FastAPI(title="Mazaj Rituals API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(router)
