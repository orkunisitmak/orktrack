"""FastAPI Backend - Main Entry Point."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db
from .routers import auth, activities, health, ai, workouts

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: Cleanup

app = FastAPI(
    title="OrkTrack API",
    description="AI-Powered Garmin Fitness Dashboard API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(activities.router, prefix="/api/activities", tags=["Activities"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(workouts.router, prefix="/api/workouts", tags=["Workouts"])


@app.get("/")
async def root():
    return {"message": "OrkTrack API", "status": "running"}


@app.get("/api/health-check")
async def health_check():
    return {"status": "healthy"}
