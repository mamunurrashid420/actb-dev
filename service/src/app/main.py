"""FastAPI application entry point."""

# Load environment variables from .env.local BEFORE any other imports
# This ensures LLM clients (OpenAI, Anthropic, etc.) can access API keys
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")  # Fallback to .env if .env.local doesn't exist

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.api.admin.route import router as admin_router
from app.api.auth.route import router as auth_router
from app.api.conversations.route import router as conversations_router
from app.api.dashboards.route import router as dashboards_router
from app.api.prompts.route import router as prompts_router
from app.api.public.route import router as public_router
from app.api.snippets.route import router as snippets_router
from app.api.tenant_assets.route import router as tenant_assets_router
from app.api.tenant_connections.route import router as tenant_connections_router
from app.api.tenants.route import router as tenants_router
from app.api.users.route import router as users_router
from app.api.variables.route import router as variables_router
from app.config import get_settings
from app.containers import AgentsContainer

logger = logging.getLogger(__name__)

settings = get_settings()

# Create DI container
container = AgentsContainer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager.

    Handles:
    - DI container wiring to route modules
    - Shared resource initialization
    - Cleanup on shutdown
    """
    # Collect modules that need DI wiring
    wire_modules: list[str] = []

    if settings.playground:
        wire_modules.append("app.api.playground.viz_designer.route")

    if wire_modules:
        container.wire(modules=wire_modules)

    yield

    # Cleanup on shutdown
    if wire_modules:
        container.unwire()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Attach container to app for access in tests
app.state.container = container

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.api_version}


# Register routers
app.include_router(admin_router)
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(auth_router)
app.include_router(tenants_router, prefix="/tenants", tags=["tenants"])
app.include_router(dashboards_router)
app.include_router(tenant_connections_router)
app.include_router(tenant_assets_router)
app.include_router(public_router)
app.include_router(conversations_router)
app.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
app.include_router(snippets_router, prefix="/snippets", tags=["snippets"])
app.include_router(variables_router, prefix="/variables", tags=["variables"])

# Playground routes (dev-only, gated by PLAYGROUND=on)
if settings.playground:
    from app.api.playground.viz_designer.route import router as viz_designer_router

    app.include_router(
        viz_designer_router,
        prefix="/playground/viz_designer",
        tags=["playground"],
    )
    logger.info("Playground routes enabled (PLAYGROUND=on)")
