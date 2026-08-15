"""Catalog FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from smartmirror_shared.logging_config import configure_service_logging
from smartmirror_shared.part_types import ALL_PART_TYPES, REQUIRED_PART_TYPES

from app.routers import router
from app.seed import seed_demo_skus
from app.settings import settings
import app.store as store_module

logger = configure_service_logging("catalog", settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Seed demo SKUs for local kiosk when the catalog is empty."""
    if settings.catalog_seed_demo:
        seed_demo_skus(store_module.store)
    yield


app = FastAPI(title="Smartmirror Catalog", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for local compose and kiosk boot."""
    return {"status": "ok", "service": "catalog"}


@app.get("/part-types")
def part_types() -> dict[str, tuple[str, ...]]:
    """Expose the capture SOP part types to staff UI."""
    return {
        "required": REQUIRED_PART_TYPES,
        "all": ALL_PART_TYPES,
    }
