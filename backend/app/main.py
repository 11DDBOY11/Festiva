"""FastAPI entrypoint for Festiva AI."""

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.briefs import router as briefs_router
from app.api.events import router as events_router
from app.core.config import DEFAULT_SECRETS, settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    # Fail startup if JWT_SECRET is the default value when ENV != dev/test
    is_default = settings.JWT_SECRET in DEFAULT_SECRETS or settings.SECRET_KEY in DEFAULT_SECRETS
    if settings.ENV not in ("dev", "test") and is_default:
        raise RuntimeError(
            f"Cannot start in '{settings.ENV}' environment with default JWT_SECRET / SECRET_KEY. "
            "Please configure a secure random key."
        )
    yield


is_prod = settings.ENV in ("production", "prod")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Festiva AI — Event Planning Copilot API",
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)


@app.middleware("http")
async def security_and_headers_middleware(request: Request, call_next):
    """Enforce payload size limits, request tracking, and defensive HTTP security headers."""
    # Request body size limit check (2MB)
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 2 * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={"detail": "Payload Too Large: maximum allowed body size is 2MB"},
        )

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled server exception [%s]: %s", request_id, exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    # Defensive security headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    if is_prod:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    return response


# Strict CORS configuration
cors_origins = (
    [o for o in settings.cors_origins_list if o != "*"] if is_prod else settings.cors_origins_list
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Include routers
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(briefs_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Health check endpoint for Docker / orchestration."""
    return {"status": "ok", "project": settings.PROJECT_NAME, "env": settings.ENV}
