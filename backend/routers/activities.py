"""Activities API Router."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .auth import get_garmin_service
from services.garmin_service import DataFetchError
from database import DatabaseManager

router = APIRouter()


class Activity(BaseModel):
    activity_id: str
    activity_type: str
    activity_name: str
    start_time: str
    duration_minutes: float
    distance_km: float
    calories: int
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    elevation_gain: Optional[float] = None
    training_effect: Optional[float] = None


class ActivityListResponse(BaseModel):
    activities: List[Dict[str, Any]]
    total: int


class ActivityStatsResponse(BaseModel):
    total_activities: int
    total_duration_hours: float
    total_distance_km: float
    total_calories: int
    activity_types: Dict[str, int]
    avg_hr: Optional[int] = None


@router.get("/recent", response_model=ActivityListResponse)
async def get_recent_activities(
    limit: int = Query(default=20, le=100),
    activity_type: Optional[str] = None
):
    """Get recent activities."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        activities = garmin.get_activities(limit=limit, activity_type=activity_type)
        
        return ActivityListResponse(
            activities=activities,
            total=len(activities)
        )
    except DataFetchError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date-range")
async def get_activities_by_date(
    start_date: date,
    end_date: Optional[date] = None,
    activity_type: Optional[str] = None
):
    """Get activities within a date range."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        activities = garmin.get_activities_by_date(
            start_date=start_date,
            end_date=end_date or date.today(),
            activity_type=activity_type
        )
        
        return {
            "activities": activities,
            "total": len(activities),
            "start_date": start_date.isoformat(),
            "end_date": (end_date or date.today()).isoformat()
        }
    except DataFetchError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ActivityStatsResponse)
async def get_activity_stats(
    days: int = Query(default=30, le=365)
):
    """Get aggregated activity statistics."""
    try:
        stats = DatabaseManager.get_activity_stats(days=days)
        
        return ActivityStatsResponse(
            total_activities=stats.get("total_activities", 0),
            total_duration_hours=stats.get("total_duration_minutes", 0) / 60,
            total_distance_km=stats.get("total_distance_km", 0),
            total_calories=stats.get("total_calories", 0),
            activity_types=stats.get("activity_types", {}),
            avg_hr=stats.get("avg_hr")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{activity_id}")
async def get_activity_detail(activity_id: str):
    """Get detailed information for a specific activity."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        activity = garmin.get_activity_details(activity_id)
        return activity
        
    except DataFetchError as e:
        raise HTTPException(status_code=404, detail=f"Activity not found: {str(e)}")


@router.get("/{activity_id}/splits")
async def get_activity_splits(activity_id: str):
    """Get activity splits/laps data."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_activity_splits(activity_id)
    except Exception as e:
        return {}


@router.get("/{activity_id}/hr-zones")
async def get_activity_hr_zones(activity_id: str):
    """Get HR zone distribution for an activity."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_activity_hr_zones(activity_id)
    except Exception as e:
        return {}


@router.get("/{activity_id}/weather")
async def get_activity_weather(activity_id: str):
    """Get weather data during an activity."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_activity_weather(activity_id)
    except Exception as e:
        return {}


@router.get("/{activity_id}/exercise-sets")
async def get_activity_exercise_sets(activity_id: str):
    """Get exercise sets for strength training activities."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_activity_exercise_sets(activity_id)
    except Exception as e:
        return {}


@router.get("/{activity_id}/gear")
async def get_activity_gear(activity_id: str):
    """Get gear used for an activity."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_activity_gear(activity_id)
    except Exception as e:
        return {}


@router.get("/{activity_id}/full")
async def get_activity_full_details(activity_id: str):
    """
    Get comprehensive activity details including:
    - Basic activity data
    - Splits/laps
    - HR zone distribution
    - Weather
    - Exercise sets (for strength)
    - Gear
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Fetch all available data
        result = {
            "activity": {},
            "splits": {},
            "hr_zones": {},
            "weather": {},
            "exercise_sets": {},
            "gear": {},
        }
        
        try:
            result["activity"] = garmin.get_activity_details(activity_id)
        except Exception:
            pass
        
        try:
            result["splits"] = garmin.get_activity_splits(activity_id)
        except Exception:
            pass
        
        try:
            result["hr_zones"] = garmin.get_activity_hr_zones(activity_id)
        except Exception:
            pass
        
        try:
            result["weather"] = garmin.get_activity_weather(activity_id)
        except Exception:
            pass
        
        try:
            result["exercise_sets"] = garmin.get_activity_exercise_sets(activity_id)
        except Exception:
            pass
        
        try:
            result["gear"] = garmin.get_activity_gear(activity_id)
        except Exception:
            pass
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
