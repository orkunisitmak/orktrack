"""AI API Router with Structured Prompts."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .auth import get_garmin_service
from services.ai_service import AIService
from database import DatabaseManager
from backend.prompts import PromptEngine

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    include_context: bool = True


class ChatResponse(BaseModel):
    response: str
    session_id: str


class WorkoutRequest(BaseModel):
    scheduled_type: str  # "VO2Max Intervals", "Long Run", "Recovery", etc.
    vdot_score: Optional[float] = None
    training_phase: str = "Base Building"
    primary_goal: str = "General Fitness"
    user_rpe: int = 5  # Subjective soreness 1-10


class WeekPlanRequest(BaseModel):
    primary_goal: str = "General Fitness"
    training_phase: Optional[str] = None  # Auto-detected if not provided
    supplementary_activities: Optional[List[str]] = None  # wim_hof, mobility, yoga, cold_plunge, gym
    supplementary_frequency: Optional[Dict[str, int]] = None  # e.g., {"wim_hof": 7, "yoga": 3}
    goal_time: Optional[str] = None  # Target race time, e.g., "45:00" for 10K
    goal_distance_km: Optional[float] = None  # Race distance in km
    target_vdot: Optional[int] = None  # Pre-calculated VDOT from frontend


class MonthPlanRequest(BaseModel):
    primary_goal: str = "General Fitness"
    training_phase: str = "Base Building"
    target_race_date: Optional[str] = None  # YYYY-MM-DD format
    supplementary_activities: Optional[List[str]] = None  # wim_hof, mobility, yoga, cold_plunge, gym
    supplementary_frequency: Optional[Dict[str, int]] = None  # e.g., {"wim_hof": 7, "yoga": 3}
    goal_time: Optional[str] = None  # Target race time
    goal_distance_km: Optional[float] = None  # Race distance in km
    target_vdot: Optional[int] = None  # Pre-calculated VDOT from frontend


class PinPlanRequest(BaseModel):
    plan_type: str = "week"  # "week" or "month"
    plan_data: Dict[str, Any]
    start_date: Optional[str] = None  # YYYY-MM-DD, defaults to today


class MatchActivityRequest(BaseModel):
    scheduled_workout_id: int
    activity_id: str  # Garmin activity ID


class InsightRequest(BaseModel):
    period: str = "week"  # "day", "week" or "month"
    focus_areas: Optional[List[str]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """AI chat with full fitness context including detailed activity data."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured. Please add GEMINI_API_KEY to .env file.")
        
        # Build context if authenticated
        user_data = {}
        recent_activities = []
        health_summary = {}
        monthly_activities = []
        
        if garmin.is_authenticated and request.include_context:
            user_data = garmin.user_profile or {}
            
            # Get more activities for better context (last 50 activities)
            try:
                recent_activities = garmin.get_activities(limit=50)
                if isinstance(recent_activities, list):
                    # Ensure all items are dicts
                    recent_activities = [a for a in recent_activities if isinstance(a, dict)]
            except Exception as e:
                print(f"Error fetching activities: {e}")
                recent_activities = []
            
            # Also get activities for current month specifically
            try:
                today = date.today()
                month_start = today.replace(day=1)
                monthly_activities = garmin.get_activities_by_date(
                    start_date=month_start,
                    end_date=today
                )
                if isinstance(monthly_activities, list):
                    monthly_activities = [a for a in monthly_activities if isinstance(a, dict)]
            except Exception as e:
                print(f"Error fetching monthly activities: {e}")
                monthly_activities = []
            
            # Merge and deduplicate activities
            all_activities = recent_activities.copy()
            seen_ids = {a.get('activityId') for a in all_activities if a.get('activityId')}
            for act in monthly_activities:
                if act.get('activityId') not in seen_ids:
                    all_activities.append(act)
                    seen_ids.add(act.get('activityId'))
            
            recent_activities = all_activities
            
            # Get comprehensive health metrics
            try:
                health_summary = garmin.get_health_metrics_for_ai(days=30)
            except Exception as e:
                print(f"Error fetching health metrics: {e}")
                health_summary = {}
        
        # Use enhanced PromptEngine for chat
        prompt = PromptEngine.build_chat_context_prompt(
            user_profile=user_data,
            health_summary=health_summary,
            recent_activities=recent_activities,
            user_query=request.message
        )
        
        # Generate response using the model directly with the enhanced prompt
        try:
            response = ai_service.model.generate_content(prompt)
            response_text = response.text
        except Exception as e:
            # Fallback to standard chat method
            response_text = ai_service.chat(
                user_query=request.message,
                user_data=user_data,
                recent_activities=recent_activities,
                health_summary=health_summary,
                session_id=request.session_id
            )
        
        session_id = request.session_id or str(datetime.now().timestamp())
        
        return ChatResponse(
            response=response_text,
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming AI chat response with full context."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured")
        
        # Build context
        user_data = garmin.user_profile or {} if garmin.is_authenticated else {}
        recent_activities = []
        health_summary = {}
        
        if garmin.is_authenticated and request.include_context:
            try:
                recent_activities = garmin.get_activities(limit=15)
            except Exception:
                pass
            
            try:
                health_summary = garmin.get_health_metrics_for_ai(days=7)
            except Exception:
                pass
        
        # Use enhanced prompt
        prompt = PromptEngine.build_chat_context_prompt(
            user_profile=user_data,
            health_summary=health_summary,
            recent_activities=recent_activities,
            user_query=request.message
        )
        
        async def generate():
            try:
                response = ai_service.model.generate_content(prompt, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'text': f'Error: {str(e)}'})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-workout")
