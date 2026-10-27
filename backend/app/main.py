"""FastAPI entrypoint for Festiva AI."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.core.config import DEFAULT_SECRETS, settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    # Fail startup if JWT_SECRET is the default value when ENV != dev
    is_default = settings.JWT_SECRET in DEFAULT_SECRETS or settings.SECRET_KEY in DEFAULT_SECRETS
    if settings.ENV != "dev" and is_default:
        raise RuntimeError(
            f"Cannot start in '{settings.ENV}' environment with default JWT_SECRET / SECRET_KEY. "
            "Please configure a secure random key."
        )
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Festiva AI — Event Planning Copilot API",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(events_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Health check endpoint for Docker / orchestration."""
    return {"status": "ok", "project": settings.PROJECT_NAME, "env": settings.ENV}
