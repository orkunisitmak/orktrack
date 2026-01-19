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
