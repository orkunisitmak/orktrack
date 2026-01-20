"""Health Data API Router."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .auth import get_garmin_service
from services.garmin_service import DataFetchError
from services.data_processor import DataProcessor
from database import DatabaseManager

router = APIRouter()


class DailyStats(BaseModel):
    date: str
    steps: int
    calories: int
    active_minutes: int
    distance_km: float
    resting_hr: Optional[int] = None
    avg_stress: Optional[int] = None


class HealthSummary(BaseModel):
    avg_steps: int
    total_steps: int
    avg_resting_hr: Optional[int] = None
    avg_stress: Optional[int] = None
    total_active_minutes: int
    total_calories: int
    avg_sleep_hours: float
    avg_sleep_score: Optional[int] = None


class SleepData(BaseModel):
    date: str
    total_hours: float
    deep_hours: float
    light_hours: float
    rem_hours: float
    awake_hours: float
    sleep_score: Optional[int] = None
    avg_hr: Optional[int] = None


@router.get("/daily-stats")
async def get_daily_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: int = Query(default=14, le=90)
):
    """Get daily health statistics."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not start_date:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        
        stats_list = garmin.get_stats_range(start_date, end_date)
        
        # Process into cleaner format
        processed = []
        for stats in stats_list:
            processed.append({
                "date": stats.get("date", stats.get("calendarDate")),
                "steps": stats.get("totalSteps", 0) or 0,
                "calories": stats.get("totalKilocalories", 0) or 0,
                "active_minutes": (
                    (stats.get("highlyActiveSeconds", 0) or 0) +
                    (stats.get("activeSeconds", 0) or 0)
                ) // 60,
                "distance_km": (stats.get("totalDistanceMeters", 0) or 0) / 1000,
                "resting_hr": stats.get("restingHeartRate"),
                "avg_stress": stats.get("averageStressLevel"),
                "floors": stats.get("floorsAscended", 0) or 0,
            })
        
        return {"stats": processed, "total": len(processed)}
        
    except DataFetchError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=HealthSummary)