async def generate_workout(request: WorkoutRequest):
    """Generate AI workout using Physiological Engine approach."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured")
        
        # Get current health telemetry
        today = date.today()
        
        today_stats = {}
        try:
            today_stats = garmin.get_stats(today)
        except Exception as e:
            print(f"Error getting stats: {e}")
        
        sleep_data = {}
        try:
            sleep_data = garmin.get_sleep_data(today)
        except Exception as e:
            print(f"Error getting sleep: {e}")
        
        training_readiness = {}
        try:
            training_readiness = garmin.get_training_readiness(today)
        except Exception as e:
            print(f"Error getting training readiness: {e}")
        
        # Get activity history for load calculation
        recent_activities = []
        try:
            recent_activities = garmin.get_activities(limit=14)
        except Exception as e:
            print(f"Error getting activities: {e}")
        
        # Build structured prompt using PromptEngine
        prompt = PromptEngine.build_workout_prompt(
            user_profile=garmin.user_profile or {},
            vdot_score=request.vdot_score or 45,  # Default VDOT
            primary_goal=request.primary_goal,
            training_phase=request.training_phase,
            scheduled_workout_type=request.scheduled_type,
            health_telemetry={
                "body_battery": today_stats.get("bodyBatteryMostRecentValue", 50),
                "sleep_score": sleep_data.get("sleepScores", {}).get("overall", {}).get("value", 70) if isinstance(sleep_data.get("sleepScores"), dict) else 70,
                "deep_sleep_mins": (sleep_data.get("dailySleepDTO", {}).get("deepSleepSeconds", 0) or 0) // 60 if isinstance(sleep_data.get("dailySleepDTO"), dict) else 0,
                "hrv_status": training_readiness.get("hrvStatus", "Balanced") if training_readiness else "Balanced",
                "resting_hr": today_stats.get("restingHeartRate", 60),
                "resting_hr_avg": 60,
                "user_rpe": request.user_rpe,
            },
            activity_history={
                "acute_load": sum(a.get("aerobicTrainingEffect", 0) or a.get("trainingEffectAerobic", 0) or 0 for a in recent_activities[:7]),
                "chronic_load": sum(a.get("aerobicTrainingEffect", 0) or a.get("trainingEffectAerobic", 0) or 0 for a in recent_activities) / 2 if recent_activities else 0,
                "yesterday_te_aerobic": recent_activities[0].get("aerobicTrainingEffect", 0) or recent_activities[0].get("trainingEffectAerobic", 0) if recent_activities else 0,
                "yesterday_te_anaerobic": recent_activities[0].get("anaerobicTrainingEffect", 0) or recent_activities[0].get("trainingEffectAnaerobic", 0) if recent_activities else 0,
            }
        )
        
        # Generate workout using AI
        response = ai_service.model.generate_content(prompt)
        
        # Parse JSON response
        workout_data = ai_service._extract_json(response.text)
        
        if workout_data:
            workout_data["generated_at"] = datetime.now().isoformat()
            workout_data["ai_model"] = ai_service.model_name
            return workout_data
        else:
            return {
                "error": "Failed to parse workout",
                "raw_response": response.text
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Workout generation error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-week-plan")
async def generate_week_plan(request: WeekPlanRequest):
    """Generate a full week training plan based on health and activity data."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured")
        
        # Get current health data
        today = date.today()
        
        # Get stats
        today_stats = {}
        try:
            today_stats = garmin.get_stats(today)
            if not isinstance(today_stats, dict):
                today_stats = {}
        except Exception:
            pass
        
        # Get sleep data
        sleep_data = {}
        try:
            sleep_data = garmin.get_sleep_data(today)
            if not isinstance(sleep_data, dict):
                sleep_data = {}
        except Exception:
            pass
        
        # Get training readiness
        training_readiness = {}
        try:
            training_readiness = garmin.get_training_readiness(today)
            if not isinstance(training_readiness, dict):
                training_readiness = {}
        except Exception:
            pass
        
        # Get recent activities (2 weeks) for analysis
        recent_activities = []
        try:
            activities_result = garmin.get_activities(limit=20)
            if isinstance(activities_result, list):
                recent_activities = activities_result
            elif isinstance(activities_result, dict) and 'activities' in activities_result:
                recent_activities = activities_result['activities']
        except Exception:
            pass
        
        # Ensure each activity is a dict
        recent_activities = [a for a in recent_activities if isinstance(a, dict)]
        
        # Get health metrics
        health_metrics = {}
        try:
            health_metrics = garmin.get_health_metrics_for_ai(days=7)
            if not isinstance(health_metrics, dict):
                health_metrics = {}
        except Exception:
            pass
        
        # Use target VDOT from goal time if provided, otherwise estimate from activities
        if request.target_vdot:
            estimated_vdot = request.target_vdot
        else:
            estimated_vdot = _estimate_vdot_from_activities(recent_activities)
        
        # Auto-calculate readiness score with safe defaults
        body_battery = today_stats.get("bodyBatteryMostRecentValue") or 70
        avg_sleep = health_metrics.get("avg_sleep_hours") or 7
        avg_stress = health_metrics.get("avg_stress") or 40
        resting_hr = today_stats.get("restingHeartRate") or 60
        
        # Ensure numeric values
        try:
            body_battery = float(body_battery)
            avg_sleep = float(avg_sleep)
            avg_stress = float(avg_stress)
        except (ValueError, TypeError):
            body_battery = 70
            avg_sleep = 7
            avg_stress = 40
        
        # Calculate overall readiness (0-100)
        readiness_score = min(100, (body_battery * 0.4 + (100 - avg_stress) * 0.3 + min(avg_sleep / 8 * 100, 100) * 0.3))
        
        # Determine training phase based on activity patterns
        training_phase = _determine_training_phase(recent_activities)
        
        # Calculate weekly volume
        weekly_volume = _calculate_weekly_volume(recent_activities)
        
        # Count running activities safely
        running_count = 0
        for a in recent_activities:
            try:
                if a.get("activityType", {}).get("typeKey") == "running":
                    running_count += 1
            except Exception:
                pass
        
        # Get TODAY's readiness for autoregulation (daily, not weekly)
        today_readiness = {}
        try:
            today_readiness = garmin.get_today_readiness()
            if not isinstance(today_readiness, dict):
                today_readiness = {}
        except Exception:
            today_readiness = {
                "body_battery": body_battery,
                "sleep_score": None,
                "hrv_status": "Unknown",
                "resting_hr": resting_hr,
                "readiness_score": readiness_score,
                "should_rest": False,
                "should_reduce_intensity": False,
            }
        
        # Get HR zones for specific BPM targets
        hr_zones = {}
        try:
            hr_zones = garmin.get_hr_zones()
            if not isinstance(hr_zones, dict):
                hr_zones = {}
        except Exception:
            pass
        
        # Use provided training phase or auto-detect
        phase = request.training_phase if request.training_phase else training_phase
        
        # Build the week plan prompt with today's readiness (for daily autoregulation)
        prompt = PromptEngine.build_week_plan_prompt(
            user_profile=garmin.user_profile or {},
            primary_goal=request.primary_goal,
            estimated_vdot=estimated_vdot,
            training_phase=phase,
            health_metrics={
                "body_battery": body_battery,
                "avg_sleep_hours": avg_sleep,
                "avg_stress": avg_stress,
                "resting_hr": resting_hr,
                "readiness_score": readiness_score,
                "hrv_status": training_readiness.get("hrvStatus", "Balanced") if isinstance(training_readiness, dict) else "Balanced",
            },
            recent_activities=recent_activities[:10],
            activity_summary={
                "total_activities": len(recent_activities),
                "running_count": running_count,
                "avg_weekly_volume": weekly_volume,
            },
            today_readiness=today_readiness,
            hr_zones=hr_zones,
            supplementary_activities=request.supplementary_activities,
            supplementary_frequency=request.supplementary_frequency,
            goal_time=request.goal_time,
            goal_distance_km=request.goal_distance_km,
        )
        
        # Generate week plan
        response = ai_service.model.generate_content(prompt)
        plan_data = ai_service._extract_json(response.text)
        
        if plan_data:
            plan_data["generated_at"] = datetime.now().isoformat()
            plan_data["ai_model"] = ai_service.model_name
            plan_data["estimated_vdot"] = estimated_vdot
            plan_data["readiness_score"] = readiness_score
            if request.goal_time:
                plan_data["goal_time"] = request.goal_time
                plan_data["goal_distance_km"] = request.goal_distance_km
            return plan_data
        else:
            return {
                "error": "Failed to parse week plan",
                "raw_response": response.text
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Week plan generation error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


def _estimate_vdot_from_activities(activities: List[Dict]) -> float:
    """Estimate VDOT from recent running activities."""
    running_paces = []
    
    for activity in activities:
        if activity.get("activityType", {}).get("typeKey") != "running":
            continue
        
        distance_m = activity.get("distance", 0) or 0
        duration_s = activity.get("duration", 0) or 0
        
        if distance_m > 1000 and duration_s > 300:  # At least 1km and 5 min
            pace_min_per_km = (duration_s / 60) / (distance_m / 1000)
            # Only consider reasonable paces (3-10 min/km)
            if 3 < pace_min_per_km < 10:
                running_paces.append(pace_min_per_km)
    
    if not running_paces:
        return 40  # Default for beginners
    
    # Use the fastest sustainable pace (median of faster half)
    sorted_paces = sorted(running_paces)
    fast_paces = sorted_paces[:max(1, len(sorted_paces) // 2)]
    avg_fast_pace = sum(fast_paces) / len(fast_paces)
    
    # Convert pace to estimated VDOT (simplified formula)
    # Based on Jack Daniels tables approximation
    if avg_fast_pace < 3.5:
        return 70  # Elite
    elif avg_fast_pace < 4.0:
        return 60
    elif avg_fast_pace < 4.5:
        return 55
    elif avg_fast_pace < 5.0:
        return 50
    elif avg_fast_pace < 5.5:
        return 45
    elif avg_fast_pace < 6.0:
        return 42
    elif avg_fast_pace < 6.5:
        return 38
    elif avg_fast_pace < 7.0:
        return 35
    else:
        return 32


def _determine_training_phase(activities: List[Dict]) -> str:
    """Determine training phase from activity patterns."""
    if not activities:
        return "Base Building"
    
    # Check recent activity intensity
    high_intensity_count = 0
    long_run_count = 0
    
    for activity in activities[:14]:  # Last 2 weeks
        duration_min = (activity.get("duration", 0) or 0) / 60
        te_aerobic = activity.get("aerobicTrainingEffect") or activity.get("trainingEffectAerobic") or 0
        te_anaerobic = activity.get("anaerobicTrainingEffect") or activity.get("trainingEffectAnaerobic") or 0
        
        if te_anaerobic > 2.5 or te_aerobic > 4.0:
            high_intensity_count += 1
        if duration_min > 60:
            long_run_count += 1
    
    # Determine phase
    if high_intensity_count >= 4:
        return "Peak Phase"
    elif high_intensity_count >= 2 and long_run_count >= 2:
        return "Build Phase"
    elif long_run_count >= 3:
        return "Specific Prep"
    else:
        return "Base Building"


def _calculate_weekly_volume(activities: List[Dict]) -> Dict[str, float]:
    """Calculate average weekly training volume."""
    total_duration = 0
    total_distance = 0
    
    # Sum last 7 days
    for activity in activities[:7]:
        total_duration += (activity.get("duration", 0) or 0) / 60  # minutes
        total_distance += (activity.get("distance", 0) or 0) / 1000  # km
    
    return {
        "duration_minutes": total_duration,
        "distance_km": total_distance
    }


@router.post("/generate-insights")
async def generate_insights(request: InsightRequest):
    """Generate comprehensive AI health insights using all available data."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated. Please login first.")
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured. Please add GEMINI_API_KEY to .env file.")
        
        days = 1 if request.period == "day" else (7 if request.period == "week" else 30)
        
        # Get comprehensive data with all new metrics
        raw_data = {}
        try:
            raw_data = garmin.get_comprehensive_data(days=days)
        except Exception as e:
            print(f"Error getting comprehensive data: {e}")
            raw_data = {
                "health_summary": garmin.get_health_metrics_for_ai(days=days),
                "sleep_data": [],
                "activities": [],
                "body_battery": [],
                "hrv_data": [],
                "performance_metrics": {},
                "today_readiness": {},
                "personal_records": {},
                "intensity_minutes": {},
                "hr_zones": {}
            }
        
        # Build structured prompt with all comprehensive data
        prompt = PromptEngine.build_insights_prompt(
            user_profile=garmin.user_profile or {},
            health_data=raw_data.get("health_summary", {}),
            sleep_data=raw_data.get("sleep_data", []),
            activities=raw_data.get("activities", []),
            period=request.period,
            focus_areas=request.focus_areas,
            # Pass all new comprehensive data
            body_battery=raw_data.get("body_battery", []),
            hrv_data=raw_data.get("hrv_data", []),
            performance_metrics=raw_data.get("performance_metrics", {}),
            today_readiness=raw_data.get("today_readiness", {}),
            personal_records=raw_data.get("personal_records", {}),
            intensity_minutes=raw_data.get("intensity_minutes", {}),
            hr_zones=raw_data.get("hr_zones", {})
        )
        
        # Generate insights
        response = ai_service.model.generate_content(prompt)
        insights_data = ai_service._extract_json(response.text)
        
        if insights_data:
            insights_data["generated_at"] = datetime.now().isoformat()
            insights_data["period"] = request.period
            # Add raw data summary for frontend display
            insights_data["data_sources"] = {
                "sleep_nights": len(raw_data.get("sleep_data", [])),
                "activities_count": len(raw_data.get("activities", [])),
                "body_battery_days": len(raw_data.get("body_battery", [])),
                "hrv_days": len(raw_data.get("hrv_data", [])),
                "has_performance_metrics": bool(raw_data.get("performance_metrics")),
            }
            return insights_data
        else:
            # Return a structured fallback response
            return {
                "overall_score": 70,
                "overall_assessment": "Analysis generated but couldn't parse structured response.",
                "raw_response": response.text,
                "highlights": [],
                "sleep_analysis": {"quality_rating": "Unknown", "insights": [], "recommendations": []},
                "activity_analysis": {"consistency_rating": "Unknown", "insights": [], "recommendations": []},
                "recovery_analysis": {"status": "Unknown", "insights": [], "recommendations": []},
                "performance_analysis": {"vo2_max": None, "fitness_age": None, "insights": [], "recommendations": []},
                "stress_analysis": {"avg_stress_level": None, "insights": [], "recommendations": []},
                "weekly_focus": "Continue your current routine",
                "action_plan": [],
                "motivational_message": "Keep up the great work!",
                "generated_at": datetime.now().isoformat(),
                "period": request.period
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Insights generation error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend-goals")
async def recommend_goals():
    """Get AI-recommended fitness goals."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured")
        
        # Get current metrics
        health_metrics = {}
        try:
            health_metrics = garmin.get_health_metrics_for_ai(days=30)
        except Exception:
            pass
        
        activities = []
        try:
            activities = garmin.get_activities(limit=30)
        except Exception:
            pass
        
        recommendations = ai_service.recommend_goals(
            current_metrics=health_metrics,
            activity_history=activities
        )
        
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Goal recommendation error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity/{activity_id}/analysis")
async def analyze_activity(
    activity_id: str,
    regenerate: bool = Query(default=False, description="Force regeneration of analysis")
):
    """Get comprehensive AI analysis of a specific activity with comparisons.
    
    - Returns cached analysis if available
    - Set regenerate=True to force new analysis generation
    - Uses comprehensive metrics including stress, respiration, performance condition
    """
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured")
        
        # Check for cached analysis if not regenerating
        if not regenerate:
            cached_analysis = DatabaseManager.get_activity_analysis(activity_id)
            if cached_analysis:
                return {
                    "activity_id": activity_id,
                    "analysis": cached_analysis.analysis_data,
                    "activity_summary": cached_analysis.activity_summary,
                    "comparison_activities_count": cached_analysis.comparison_activities_count,
                    "has_splits": cached_analysis.activity_summary.get("has_splits", False) if cached_analysis.activity_summary else False,
                    "has_weather": cached_analysis.activity_summary.get("has_weather", False) if cached_analysis.activity_summary else False,
                    "cached": True,
                    "cached_at": cached_analysis.created_at.isoformat() if cached_analysis.created_at else None,
                }
        
        # Get comprehensive activity details using the new method
        try:
            full_data = garmin.get_comprehensive_activity_data(activity_id)
            raw_activity = full_data.get("activity", {})
            
            # Debug: log what we got
            print(f"[Activity Analysis] Full data keys: {list(full_data.keys())}")
            print(f"[Activity Analysis] Raw activity keys: {list(raw_activity.keys()) if raw_activity else 'None'}")
            
            # The Garmin API returns detailed activity data with nested DTOs
            # We need to flatten the data structure for our analysis
            summary_dto = raw_activity.get("summaryDTO", {}) or {}
            activity_type_dto = raw_activity.get("activityTypeDTO", {}) or {}
            
            # Debug: log the summary DTO
            print(f"[Activity Analysis] Summary DTO keys: {list(summary_dto.keys()) if summary_dto else 'None'}")
            
            # Build a flat activity object with the data we need
            activity = {
                "activityId": raw_activity.get("activityId"),
                "activityName": raw_activity.get("activityName", ""),
                "activityType": activity_type_dto,  # Keep the DTO structure
                # Extract metrics from summaryDTO
                "duration": summary_dto.get("duration") or summary_dto.get("elapsedDuration") or summary_dto.get("movingDuration"),
                "distance": summary_dto.get("distance"),
                "averageHR": summary_dto.get("averageHR") or summary_dto.get("averageHeartRate"),
                "maxHR": summary_dto.get("maxHR") or summary_dto.get("maxHeartRate"),
                "calories": summary_dto.get("calories") or summary_dto.get("activeKilocalories"),
                "averageSpeed": summary_dto.get("averageSpeed"),
                "maxSpeed": summary_dto.get("maxSpeed"),
                "averageRunningCadenceInStepsPerMinute": summary_dto.get("averageRunningCadenceInStepsPerMinute"),
                "elevationGain": summary_dto.get("elevationGain"),
                "elevationLoss": summary_dto.get("elevationLoss"),
                "aerobicTrainingEffect": summary_dto.get("aerobicTrainingEffect") or summary_dto.get("trainingEffect"),
                "anaerobicTrainingEffect": summary_dto.get("anaerobicTrainingEffect"),
                "avgStrideLength": summary_dto.get("avgStrideLength"),
                "avgStressLevel": summary_dto.get("avgStressLevel"),
                "maxStressLevel": summary_dto.get("maxStressLevel"),
                "avgRespirationRate": summary_dto.get("avgRespirationRate"),
                "maxRespirationRate": summary_dto.get("maxRespirationRate"),
                # Keep the start time
                "startTimeLocal": summary_dto.get("startTimeLocal") or raw_activity.get("startTimeLocal"),
                "startTimeGMT": summary_dto.get("startTimeGMT") or raw_activity.get("startTimeGMT"),
            }
            
            activity_details = {
                "splits": full_data.get("splits"),
                "hr_zones": full_data.get("hr_zones"),
                "weather": full_data.get("weather"),
                "typed_splits": full_data.get("typed_splits"),
                "split_summaries": full_data.get("split_summaries"),
            }
            
        except Exception as e:
            print(f"Error getting comprehensive data, falling back to basic: {e}")
            import traceback
            traceback.print_exc()
            activity = garmin.get_activity_details(activity_id)
            activity_details = {}
        
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        # Get the activity name first
        activity_name = activity.get("activityName", "") or ""
        
        # Determine the actual activity type - use classifiedType if available, otherwise from Garmin
        raw_activity_type = activity.get("activityType", {})
        if isinstance(raw_activity_type, dict):
            activity_type = raw_activity_type.get("typeKey", "other")
            # Also get the display name for better context
            activity_type_name = raw_activity_type.get("typeKey", activity_type)
        else:
            activity_type = str(raw_activity_type) if raw_activity_type else "other"
            activity_type_name = activity_type
        
        # Use classified type if different (our better detection)
        classified_type = activity.get("classifiedType")
        if classified_type and classified_type != "other":
            activity_type = classified_type
        
        # If type is still "other" but we have a descriptive name, try to classify it
        if activity_type == "other" and activity_name:
            name_lower = activity_name.lower()
            if any(kw in name_lower for kw in ['yoga', 'stretch', 'pilates']):
                activity_type = "yoga"
            elif any(kw in name_lower for kw in ['cold plunge', 'ice bath', 'cold']):
                activity_type = "cold_plunge"
            elif any(kw in name_lower for kw in ['sauna', 'steam']):
                activity_type = "sauna"
            elif any(kw in name_lower for kw in ['breath', 'wim hof', 'meditation']):
                activity_type = "breathing"
        
        # Debug logging - more detailed
        print(f"[Activity Analysis] ====== ACTIVITY DATA ======")
        print(f"[Activity Analysis] Activity ID: {activity_id}")
        print(f"[Activity Analysis] Activity Name: '{activity_name}'")
        print(f"[Activity Analysis] Activity Type: {activity_type} (raw: {raw_activity_type})")
        print(f"[Activity Analysis] Duration: {(activity.get('duration', 0) or 0) / 60:.1f} min (raw: {activity.get('duration')})")
        print(f"[Activity Analysis] Distance: {(activity.get('distance', 0) or 0) / 1000:.2f} km")
        print(f"[Activity Analysis] Avg HR: {activity.get('averageHR', 'N/A')}")
        print(f"[Activity Analysis] Max HR: {activity.get('maxHR', 'N/A')}")
        print(f"[Activity Analysis] Calories: {activity.get('calories', 'N/A')}")
        print(f"[Activity Analysis] Aerobic TE: {activity.get('aerobicTrainingEffect', activity.get('trainingEffectAerobic', 'N/A'))}")
        print(f"[Activity Analysis] =============================")
        
        # Get similar activities for comparison (same type, recent) with their comprehensive data
        similar_activities = []
        similar_activities_detailed = []
        
        try:
            # Get recent activities of same type
            recent_activities = garmin.get_activities(limit=50)
            if isinstance(recent_activities, list):
                for act in recent_activities:
                    if not isinstance(act, dict):
                        continue
                    
                    act_type_raw = act.get("activityType", {})
                    if isinstance(act_type_raw, dict):
                        act_type = act_type_raw.get("typeKey", "other")
                    else:
                        act_type = str(act_type_raw) if act_type_raw else "other"
                    
                    # Use classified type if available
                    act_classified = act.get("classifiedType")
                    if act_classified and act_classified != "other":
                        act_type = act_classified
                    
                    # Same type and not the current activity
                    if act_type == activity_type and str(act.get("activityId")) != str(activity_id):
                        similar_activities.append(act)
                        
                        # Get detailed metrics for comparison
                        act_summary = {
                            "name": act.get("activityName"),
                            "date": act.get("startTimeLocal"),
                            "duration_minutes": (act.get("duration", 0) or 0) / 60,
                            "distance_km": (act.get("distance", 0) or 0) / 1000,
                            "avg_hr": act.get("averageHR"),
                            "max_hr": act.get("maxHR"),
                            "training_effect": act.get("aerobicTrainingEffect") or act.get("trainingEffectAerobic"),
                            "avg_pace": None,
                        }
                        
                        # Calculate pace for running
                        if act_summary["distance_km"] and act_summary["distance_km"] > 0 and act_summary["duration_minutes"]:
                            pace = act_summary["duration_minutes"] / act_summary["distance_km"]
                            pace_min = int(pace)
                            pace_sec = int((pace - pace_min) * 60)
                            act_summary["avg_pace"] = f"{pace_min}:{pace_sec:02d}/km"
                        
                        similar_activities_detailed.append(act_summary)
                        
                        if len(similar_activities) >= 10:  # Increased for better comparison
                            break
        except Exception as e:
            print(f"Error getting similar activities: {e}")
        
        # Log similar activities found
        print(f"[Activity Analysis] Found {len(similar_activities)} similar activities of type '{activity_type}'")
        
        # Get user's HR zones
        user_hr_zones = {}
        try:
            user_hr_zones = garmin.get_hr_zones()
        except Exception as e:
            print(f"Error getting user HR zones: {e}")
        
        # Debug: Log activity details for detection
        activity_name = activity.get("activityName", "Unknown")
        activity_type_key = activity.get("activityType", {}).get("typeKey", "unknown")
        print(f"[Activity Analysis] Activity: '{activity_name}', Type: '{activity_type_key}'")
        
        # Check if recovery activity for logging
        combined_lower = f"{activity_name.lower()} {activity_type_key.lower()}"
        recovery_keywords = ['cold', 'plunge', 'ice', 'sauna', 'yoga', 'stretch', 'breath', 'meditation', 'recovery', 'wellness']
        is_recovery = any(kw in combined_lower for kw in recovery_keywords)
        print(f"[Activity Analysis] Detected as recovery activity: {is_recovery}")
        
        # Build the analysis prompt using PromptEngine
        prompt = PromptEngine.build_activity_analysis_prompt(
            activity=activity,
            activity_details=activity_details,
            similar_activities=similar_activities,
            user_profile=garmin.user_profile or {},
            hr_zones=user_hr_zones,
        )
        
        # Generate analysis
        response = ai_service.model.generate_content(prompt)
        analysis_data = ai_service._extract_json(response.text)
        
        if not analysis_data:
            # Return structured fallback
            analysis_data = {
                "overall_rating": "Good",
                "overall_score": 70,
                "one_liner": "Analysis generated but couldn't parse structured response.",
                "performance_summary": response.text[:500] if response.text else "Unable to generate analysis.",
                "comparison_to_history": {"trend": "no_data"},
                "what_went_well": [],
                "what_needs_improvement": [],
                "key_takeaways": ["Continue your training routine."],
                "recommendations_for_next_time": []
            }
        
        # Add metadata
        analysis_data["generated_at"] = datetime.now().isoformat()
        analysis_data["ai_model"] = ai_service.model_name
        
        # Build activity summary
        activity_summary = {
            "name": activity.get("activityName"),
            "type": activity_type,
            "duration_minutes": (activity.get("duration", 0) or 0) / 60,
            "distance_km": (activity.get("distance", 0) or 0) / 1000,
            "calories": activity.get("calories"),
            "avg_hr": activity.get("averageHR"),
            "max_hr": activity.get("maxHR"),
            "training_effect_aerobic": activity.get("aerobicTrainingEffect") or activity.get("trainingEffectAerobic"),
            "training_effect_anaerobic": activity.get("anaerobicTrainingEffect") or activity.get("trainingEffectAnaerobic"),
            "elevation_gain": activity.get("elevationGain"),
            "avg_cadence": activity.get("averageRunningCadenceInStepsPerMinute"),
            "start_time": activity.get("startTimeLocal"),
            # New comprehensive metrics: stress, respiration, performance condition, power
            "avg_stress": activity.get("avgStressLevel"),
            "max_stress": activity.get("maxStressLevel"),
            "avg_respiration": activity.get("avgRespirationRate"),
            "max_respiration": activity.get("maxRespirationRate"),
            "performance_condition": activity.get("performanceCondition") or activity.get("firstBeatPerformanceCondition"),
            "avg_stride_length": activity.get("avgStrideLength"),
            "avg_power": activity.get("avgPower"),
            "max_power": activity.get("maxPower"),
            "normalized_power": activity.get("normPower"),
            "training_load": activity.get("trainingLoad"),
            "recovery_time_minutes": activity.get("recoveryTimeInMinutes"),
            "vo2_max": activity.get("vO2MaxValue"),
            # Flags for extra data
            "has_splits": bool(activity_details.get("splits")),
            "has_weather": bool(activity_details.get("weather")),
        }
        
        # Save analysis to database for caching
        try:
            activity_date = None
            if activity.get("startTimeLocal"):
                try:
                    activity_date = datetime.strptime(activity.get("startTimeLocal")[:19], "%Y-%m-%dT%H:%M:%S")
                except:
                    pass
            
            DatabaseManager.save_activity_analysis(
                activity_id=activity_id,
                activity_type=activity_type,
                activity_name=activity.get("activityName", ""),
                activity_date=activity_date,
                overall_score=analysis_data.get("overall_score", 70),
                overall_rating=analysis_data.get("overall_rating", "Good"),
                analysis_data=analysis_data,
                activity_summary=activity_summary,
                comparison_count=len(similar_activities),
                similar_activities_data={"activities": similar_activities_detailed},
                ai_model=ai_service.model_name
            )
        except Exception as e:
            print(f"Warning: Could not save analysis to database: {e}")
        
        return {
            "activity_id": activity_id,
            "analysis": analysis_data,
            "activity_summary": activity_summary,
            "comparison_activities_count": len(similar_activities),
            "has_splits": bool(activity_details.get("splits")),
            "has_weather": bool(activity_details.get("weather")),
            "cached": False,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Activity analysis error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/activity/{activity_id}/analysis")
async def delete_activity_analysis(activity_id: str):
    """Delete cached analysis for an activity (to allow regeneration)."""
    try:
        deleted = DatabaseManager.delete_activity_analysis(activity_id)
        if deleted:
            return {"message": "Analysis deleted successfully", "activity_id": activity_id}
        else:
            return {"message": "No analysis found to delete", "activity_id": activity_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-month-plan")
async def generate_month_plan(request: MonthPlanRequest):
    """Generate a 4-week (mesocycle) training plan."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated. Please login first.")
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured.")
        
        today = date.today()
        
        # Gather data
        recent_activities = []
        try:
            activities_result = garmin.get_activities(limit=30)
            if isinstance(activities_result, list):
                recent_activities = [a for a in activities_result if isinstance(a, dict)]
        except Exception:
            pass
        
        health_metrics = {}
        try:
            health_metrics = garmin.get_health_metrics_for_ai(days=14)
        except Exception:
            pass
        
        hr_zones = {}
        try:
            hr_zones = garmin.get_hr_zones()
        except Exception:
            pass
        
        # Use target VDOT from goal time if provided, otherwise estimate
        if request.target_vdot:
            estimated_vdot = request.target_vdot
        else:
            estimated_vdot = _estimate_vdot_from_activities(recent_activities)
        
        weekly_volume = _calculate_weekly_volume(recent_activities)
        
        # Count running activities
        running_count = sum(1 for a in recent_activities 
                          if a.get("activityType", {}).get("typeKey") == "running")
        
        # Build the month plan prompt
        prompt = PromptEngine.build_month_plan_prompt(
            user_profile=garmin.user_profile or {},
            primary_goal=request.primary_goal,
            estimated_vdot=estimated_vdot,
            training_phase=request.training_phase,
            health_metrics=health_metrics,
            recent_activities=recent_activities[:14],
            activity_summary={
                "total_activities": len(recent_activities),
                "running_count": running_count,
                "avg_weekly_volume": weekly_volume,
            },
            target_race_date=request.target_race_date,
            hr_zones=hr_zones,
            supplementary_activities=request.supplementary_activities,
            supplementary_frequency=request.supplementary_frequency,
            goal_time=request.goal_time,
            goal_distance_km=request.goal_distance_km,
        )
        
        # Generate month plan
        response = ai_service.model.generate_content(prompt)
        plan_data = ai_service._extract_json(response.text)
        
        # Debug logging
        print(f"[Month Plan] Response received, plan_data parsed: {plan_data is not None}")
        if plan_data:
            print(f"[Month Plan] Keys: {list(plan_data.keys())}")
            if "weeks" in plan_data:
                print(f"[Month Plan] Found {len(plan_data['weeks'])} weeks")
                for i, week in enumerate(plan_data['weeks']):
                    if isinstance(week, dict):
                        workout_count = len(week.get('workouts', []))
                        print(f"[Month Plan] Week {i+1}: {workout_count} workouts")
            else:
                print(f"[Month Plan] WARNING: No 'weeks' key found in response!")
                # Check if workouts are at root level
                if "workouts" in plan_data:
                    print(f"[Month Plan] Found {len(plan_data['workouts'])} workouts at root level")
        
        if plan_data:
            plan_data["generated_at"] = datetime.now().isoformat()
            plan_data["ai_model"] = ai_service.model_name
            plan_data["estimated_vdot"] = estimated_vdot
            plan_data["plan_type"] = "month"
            if request.goal_time:
                plan_data["goal_time"] = request.goal_time
                plan_data["goal_distance_km"] = request.goal_distance_km
            return plan_data
        else:
            print(f"[Month Plan] Failed to parse! Raw response: {response.text[:500]}...")
            return {
                "error": "Failed to parse month plan",
                "raw_response": response.text
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Month plan generation error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pin-plan")
async def pin_workout_plan(request: PinPlanRequest):
    """Pin/save a generated workout plan for tracking."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        plan_data = request.plan_data
        plan_type = request.plan_type
        
        # Debug: log the received data structure
        print(f"Pin plan request - type: {plan_type}")
        print(f"Pin plan data keys: {list(plan_data.keys()) if isinstance(plan_data, dict) else 'not a dict'}")
        if "weeks" in plan_data:
            print(f"Weeks count: {len(plan_data['weeks'])}")
            if plan_data['weeks'] and len(plan_data['weeks']) > 0:
                first_week = plan_data['weeks'][0]
                print(f"First week keys: {list(first_week.keys()) if isinstance(first_week, dict) else 'not a dict'}")
                if "workouts" in first_week:
                    print(f"First week workouts count: {len(first_week['workouts'])}")
        
        # Determine start date
        if request.start_date:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        else:
            start_date = date.today()
        
        # For weekly plans, align to the Monday of the week to ensure proper week grouping
        if plan_type == "week":
            while start_date.weekday() != 0:  # 0 = Monday
                start_date -= timedelta(days=1)
        
        # Calculate end date based on plan type
        if plan_type == "month":
            end_date = start_date + timedelta(days=28)
        else:
            end_date = start_date + timedelta(days=6)  # Monday to Sunday = 6 days difference
        
        # Save the plan to database
        plan_id = DatabaseManager.save_workout_plan(
            plan_name=plan_data.get("plan_name", f"AI {plan_type.title()} Plan"),
            plan_type=plan_type,
            start_date=start_date,
            end_date=end_date,
            primary_goal=plan_data.get("primary_goal", "General Fitness"),
            plan_data=plan_data,
            ai_model=plan_data.get("ai_model", "gemini")
        )
        
        if not plan_id:
            raise HTTPException(status_code=500, detail="Failed to save plan")
        
        # Save individual scheduled workouts
        workouts_to_save = []
        
        # Process based on plan_type, not data structure
        # This ensures weekly plans aren't incorrectly processed as monthly
        if plan_type == "month":
            # Month plan structure - expect weeks array
            weeks_data = plan_data.get("weeks") or plan_data.get("weekly_plans") or []
            current_date = start_date
            for week_idx, week in enumerate(weeks_data):
                # Get workouts from the week - check multiple possible keys
                week_workouts = week.get("workouts") or week.get("daily_workouts") or []
                
                # Find the Monday of the current week
                week_start = current_date
                while week_start.weekday() != 0:  # 0 = Monday
                    week_start -= timedelta(days=1)
                
                for workout in week_workouts:
                    day_name = workout.get("day", "Monday")
                    try:
                        # Find the day offset within the week
                        days_ahead = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                                      "Friday", "Saturday", "Sunday"].index(day_name)
                    except ValueError:
                        days_ahead = 0
                    
                    workout_date = week_start + timedelta(days=days_ahead)
                    workouts_to_save.append({
                        "date": workout_date,
                        "workout": workout
                    })
                current_date += timedelta(days=7)
        else:
            # Week plan structure - use flat workouts array
            # First try workouts key, then fall back to extracting from weeks if AI returned that structure
            flat_workouts = plan_data.get("workouts") or []
            
            # If workouts is empty but we have weeks (AI returned week plan in weeks format), extract them
            if not flat_workouts:
                weeks_data = plan_data.get("weeks") or plan_data.get("weekly_plans") or []
                if weeks_data and len(weeks_data) > 0:
                    # Take only the first week for a week plan
                    first_week = weeks_data[0]
                    flat_workouts = first_week.get("workouts") or first_week.get("daily_workouts") or []
            
            # For weekly plans, find the Monday of the current week and schedule from there
            # This ensures all workouts stay within the same week (Week 1)
            week_start = start_date
            while week_start.weekday() != 0:  # 0 = Monday
                week_start -= timedelta(days=1)
            
            for workout in flat_workouts:
                day_name = workout.get("day", "Monday")
                days_map = {
                    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                    "Friday": 4, "Saturday": 5, "Sunday": 6
                }
                days_from_monday = days_map.get(day_name, 0)
                workout_date = week_start + timedelta(days=days_from_monday)
                workouts_to_save.append({
                    "date": workout_date,
                    "workout": workout
                })

        
        print(f"Pin plan: found {len(workouts_to_save)} workouts to save")
        
        # Save each scheduled workout with full details
        for item in workouts_to_save:
            workout = item["workout"]
            
            # Extract steps/exercises from various possible locations in AI response
            steps = workout.get("steps") or workout.get("exercises") or []
            
            # Extract supplementary activities - handle both list and dict formats
            supplementary = workout.get("supplementary")
            if isinstance(supplementary, dict):
                # Convert dict to list format if needed
                supplementary = [supplementary]
            elif not isinstance(supplementary, list):
                supplementary = []
            
            # Extract other fields with fallbacks
            description = workout.get("description") or workout.get("rationale") or ""
            duration = workout.get("duration_minutes") or workout.get("total_duration_minutes")
            hr_zone = workout.get("target_hr_zone") or workout.get("hr_zone")
            hr_bpm = workout.get("target_hr_bpm") or workout.get("hr_bpm")
            
            DatabaseManager.save_scheduled_workout(
                plan_id=plan_id,
                scheduled_date=item["date"],
                workout_type=workout.get("type", "other"),
                title=workout.get("title", workout.get("name", "Workout")),
                description=description,
                duration_minutes=duration,
                intensity=workout.get("intensity", "moderate"),
                exercises=steps,
                target_hr_zone=hr_zone,
                # Rich display fields
                key_focus=workout.get("key_focus"),
                estimated_distance_km=workout.get("estimated_distance_km") or workout.get("distance_km"),
                target_hr_bpm=hr_bpm,
                supplementary=supplementary,
                optimal_time=workout.get("optimal_time"),
            )
        
        return {
            "success": True,
            "plan_id": plan_id,
            "message": f"Plan saved with {len(workouts_to_save)} scheduled workouts",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Pin plan error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pinned-plans")
async def get_pinned_plans():
    """Get all pinned/saved workout plans."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        plans = DatabaseManager.get_active_workout_plans()
        
        result = []
        for plan in plans:
            # Get scheduled workouts for this plan
            scheduled = DatabaseManager.get_scheduled_workouts(plan.id)
            completed = sum(1 for w in scheduled if w.is_completed)
            
            result.append({
                "id": plan.id,
                "plan_name": plan.plan_name,
                "plan_type": plan.plan_type,
                "start_date": plan.start_date.isoformat() if plan.start_date else None,
                "end_date": plan.end_date.isoformat() if plan.end_date else None,
                "primary_goal": plan.primary_goal,
                "is_active": plan.is_active,
                "total_workouts": len(scheduled),
                "completed_workouts": completed,
                "progress_percentage": (completed / len(scheduled) * 100) if scheduled else 0,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
            })
        
        return {"plans": result}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get pinned plans error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pinned-plan/{plan_id}")
async def get_pinned_plan_details(plan_id: int):
    """Get detailed view of a pinned plan with all workouts."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        plan = DatabaseManager.get_workout_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        scheduled = DatabaseManager.get_scheduled_workouts(plan_id)
        
        workouts = []
        for w in scheduled:
            workout_data = {
                "id": w.id,
                "scheduled_date": w.scheduled_date.isoformat() if w.scheduled_date else None,
                "workout_type": w.workout_type,
                "title": w.title,
                "description": w.description,
                "duration_minutes": w.duration_minutes,
                "intensity": w.intensity,
                "target_hr_zone": w.target_hr_zone,
                "exercises": w.exercises,
                "steps": w.exercises,  # Alias for frontend compatibility
                "is_completed": w.is_completed,
                "completed_at": w.completed_at.isoformat() if w.completed_at else None,
                "actual_duration_minutes": w.actual_duration_minutes,
                "actual_calories": w.actual_calories,
                "linked_activity_id": w.linked_activity_id,
                "notes": w.notes,
                # New fields for rich display
                "key_focus": w.key_focus,
                "estimated_distance_km": w.estimated_distance_km,
                "target_hr_bpm": w.target_hr_bpm,
                "supplementary": w.supplementary,
                "optimal_time": w.optimal_time,
            }
            
            # Get linked activity details if available
            if w.linked_activity_id:
                try:
                    activity = garmin.get_activity_details(w.linked_activity_id)
                    if activity:
                        workout_data["linked_activity"] = {
                            "name": activity.get("activityName"),
                            "type": activity.get("activityType", {}).get("typeKey"),
                            "duration": activity.get("duration"),
                            "distance": activity.get("distance"),
                            "avg_hr": activity.get("averageHR"),
                            "max_hr": activity.get("maxHR"),
                            "calories": activity.get("calories"),
                            "training_effect": activity.get("aerobicTrainingEffect"),
                        }
                except Exception:
                    pass
            
            workouts.append(workout_data)
        
        return {
            "id": plan.id,
            "plan_name": plan.plan_name,
            "plan_type": plan.plan_type,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "primary_goal": plan.primary_goal,
            "plan_data": plan.plan_data,
            "is_active": plan.is_active,
            "workouts": workouts,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get pinned plan details error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-activity")
async def match_activity_to_workout(request: MatchActivityRequest):
    """Match a Garmin activity to a scheduled workout to mark it complete."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get the scheduled workout
        workout = DatabaseManager.get_scheduled_workout(request.scheduled_workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail="Scheduled workout not found")
        
        # Get the activity details
        activity = garmin.get_activity_details(request.activity_id)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        # Update the scheduled workout with activity data
        success = DatabaseManager.complete_scheduled_workout(
            workout_id=request.scheduled_workout_id,
            activity_id=request.activity_id,
            actual_duration=(activity.get("duration", 0) or 0) / 60,  # Convert to minutes
            actual_calories=activity.get("calories"),
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to match activity")
        
        return {
            "success": True,
            "message": "Activity matched to workout",
            "workout_id": request.scheduled_workout_id,
            "activity_id": request.activity_id,
            "activity_summary": {
                "name": activity.get("activityName"),
                "type": activity.get("activityType", {}).get("typeKey"),
                "duration_minutes": (activity.get("duration", 0) or 0) / 60,
                "distance_km": (activity.get("distance", 0) or 0) / 1000,
                "avg_hr": activity.get("averageHR"),
                "calories": activity.get("calories"),
                "training_effect": activity.get("aerobicTrainingEffect"),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Match activity error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-match-activities")
async def auto_match_activities():
    """Automatically match recent activities to scheduled workouts based on date and type."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get recent activities
        recent_activities = garmin.get_activities(limit=20)
        if not isinstance(recent_activities, list):
            recent_activities = []
        
        # Get incomplete scheduled workouts from active plans
        active_plans = DatabaseManager.get_active_workout_plans()
        
        matched = []
        
        for plan in active_plans:
            scheduled = DatabaseManager.get_scheduled_workouts(plan.id)
            
            for workout in scheduled:
                if workout.is_completed:
                    continue
                
                # Look for matching activity
                for activity in recent_activities:
                    # Get activity date
                    activity_date_str = activity.get("startTimeLocal", "")[:10]
                    try:
                        activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        continue
                    
                    # Check if dates match
                    if activity_date != workout.scheduled_date:
                        continue
                    
                    # Check if activity type matches workout type (fuzzy matching)
                    activity_type = activity.get("activityType", {}).get("typeKey", "").lower()
                    workout_type = (workout.workout_type or "").lower()
                    
                    # Type matching rules
                    type_matches = False
                    if workout_type in ["easy_run", "long_run", "tempo", "interval", "recovery"]:
                        type_matches = "running" in activity_type or "treadmill" in activity_type
                    elif workout_type == "strength":
                        type_matches = "strength" in activity_type or "hiit" in activity_type
                    elif workout_type == "rest":
                        continue  # Don't match rest days
                    else:
                        # Generic match - any activity on that day counts
                        type_matches = True
                    
                    if type_matches:
                        # Match found - update the workout
                        success = DatabaseManager.complete_scheduled_workout(
                            workout_id=workout.id,
                            activity_id=str(activity.get("activityId")),
                            actual_duration=(activity.get("duration", 0) or 0) / 60,
                            actual_calories=activity.get("calories"),
                        )
                        
                        if success:
                            matched.append({
                                "workout_id": workout.id,
                                "workout_title": workout.title,
                                "workout_date": workout.scheduled_date.isoformat(),
                                "activity_id": str(activity.get("activityId")),
                                "activity_name": activity.get("activityName"),
                                "activity_type": activity_type,
                            })
                        break  # Move to next workout
        
        return {
            "success": True,
            "matched_count": len(matched),
            "matched_workouts": matched,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Auto-match error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pinned-plan/{plan_id}")
async def delete_pinned_plan(plan_id: int):
    """Delete/unpin a workout plan."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        success = DatabaseManager.delete_workout_plan(plan_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Plan not found or already deleted")
        
        return {"success": True, "message": "Plan deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete plan error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


class AdjustPlanRequest(BaseModel):
    plan_id: int
    adjustment_type: str = "auto"  # auto, increase_intensity, decrease_intensity, add_recovery


@router.post("/adjust-pinned-plan")
async def adjust_pinned_plan(request: AdjustPlanRequest):
    """Adjust a pinned plan based on current health data and recent performance.
    
    This analyzes the user's current readiness (Body Battery, HRV, Sleep) and recent
    activity performance to suggest and apply adjustments to the remaining workouts.
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get the plan
        plan = DatabaseManager.get_workout_plan(request.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Get current health data
        today_readiness = garmin.get_today_readiness()
        recent_activities = garmin.get_activities(limit=10)
        
        # Get scheduled workouts that haven't been completed
        scheduled = DatabaseManager.get_scheduled_workouts(request.plan_id)
        incomplete_workouts = [w for w in scheduled if not w.is_completed]
        
        if not incomplete_workouts:
            return {
                "success": True,
                "message": "All workouts are already completed!",
                "adjustments_made": 0
            }
        
        # Analyze readiness
        body_battery = today_readiness.get("body_battery", 50)
        sleep_score = today_readiness.get("sleep_score", 70)
        hrv_status = today_readiness.get("hrv_status", "Unknown")
        
        # Calculate adjustment factor
        readiness_score = (
            (body_battery / 100) * 0.4 +
            (sleep_score / 100) * 0.3 +
            (1.0 if hrv_status in ["BALANCED", "HIGH"] else 0.7 if hrv_status == "LOW" else 0.85) * 0.3
        )
        
        adjustments = []
        adjustment_factor = 1.0
        
        if request.adjustment_type == "auto":
            if readiness_score < 0.5:
                adjustment_factor = 0.7
                adjustments.append("Reduced intensity due to low readiness")
            elif readiness_score < 0.7:
                adjustment_factor = 0.85
                adjustments.append("Slightly reduced intensity")
            elif readiness_score > 0.85:
                adjustment_factor = 1.1
                adjustments.append("Increased intensity due to good readiness")
        elif request.adjustment_type == "increase_intensity":
            adjustment_factor = 1.15
            adjustments.append("Manual increase in intensity")
        elif request.adjustment_type == "decrease_intensity":
            adjustment_factor = 0.8
            adjustments.append("Manual decrease in intensity")
        elif request.adjustment_type == "add_recovery":
            adjustments.append("Added extra recovery day")
        
        # Apply adjustments to incomplete workouts
        adjusted_count = 0
        for workout in incomplete_workouts:
            if workout.duration_minutes:
                new_duration = int(workout.duration_minutes * adjustment_factor)
                # Update workout in database (simplified - in real impl, update exercises too)
                DatabaseManager.update_scheduled_workout(
                    workout.id,
                    duration_minutes=new_duration,
                    notes=f"Adjusted ({adjustment_factor:.0%}) based on readiness"
                )
                adjusted_count += 1
        
        return {
            "success": True,
            "message": f"Plan adjusted based on current readiness ({readiness_score:.0%})",
            "adjustments_made": adjusted_count,
            "adjustment_factor": adjustment_factor,
            "adjustments": adjustments,
            "readiness_data": {
                "body_battery": body_battery,
                "sleep_score": sleep_score,
                "hrv_status": hrv_status,
                "readiness_score": round(readiness_score * 100)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Adjust plan error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hr-zones")
async def get_hr_zones():
    """Get user's heart rate zones."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        hr_zones = garmin.get_hr_zones()
        return hr_zones
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"HR zones error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today-readiness")
async def get_today_readiness():
    """Get today's readiness data for autoregulation decisions."""
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        readiness = garmin.get_today_readiness()
        return readiness
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Today readiness error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
