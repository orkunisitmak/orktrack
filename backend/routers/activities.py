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
    activity_type: Optional[str] = None,
    include_details: bool = Query(default=True, description="Include detailed metrics like stress, respiration")
):
    """Get recent activities with optional detailed metrics."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        activities = garmin.get_activities(limit=limit, activity_type=activity_type)
        
        # Enrich activities with detailed metrics if requested
        if include_details and activities:
            enriched_activities = []
            for activity in activities:
                try:
                    activity_id = str(activity.get("activityId", ""))
                    if activity_id:
                        # Fetch detailed data for each activity
                        details = garmin.get_activity_details(activity_id)
                        if details:
                            # Merge detailed metrics into the activity
                            activity["avgStressLevel"] = details.get("avgStressLevel")
                            activity["maxStressLevel"] = details.get("maxStressLevel")
                            activity["avgRespirationRate"] = details.get("avgRespirationRate")
                            activity["maxRespirationRate"] = details.get("maxRespirationRate")
                            activity["performanceCondition"] = details.get("performanceCondition")
                            activity["firstBeatPerformanceCondition"] = details.get("firstBeatPerformanceCondition")
                            activity["avgStrideLength"] = details.get("avgStrideLength")
                            activity["avgPower"] = details.get("avgPower")
                            activity["maxPower"] = details.get("maxPower")
                            activity["normPower"] = details.get("normPower") or details.get("normalizedPower")
                            activity["trainingLoad"] = details.get("trainingLoad") or details.get("activityTrainingLoad")
                            activity["recoveryTimeInMinutes"] = details.get("recoveryTimeInMinutes")
                    enriched_activities.append(activity)
                except Exception as e:
                    # If we can't get details, just use the basic activity data
                    print(f"Warning: Could not fetch details for activity {activity.get('activityId')}: {e}")
                    enriched_activities.append(activity)
            activities = enriched_activities
        
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
    - Splits/laps with detailed metrics
    - Typed splits (more structured)
    - Split summaries
    - HR zone distribution
    - Weather (actual temperature, conditions)
    - Exercise sets (for strength)
    - Gear
    - Stress, respiration, cadence, stride length, performance condition
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Use the new comprehensive method
        result = garmin.get_comprehensive_activity_data(activity_id)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{activity_id}/metrics")
async def get_activity_metrics(activity_id: str):
    """
    Get detailed metrics for an activity suitable for chart display.
    Returns: pace, heart rate, stress, respiration, cadence, stride length, 
    performance condition timeline data when available.
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get comprehensive data
        full_data = garmin.get_comprehensive_activity_data(activity_id)
        
        # Extract chart-friendly data
        result = {
            "activity_id": activity_id,
            "summary": full_data.get("summary", {}),
            "available_metrics": full_data.get("metrics", {}),
            "weather": full_data.get("weather", {}),
            "hr_zones": full_data.get("hr_zones", {}),
            "splits": [],
            "charts": {
                "has_data": False,
                "heart_rate": [],
                "pace": [],
                "cadence": [],
                "stress": [],
                "respiration": [],
                "elevation": [],
                "power": [],
            }
        }
        
        # Process splits into chart-friendly format
        splits_data = full_data.get("splits", {})
        if splits_data and isinstance(splits_data, dict):
            lap_list = splits_data.get("lapDTOs", []) or splits_data.get("laps", [])
            if lap_list:
                for i, lap in enumerate(lap_list):
                    split_info = {
                        "lap_number": i + 1,
                        "duration_seconds": lap.get("duration"),
                        "distance_meters": lap.get("distance"),
                        "avg_hr": lap.get("averageHR"),
                        "max_hr": lap.get("maxHR"),
                        "avg_speed": lap.get("averageSpeed"),
                        "avg_cadence": lap.get("averageRunningCadenceInStepsPerMinute") or lap.get("avgCadence"),
                        "elevation_gain": lap.get("elevationGain"),
                        "elevation_loss": lap.get("elevationLoss"),
                        "avg_respiration": lap.get("avgRespirationRate"),
                        "avg_stress": lap.get("avgStressLevel"),
                    }
                    
                    # Calculate pace (min/km) if we have speed
                    if split_info["avg_speed"] and split_info["avg_speed"] > 0:
                        pace_sec_per_km = 1000 / split_info["avg_speed"]
                        pace_min = int(pace_sec_per_km // 60)
                        pace_sec = int(pace_sec_per_km % 60)
                        split_info["pace_min_km"] = f"{pace_min}:{pace_sec:02d}"
                    
                    result["splits"].append(split_info)
                    
                    # Add to charts
                    if split_info["avg_hr"]:
                        result["charts"]["heart_rate"].append({
                            "lap": i + 1,
                            "value": split_info["avg_hr"],
                            "max": split_info.get("max_hr")
                        })
                        result["charts"]["has_data"] = True
                    
                    if split_info["avg_speed"]:
                        result["charts"]["pace"].append({
                            "lap": i + 1,
                            "value": split_info.get("pace_min_km"),
                            "speed_ms": split_info["avg_speed"]
                        })
                        result["charts"]["has_data"] = True
                    
                    if split_info["avg_cadence"]:
                        result["charts"]["cadence"].append({
                            "lap": i + 1,
                            "value": split_info["avg_cadence"]
                        })
                        result["charts"]["has_data"] = True
                    
                    if split_info["avg_stress"]:
                        result["charts"]["stress"].append({
                            "lap": i + 1,
                            "value": split_info["avg_stress"]
                        })
                        result["charts"]["has_data"] = True
                    
                    if split_info["avg_respiration"]:
                        result["charts"]["respiration"].append({
                            "lap": i + 1,
                            "value": split_info["avg_respiration"]
                        })
                        result["charts"]["has_data"] = True
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{activity_id}/typed-splits")
async def get_activity_typed_splits(activity_id: str):
    """Get typed splits data for an activity."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_activity_typed_splits(activity_id)
    except Exception as e:
        return {}


@router.get("/{activity_id}/split-summaries")
async def get_activity_split_summaries(activity_id: str):
    """Get split summaries for an activity."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_activity_split_summaries(activity_id)
    except Exception as e:
        return {}
