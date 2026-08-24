"""
FastAPI application entrypoint.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import analytics, payments, recovery, gateway

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Set LangSmith env vars
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

    # Initialize database tables
    await init_db()
    yield


app = FastAPI(
    title="AI Revenue Recovery Agent",
    description="Detects failed payments, diagnoses root causes, executes bounded recovery workflows, and measures actual revenue recovered.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(payments.router)
app.include_router(recovery.router)
app.include_router(analytics.router)
app.include_router(gateway.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "AI Revenue Recovery Agent"}


@app.get("/")
async def root():
    return {
        "service": "AI Revenue Recovery Agent",
        "docs": "/docs",
        "health": "/health",
    }