async def get_health_summary(days: int = Query(default=7, le=90)):
    """Get aggregated health summary."""
    try:
        health_summary = DatabaseManager.get_health_summary(days=days)
        sleep_summary = DatabaseManager.get_sleep_summary(days=days)
        
        return HealthSummary(
            avg_steps=health_summary.get("avg_steps", 0),
            total_steps=health_summary.get("total_steps", 0),
            avg_resting_hr=health_summary.get("avg_resting_hr"),
            avg_stress=health_summary.get("avg_stress"),
            total_active_minutes=health_summary.get("total_active_minutes", 0),
            total_calories=health_summary.get("total_calories", 0),
            avg_sleep_hours=sleep_summary.get("avg_sleep_hours", 0),
            avg_sleep_score=sleep_summary.get("avg_sleep_score")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sleep")
async def get_sleep_data(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: int = Query(default=14, le=90)
):
    """Get sleep data."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not start_date:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        
        sleep_list = garmin.get_sleep_range(start_date, end_date)
        
        # Process into cleaner format
        processed = []
        for sleep in sleep_list:
            daily = sleep.get("dailySleepDTO", {})
            scores = sleep.get("sleepScores", {})
            
            total_seconds = daily.get("sleepTimeSeconds", 0) or 0
            
            processed.append({
                "date": sleep.get("date"),
                "total_hours": total_seconds / 3600,
                "deep_hours": (daily.get("deepSleepSeconds", 0) or 0) / 3600,
                "light_hours": (daily.get("lightSleepSeconds", 0) or 0) / 3600,
                "rem_hours": (daily.get("remSleepSeconds", 0) or 0) / 3600,
                "awake_hours": (daily.get("awakeSleepSeconds", 0) or 0) / 3600,
                "sleep_score": scores.get("overall", {}).get("value"),
                "avg_hr": daily.get("averageHeartRate"),
                "hrv": daily.get("averageHRV"),
            })
        
        return {"sleep": processed, "total": len(processed)}
        
    except DataFetchError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heart-rate/{hr_date}")
async def get_heart_rate(hr_date: date):
    """Get heart rate data for a specific date."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        hr_data = garmin.get_heart_rates(hr_date)
        return hr_data
        
    except DataFetchError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stress/{stress_date}")
async def get_stress(stress_date: date):
    """Get stress data for a specific date."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        stress_data = garmin.get_stress_data(stress_date)
        return stress_data
        
    except Exception as e:
        return {}


@router.get("/stress/{stress_date}/all-day")
async def get_all_day_stress(stress_date: date):
    """Get all-day stress data with timeline for a specific date.
    
    Returns detailed stress values throughout the day including:
    - Stress timeline values
    - Rest stress
    - Activity stress
    - Low, medium, high stress periods
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        stress_data = garmin.get_all_day_stress(stress_date)
        return stress_data
        
    except Exception as e:
        return {}


@router.get("/body-battery")
async def get_body_battery(bb_date: Optional[date] = None):
    """Get body battery data."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        target_date = bb_date or date.today()
        stats = garmin.get_stats(target_date)
        
        return {
            "date": target_date.isoformat(),
            "body_battery_high": stats.get("bodyBatteryMostRecentValue") or stats.get("bodyBatteryHighestValue"),
            "body_battery_low": stats.get("bodyBatteryLowestValue"),
            "body_battery_charged": stats.get("bodyBatteryChargedValue"),
            "body_battery_drained": stats.get("bodyBatteryDrainedValue"),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/training-readiness")
async def get_training_readiness(tr_date: Optional[date] = None):
    """Get training readiness data."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        target_date = tr_date or date.today()
        readiness = garmin.get_training_readiness(target_date)
        return readiness
    except Exception as e:
        return {}


@router.get("/full-snapshot")
async def get_full_health_snapshot(snapshot_date: Optional[date] = None):
    """
    Get a complete health snapshot including all available metrics.
    Useful for dashboard and AI analysis.
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_full_health_snapshot(snapshot_date)
    except Exception as e:
        return {"error": str(e)}


@router.get("/performance-metrics")
async def get_performance_metrics():
    """
    Get all performance-related metrics including:
    - Race predictions (5K, 10K, Half, Marathon)
    - VO2max
    - Endurance score
    - Hill score
    - Fitness age
    - Lactate threshold
    - Personal records
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_performance_metrics()
    except Exception as e:
        return {"error": str(e)}


@router.get("/body-battery/detailed")
async def get_body_battery_detailed(bb_date: Optional[date] = None):
    """Get detailed body battery data including timeline and events."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        target_date = bb_date or date.today()
        return garmin.get_body_battery_detailed(target_date)
    except Exception as e:
        return {"error": str(e)}


@router.get("/respiration/{resp_date}")
async def get_respiration(resp_date: date):
    """Get respiration rate data."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_respiration_data(resp_date)
    except Exception as e:
        return {}


@router.get("/spo2/{spo2_date}")
async def get_spo2(spo2_date: date):
    """Get SpO2 (blood oxygen) data."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_spo2_data(spo2_date)
    except Exception as e:
        return {}


@router.get("/hydration/{hydration_date}")
async def get_hydration(hydration_date: date):
    """Get hydration data."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_hydration_data(hydration_date)
    except Exception as e:
        return {}


@router.get("/intensity-minutes")
async def get_intensity_minutes(weeks: int = Query(default=4, le=52)):
    """Get weekly intensity minutes for trend analysis."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_weekly_intensity_minutes(weeks)
    except Exception as e:
        return []


@router.get("/hrv/{hrv_date}")
async def get_hrv(hrv_date: date):
    """Get HRV (Heart Rate Variability) data."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_hrv_data(hrv_date)
    except Exception as e:
        return {}


@router.get("/devices")
async def get_devices():
    """Get list of Garmin devices."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        devices = garmin.get_devices()
        primary = garmin.get_primary_training_device()
        
        return {
            "devices": devices,
            "primary_device": primary
        }
    except Exception as e:
        return {"devices": [], "primary_device": None}


@router.get("/goals")
async def get_garmin_goals():
    """Get fitness goals from Garmin."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_goals()
    except Exception as e:
        return {}


@router.get("/badges")
async def get_badges():
    """Get earned badges."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_earned_badges()
    except Exception as e:
        return []


@router.get("/personal-records")
async def get_personal_records():
    """Get personal records."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return garmin.get_personal_records()
    except Exception as e:
        return {}


# ==================== Sync Endpoints ====================

@router.get("/sync/status")
async def get_sync_status():
    """Get sync status for all data types."""
    try:
        sync_status = DatabaseManager.get_all_sync_status()
        
        # Add default statuses if not present
        data_types = ["activities", "health_stats", "sleep", "body_battery"]
        for dt in data_types:
            if dt not in sync_status:
                sync_status[dt] = {
                    "last_sync_at": None,
                    "last_sync_success": False,
                    "records_synced": 0,
                    "is_stale": True,
                }
        
        return {
            "sync_status": sync_status,
            "server_time": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_all_data():
    """
    Sync all data from Garmin to local database.
    This is a manual sync that fetches fresh data regardless of cache age.
    """
    import time
    start_time = time.time()
    
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        results = {
            "activities": {"success": False, "count": 0, "error": None},
            "health_stats": {"success": False, "count": 0, "error": None},
            "sleep": {"success": False, "count": 0, "error": None},
            "body_battery": {"success": False, "count": 0, "error": None},
        }
        
        today = date.today()
        sync_days = 14  # Sync last 14 days
        
        # Sync activities
        try:
            activities = garmin.get_activities(limit=50)
            for act in activities:
                if isinstance(act, dict):
                    DatabaseManager.save_activity(act)
            results["activities"]["success"] = True
            results["activities"]["count"] = len(activities) if isinstance(activities, list) else 0
            DatabaseManager.update_sync_status(
                "activities", True, results["activities"]["count"], 
                time.time() - start_time
            )
        except Exception as e:
            results["activities"]["error"] = str(e)
            DatabaseManager.update_sync_status("activities", False, 0, 0, str(e))
        
        # Sync health stats
        try:
            stats_count = 0
            for i in range(sync_days):
                stat_date = today - timedelta(days=i)
                try:
                    stats = garmin.get_stats(stat_date)
                    if stats:
                        DatabaseManager.save_health_stats(stat_date, stats)
                        stats_count += 1
                except Exception:
                    pass
            results["health_stats"]["success"] = True
            results["health_stats"]["count"] = stats_count
            DatabaseManager.update_sync_status(
                "health_stats", True, stats_count, 
                time.time() - start_time
            )
        except Exception as e:
            results["health_stats"]["error"] = str(e)
            DatabaseManager.update_sync_status("health_stats", False, 0, 0, str(e))
        
        # Sync sleep data
        try:
            sleep_count = 0
            for i in range(sync_days):
                sleep_date = today - timedelta(days=i)
                try:
                    sleep = garmin.get_sleep_data(sleep_date)
                    if sleep:
                        DatabaseManager.save_sleep_data(sleep_date, sleep)
                        sleep_count += 1
                except Exception:
                    pass
            results["sleep"]["success"] = True
            results["sleep"]["count"] = sleep_count
            DatabaseManager.update_sync_status(
                "sleep", True, sleep_count, 
                time.time() - start_time
            )
        except Exception as e:
            results["sleep"]["error"] = str(e)
            DatabaseManager.update_sync_status("sleep", False, 0, 0, str(e))
        
        # Sync body battery
        try:
            bb = garmin.get_body_battery_detailed(today)
            if bb:
                results["body_battery"]["success"] = True
                results["body_battery"]["count"] = 1
            DatabaseManager.update_sync_status(
                "body_battery", True, 1, 
                time.time() - start_time
            )
        except Exception as e:
            results["body_battery"]["error"] = str(e)
            DatabaseManager.update_sync_status("body_battery", False, 0, 0, str(e))
        
        total_time = time.time() - start_time
        
        return {
            "success": True,
            "results": results,
            "total_time_seconds": round(total_time, 2),
            "synced_at": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
