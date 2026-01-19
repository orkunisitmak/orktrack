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
    period: str = "week"  # "week" or "month"
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
    """Generate AI health insights."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated. Please login first.")
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured. Please add GEMINI_API_KEY to .env file.")
        
        days = 7 if request.period == "week" else 30
        
        # Get comprehensive data
        raw_data = {}
        try:
            raw_data = garmin.get_comprehensive_data(days=days)
        except Exception as e:
            print(f"Error getting comprehensive data: {e}")
            raw_data = {
                "health_summary": garmin.get_health_metrics_for_ai(days=days),
                "sleep_data": [],
                "activities": []
            }
        
        # Build structured prompt
        prompt = PromptEngine.build_insights_prompt(
            user_profile=garmin.user_profile or {},
            health_data=raw_data.get("health_summary", {}),
            sleep_data=raw_data.get("sleep_data", []),
            activities=raw_data.get("activities", []),
            period=request.period,
            focus_areas=request.focus_areas
        )
        
        # Generate insights
        response = ai_service.model.generate_content(prompt)
        insights_data = ai_service._extract_json(response.text)
        
        if insights_data:
            insights_data["generated_at"] = datetime.now().isoformat()
            insights_data["period"] = request.period
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
                "weekly_focus": "Continue your current routine",
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
async def analyze_activity(activity_id: str):
    """Get comprehensive AI analysis of a specific activity with comparisons."""
    try:
        garmin = get_garmin_service()
        ai_service = AIService()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not ai_service.is_configured():
            raise HTTPException(status_code=503, detail="AI service not configured")
        
        # Get activity details
        activity = garmin.get_activity_details(activity_id)
        
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        # Get additional activity details
        activity_details = {}
        
        # Get splits
        try:
            splits = garmin.get_activity_splits(activity_id)
            activity_details["splits"] = splits
        except Exception as e:
            print(f"Error getting splits: {e}")
        
        # Get HR zones distribution
        try:
            hr_zones = garmin.get_activity_hr_zones(activity_id)
            activity_details["hr_zones"] = hr_zones
        except Exception as e:
            print(f"Error getting HR zones: {e}")
        
        # Get weather
        try:
            weather = garmin.get_activity_weather(activity_id)
            activity_details["weather"] = weather
        except Exception as e:
            print(f"Error getting weather: {e}")
        
        # Get similar activities for comparison (same type, recent)
        activity_type = activity.get("activityType", {}).get("typeKey", "other") if isinstance(activity.get("activityType"), dict) else "other"
        similar_activities = []
        
        try:
            # Get recent activities of same type
            recent_activities = garmin.get_activities(limit=30)
            if isinstance(recent_activities, list):
                for act in recent_activities:
                    if not isinstance(act, dict):
                        continue
                    act_type = act.get("activityType", {}).get("typeKey", "other") if isinstance(act.get("activityType"), dict) else "other"
                    # Same type and not the current activity
                    if act_type == activity_type and str(act.get("activityId")) != str(activity_id):
                        similar_activities.append(act)
                        if len(similar_activities) >= 5:
                            break
        except Exception as e:
            print(f"Error getting similar activities: {e}")
        
        # Get user's HR zones
        user_hr_zones = {}
        try:
            user_hr_zones = garmin.get_hr_zones()
        except Exception as e:
            print(f"Error getting user HR zones: {e}")
        
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
        
        return {
            "activity_id": activity_id,
            "analysis": analysis_data,
            "activity_summary": {
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
            },
            "comparison_activities_count": len(similar_activities),
            "has_splits": bool(activity_details.get("splits")),
            "has_weather": bool(activity_details.get("weather")),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Activity analysis error: {traceback.format_exc()}")
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
        
        # Determine start date
        if request.start_date:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        else:
            start_date = date.today()
        
        # Calculate end date based on plan type
        if plan_type == "month":
            end_date = start_date + timedelta(days=28)
        else:
            end_date = start_date + timedelta(days=7)
        
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
        
        if plan_type == "month" and "weeks" in plan_data:
            # Month plan structure
            current_date = start_date
            for week in plan_data.get("weeks", []):
                for workout in week.get("workouts", []):
                    day_name = workout.get("day", "Monday")
                    # Find the next occurrence of this day
                    days_ahead = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                                  "Friday", "Saturday", "Sunday"].index(day_name)
                    workout_date = current_date + timedelta(days=days_ahead)
                    workouts_to_save.append({
                        "date": workout_date,
                        "workout": workout
                    })
                current_date += timedelta(days=7)
        else:
            # Week plan structure
            for workout in plan_data.get("workouts", []):
                day_name = workout.get("day", "Monday")
                days_map = {
                    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                    "Friday": 4, "Saturday": 5, "Sunday": 6
                }
                days_from_monday = days_map.get(day_name, 0)
                # Calculate from start of week
                days_until_monday = (7 - start_date.weekday()) % 7
                workout_date = start_date + timedelta(days=days_until_monday + days_from_monday)
                workouts_to_save.append({
                    "date": workout_date,
                    "workout": workout
                })
        
        # Save each scheduled workout
        for item in workouts_to_save:
            workout = item["workout"]
            DatabaseManager.save_scheduled_workout(
                plan_id=plan_id,
                scheduled_date=item["date"],
                workout_type=workout.get("type", "other"),
                title=workout.get("title", "Workout"),
                description=workout.get("description", ""),
                duration_minutes=workout.get("duration_minutes"),
                intensity=workout.get("intensity", "moderate"),
                exercises=workout.get("steps", []),
                target_hr_zone=workout.get("target_hr_zone"),
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
                "is_completed": w.is_completed,
                "completed_at": w.completed_at.isoformat() if w.completed_at else None,
                "actual_duration_minutes": w.actual_duration_minutes,
                "actual_calories": w.actual_calories,
                "linked_activity_id": w.linked_activity_id,
                "notes": w.notes,
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
