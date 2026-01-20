"""FastAPI Backend - Main Entry Point."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db, DatabaseManager
from .routers import auth, activities, health, ai, workouts

# Background sync task
_sync_task = None
_sync_running = False

async def background_sync_task():
    """Background task that syncs data from Garmin every 5 minutes."""
    global _sync_running
    
    while True:
        try:
            await asyncio.sleep(300)  # Wait 5 minutes
            
            # Check if we should sync (only if authenticated)
            from .routers.auth import get_garmin_service
            try:
                garmin = get_garmin_service()
                if not garmin.is_authenticated:
                    continue
            except Exception:
                continue
            
            _sync_running = True
            print(f"[Background Sync] Starting sync at {datetime.now().isoformat()}")
            
            from datetime import date, timedelta
            today = date.today()
            
            # Sync recent activities
            try:
                activities = garmin.get_activities(limit=20)
                for act in activities:
                    if isinstance(act, dict):
                        DatabaseManager.save_activity(act)
                DatabaseManager.update_sync_status("activities", True, len(activities) if isinstance(activities, list) else 0, 0)
                print(f"[Background Sync] Synced {len(activities) if isinstance(activities, list) else 0} activities")
            except Exception as e:
                print(f"[Background Sync] Activities sync failed: {e}")
            
            # Sync health stats for last 3 days
            try:
                count = 0
                for i in range(3):
                    stat_date = today - timedelta(days=i)
                    try:
                        stats = garmin.get_stats(stat_date)
                        if stats:
                            DatabaseManager.save_health_stats(stat_date, stats)
                            count += 1
                    except Exception:
                        pass
                DatabaseManager.update_sync_status("health_stats", True, count, 0)
                print(f"[Background Sync] Synced {count} health stats")
            except Exception as e:
                print(f"[Background Sync] Health stats sync failed: {e}")
            
            # Sync sleep for last 2 days
            try:
                count = 0
                for i in range(2):
                    sleep_date = today - timedelta(days=i)
                    try:
                        sleep = garmin.get_sleep_data(sleep_date)
                        if sleep:
                            DatabaseManager.save_sleep_data(sleep_date, sleep)
                            count += 1
                    except Exception:
                        pass
                DatabaseManager.update_sync_status("sleep", True, count, 0)
                print(f"[Background Sync] Synced {count} sleep records")
            except Exception as e:
                print(f"[Background Sync] Sleep sync failed: {e}")
            
            _sync_running = False
            print(f"[Background Sync] Completed at {datetime.now().isoformat()}")
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Background Sync] Error: {e}")
            _sync_running = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global _sync_task
    
    # Startup: Initialize database
    init_db()
    
    # Start background sync task
    _sync_task = asyncio.create_task(background_sync_task())
    print("[Startup] Background sync task started")
    
    yield
    
    # Shutdown: Cancel background task
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
    print("[Shutdown] Background sync task stopped")

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
