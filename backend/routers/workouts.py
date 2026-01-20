"""Workouts API Router - Workout Plans and Scheduling."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import DatabaseManager
from .auth import get_garmin_service

router = APIRouter()


class WorkoutPlanCreate(BaseModel):
    plan_name: str
    plan_type: str = "weekly"
    primary_goal: str
    target_days_per_week: int = 4
    plan_data: Dict[str, Any]


class ScheduledWorkoutComplete(BaseModel):
    actual_duration_minutes: Optional[int] = None
    actual_calories: Optional[int] = None
    linked_activity_id: Optional[str] = None
    notes: Optional[str] = None


@router.get("/plans")
async def get_workout_plans(active_only: bool = True):
    """Get all workout plans."""
    try:
        if active_only:
            plan = DatabaseManager.get_active_plan()
            return {"plans": [plan.plan_data] if plan else [], "total": 1 if plan else 0}
        else:
            # Would need to implement get_all_plans in DatabaseManager
            plan = DatabaseManager.get_active_plan()
            return {"plans": [plan.plan_data] if plan else [], "total": 1 if plan else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans")
async def create_workout_plan(plan: WorkoutPlanCreate):
    """Create a new workout plan."""
    try:
        plan_data = {
            "plan_name": plan.plan_name,
            "plan_type": plan.plan_type,
            "primary_goal": plan.primary_goal,
            "target_days_per_week": plan.target_days_per_week,
            **plan.plan_data
        }
        
        saved_plan = DatabaseManager.save_workout_plan(plan_data)
        
        return {
            "success": True,
            "plan_id": saved_plan.id,
            "message": "Workout plan created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled")
async def get_scheduled_workouts(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: int = Query(default=7, le=90)
):
    """Get scheduled workouts for a date range."""
    try:
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = start_date + timedelta(days=days)
        
        workouts = DatabaseManager.get_scheduled_workouts(
            start_date=start_date,
            end_date=end_date
        )
        
        # Convert to dict format
        workout_list = []
        for w in workouts:
            workout_list.append({
                "id": w.id,
                "scheduled_date": w.scheduled_date.isoformat(),
                "workout_type": w.workout_type,
                "title": w.title,
                "description": w.description,
                "duration_minutes": w.duration_minutes,
                "intensity": w.intensity,
                "exercises": w.exercises,
                "target_hr_zone": w.target_hr_zone,
                "estimated_calories": w.estimated_calories,
                "is_completed": w.is_completed,
                "completed_at": w.completed_at.isoformat() if w.completed_at else None,
            })
        
        return {"workouts": workout_list, "total": len(workout_list)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled/{workout_id}/complete")
async def complete_workout(workout_id: int, data: ScheduledWorkoutComplete):
    """Mark a scheduled workout as complete."""
    try:
        success = DatabaseManager.complete_workout(
            workout_id=workout_id,
            actual_data={
                "duration_minutes": data.actual_duration_minutes,
                "calories": data.actual_calories,
                "activity_id": data.linked_activity_id,
                "notes": data.notes
            }
        )
        
        if success:
            return {"success": True, "message": "Workout marked as complete"}
        else:
            raise HTTPException(status_code=404, detail="Workout not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goals")
async def get_goals(active_only: bool = True):
    """Get user fitness goals."""
    try:
        goals = DatabaseManager.get_active_goals()
        
        goal_list = []
        for g in goals:
            goal_list.append({
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "category": g.category,
                "target_value": g.target_value,
                "current_value": g.current_value,
                "unit": g.unit,
                "timeframe": g.timeframe,
                "progress_percentage": g.progress_percentage,
                "is_completed": g.is_completed,
                "difficulty": g.difficulty,
                "ai_recommended": g.ai_recommended,
            })
        
        return {"goals": goal_list, "total": len(goal_list)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/goals")
async def create_goal(goal_data: Dict[str, Any]):
    """Create a new fitness goal."""
    try:
        saved_goal = DatabaseManager.save_goal(goal_data)
        
        return {
            "success": True,
            "goal_id": saved_goal.id,
            "message": "Goal created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/goals/{goal_id}/progress")
async def update_goal_progress(goal_id: int, current_value: float):
    """Update goal progress."""
    try:
        success = DatabaseManager.update_goal_progress(goal_id, current_value)
        
        if success:
            return {"success": True, "message": "Goal progress updated"}
        else:
            raise HTTPException(status_code=404, detail="Goal not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class WorkoutStep(BaseModel):
    """Individual workout step (warmup, interval, cooldown, etc.)."""
    type: str  # warmup, active, recovery, rest, cooldown, repeat
    duration_minutes: Optional[float] = None
    duration_type: str = "time"  # time, distance, open
    distance_meters: Optional[int] = None
    target_type: Optional[str] = None  # pace, heart_rate, power, cadence, open
    target_pace_min: Optional[str] = None  # e.g., "5:30" for 5:30 min/km
    target_pace_max: Optional[str] = None
    target_hr_zone: Optional[int] = None  # 1-5
    target_hr_bpm_low: Optional[int] = None
    target_hr_bpm_high: Optional[int] = None
    description: Optional[str] = None
    repeat_count: Optional[int] = None  # for repeat steps
    repeat_steps: Optional[List[Dict[str, Any]]] = None


class GarminWorkoutCreate(BaseModel):
    """Workout structure to send to Garmin."""
    title: str
    description: str
    type: str = "running"  # running, cycling, strength, swimming, walking, hiking
    duration_minutes: int
    steps: Optional[List[WorkoutStep]] = None
    target_hr_zone: Optional[str] = None
    scheduled_date: Optional[str] = None  # YYYY-MM-DD


class GarminBatchUpload(BaseModel):
    """Batch upload multiple workouts."""
    workouts: List[GarminWorkoutCreate]
    plan_name: Optional[str] = None


def pace_to_speed_ms(pace_str: str) -> float:
    """Convert pace string (e.g., '5:30') to speed in m/s."""
    try:
        parts = pace_str.split(":")
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = int(parts[1])
            total_seconds = minutes * 60 + seconds
            if total_seconds > 0:
                return 1000 / total_seconds  # m/s
    except:
        pass
    return 2.78  # Default ~5:59 min/km


def build_garmin_workout(workout: GarminWorkoutCreate, hr_zones: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build a properly structured Garmin workout."""
    
    # Map workout types to Garmin sport types
    sport_map = {
        "running": "RUNNING",
        "cycling": "CYCLING",
        "swimming": "SWIMMING",
        "strength": "STRENGTH_TRAINING",
        "walking": "WALKING",
        "hiking": "HIKING",
        "yoga": "YOGA",
        "other": "OTHER",
    }
    
    sport_type = sport_map.get(workout.type.lower(), "RUNNING")
    
    garmin_workout = {
        "workoutName": workout.title,
        "description": workout.description or "",
        "sport": sport_type,
        "estimatedDurationInSecs": workout.duration_minutes * 60,
        "workoutSegments": [],
    }
    
    if workout.steps:
        segment = {
            "segmentOrder": 1,
            "sportType": sport_type,
            "workoutSteps": []
        }
        
        step_order = 1
        for step in workout.steps:
            garmin_step = build_garmin_step(step, step_order, hr_zones)
            segment["workoutSteps"].append(garmin_step)
            step_order += 1
        
        garmin_workout["workoutSegments"].append(segment)
    else:
        # Create default structure with warmup, main, cooldown
        segment = {
            "segmentOrder": 1,
            "sportType": sport_type,
            "workoutSteps": [
                {
                    "type": "WARMUP",
                    "stepOrder": 1,
                    "description": "Warm up",
                    "durationType": "TIME",
                    "durationValue": 600000,  # 10 minutes in ms
                    "targetType": "OPEN",
                },
                {
                    "type": "ACTIVE",
                    "stepOrder": 2,
                    "description": "Main workout",
                    "durationType": "TIME",
                    "durationValue": (workout.duration_minutes - 15) * 60000,
                    "targetType": "OPEN",
                },
                {
                    "type": "COOLDOWN",
                    "stepOrder": 3,
                    "description": "Cool down",
                    "durationType": "TIME",
                    "durationValue": 300000,  # 5 minutes in ms
                    "targetType": "OPEN",
                }
            ]
        }
        garmin_workout["workoutSegments"].append(segment)
    
    return garmin_workout


def build_garmin_step(step: WorkoutStep, order: int, hr_zones: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build a single Garmin workout step."""
    
    # Map step types
    type_map = {
        "warmup": "WARMUP",
        "active": "ACTIVE",
        "recovery": "RECOVERY",
        "rest": "REST",
        "cooldown": "COOLDOWN",
        "interval": "ACTIVE",
        "repeat": "REPEAT",
    }
    
    step_type = type_map.get(step.type.lower(), "ACTIVE")
    
    garmin_step = {
        "type": step_type,
        "stepOrder": order,
        "description": step.description or "",
    }
    
    # Set duration
    if step.duration_type == "distance" and step.distance_meters:
        garmin_step["durationType"] = "DISTANCE"
        garmin_step["durationValue"] = step.distance_meters
    elif step.duration_minutes:
        garmin_step["durationType"] = "TIME"
        garmin_step["durationValue"] = int(step.duration_minutes * 60000)  # milliseconds
    else:
        garmin_step["durationType"] = "OPEN"
    
    # Set target
    if step.target_type == "pace" and step.target_pace_min:
        speed_low = pace_to_speed_ms(step.target_pace_max or step.target_pace_min) * 0.95
        speed_high = pace_to_speed_ms(step.target_pace_min) * 1.05
        garmin_step["targetType"] = "SPEED"
        garmin_step["targetValueLow"] = speed_low
        garmin_step["targetValueHigh"] = speed_high
    elif step.target_type == "heart_rate":
        garmin_step["targetType"] = "HEART_RATE"
        if step.target_hr_bpm_low and step.target_hr_bpm_high:
            garmin_step["targetValueLow"] = step.target_hr_bpm_low
            garmin_step["targetValueHigh"] = step.target_hr_bpm_high
        elif step.target_hr_zone and hr_zones:
            # Get HR zone boundaries
            zone_key = f"zone{step.target_hr_zone}"
            zone_data = hr_zones.get("zones", {}).get(zone_key, {})
            garmin_step["targetValueLow"] = zone_data.get("low", 100)
            garmin_step["targetValueHigh"] = zone_data.get("high", 150)
    else:
        garmin_step["targetType"] = "OPEN"
    
    # Handle repeat steps
    if step.type.lower() == "repeat" and step.repeat_count and step.repeat_steps:
        garmin_step["numberOfIterations"] = step.repeat_count
        garmin_step["childSteps"] = []
        for i, child in enumerate(step.repeat_steps):
            child_step = WorkoutStep(**child)
            garmin_step["childSteps"].append(build_garmin_step(child_step, i + 1, hr_zones))
    
    return garmin_step


@router.post("/send-to-garmin")
async def send_workout_to_garmin(workout: GarminWorkoutCreate):
    """
    Send a single workout to Garmin Connect.
    Creates a properly structured workout with warmup, main workout, and cooldown.
    The workout will appear in Garmin Connect and sync to your watch.
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Convert steps to the format expected by garmin_service
        formatted_steps = []
        if workout.steps:
            for step in workout.steps:
                formatted_step = {
                    "type": step.type,
                    "duration_minutes": step.duration_minutes,
                    "distance_meters": step.distance_meters,
                    "target_type": step.target_type or "open",
                    "target_pace_min": step.target_pace_min,
                    "target_pace_max": step.target_pace_max,
                    "target_hr_zone": step.target_hr_zone,
                    "description": step.description or "",
                    "repeat_count": step.repeat_count,
                    "repeat_steps": step.repeat_steps,
                }
                formatted_steps.append(formatted_step)
        else:
            # Create default steps with warmup, main, cooldown
            warmup_duration = min(10, workout.duration_minutes * 0.15)
            cooldown_duration = min(5, workout.duration_minutes * 0.1)
            main_duration = workout.duration_minutes - warmup_duration - cooldown_duration
            
            formatted_steps = [
                {"type": "warmup", "duration_minutes": warmup_duration, "target_type": "open", "description": "Warm up gradually"},
                {"type": "active", "duration_minutes": main_duration, "target_type": "open", "description": "Main workout"},
                {"type": "cooldown", "duration_minutes": cooldown_duration, "target_type": "open", "description": "Cool down easy"},
            ]
        
        # Upload using the structured method
        upload_result = garmin.upload_running_workout_structured(
            workout_name=workout.title,
            steps=formatted_steps,
            estimated_duration_secs=workout.duration_minutes * 60
        )
        
        upload_success = upload_result.get("success", False) and not upload_result.get("error")
        
        # Try to schedule if date provided
        scheduled_result = None
        if workout.scheduled_date and upload_success and upload_result.get("workoutId"):
            try:
                scheduled_result = garmin.schedule_workout(
                    upload_result["workoutId"], 
                    workout.scheduled_date
                )
            except Exception as e:
                print(f"Scheduling error: {e}")
        
        if upload_success:
            return {
                "success": True,
                "message": f"✅ Workout '{workout.title}' uploaded to Garmin Connect! Sync your watch to download it.",
                "workout_id": upload_result.get("workoutId"),
                "scheduled": bool(scheduled_result and not scheduled_result.get("error")),
                "scheduled_date": workout.scheduled_date,
                "steps_summary": [
                    {
                        "type": s.get("type", "active"),
                        "duration": f"{s.get('duration_minutes', 0)} min" if s.get("duration_minutes") else "Open",
                        "target": f"{s.get('target_pace_min')}/km" if s.get("target_pace_min") else f"Zone {s.get('target_hr_zone')}" if s.get("target_hr_zone") else "Open"
                    }
                    for s in formatted_steps
                ],
                "instructions": "Open Garmin Connect app on your phone and sync your watch to download the workout."
            }
        else:
            error_msg = upload_result.get("error", "Unknown error")
            return {
                "success": False,
                "message": f"❌ Failed to upload workout: {error_msg}",
                "error": error_msg,
                "manual_creation_url": "https://connect.garmin.com/modern/workouts",
                "instructions": "You can manually create this workout in Garmin Connect."
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-day-to-garmin")
async def send_day_to_garmin(day_workouts: List[GarminWorkoutCreate]):
    """Send all workouts for a single day to Garmin."""
    try:
        results = []
        for workout in day_workouts:
            result = await send_workout_to_garmin(workout)
            results.append(result)
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count > 0,
            "message": f"Sent {success_count}/{len(day_workouts)} workouts to Garmin",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-week-to-garmin")
async def send_week_to_garmin(request: GarminBatchUpload):
    """Send an entire week's workouts to Garmin Connect.
    
    All workouts will be uploaded and will appear in your Garmin Connect workout library.
    Sync your watch to download them.
    """
    try:
        garmin = get_garmin_service()
        
        if not garmin.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        results = []
        
        for workout in request.workouts:
            try:
                # Convert steps to the format expected by garmin_service
                formatted_steps = []
                if workout.steps:
                    for step in workout.steps:
                        formatted_step = {
                            "type": step.type,
                            "duration_minutes": step.duration_minutes,
                            "distance_meters": step.distance_meters,
                            "target_type": step.target_type or "open",
                            "target_pace_min": step.target_pace_min,
                            "target_pace_max": step.target_pace_max,
                            "target_hr_zone": step.target_hr_zone,
                            "description": step.description or "",
                            "repeat_count": step.repeat_count,
                            "repeat_steps": step.repeat_steps,
                        }
                        formatted_steps.append(formatted_step)
                else:
                    # Create default steps
                    warmup_duration = min(10, workout.duration_minutes * 0.15)
                    cooldown_duration = min(5, workout.duration_minutes * 0.1)
                    main_duration = workout.duration_minutes - warmup_duration - cooldown_duration
                    
                    formatted_steps = [
                        {"type": "warmup", "duration_minutes": warmup_duration, "target_type": "open", "description": "Warm up"},
                        {"type": "active", "duration_minutes": main_duration, "target_type": "open", "description": workout.description or "Main workout"},
                        {"type": "cooldown", "duration_minutes": cooldown_duration, "target_type": "open", "description": "Cool down"},
                    ]
                
                # Upload the workout
                upload_result = garmin.upload_running_workout_structured(
                    workout_name=workout.title,
                    steps=formatted_steps,
                    estimated_duration_secs=workout.duration_minutes * 60
                )
                
                upload_success = upload_result.get("success", False) and not upload_result.get("error")
                
                # Try to schedule if date provided
                if workout.scheduled_date and upload_success and upload_result.get("workoutId"):
                    try:
                        garmin.schedule_workout(upload_result["workoutId"], workout.scheduled_date)
                    except Exception:
                        pass  # Scheduling is optional
                
                results.append({
                    "title": workout.title,
                    "date": workout.scheduled_date,
                    "success": upload_success,
                    "workout_id": upload_result.get("workoutId"),
                    "error": upload_result.get("error") if not upload_success else None
                })
                
            except Exception as e:
                results.append({
                    "title": workout.title,
                    "date": workout.scheduled_date,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r.get("success"))
        total_count = len(request.workouts)
        
        if success_count == total_count:
            message = f"✅ All {success_count} workouts uploaded to Garmin Connect! Sync your watch to download them."
        elif success_count > 0:
            message = f"⚠️ Uploaded {success_count}/{total_count} workouts to Garmin. Some failed - check results."
        else:
            message = f"❌ Failed to upload workouts to Garmin."
        
        return {
            "success": success_count > 0,
            "message": message,
            "plan_name": request.plan_name,
            "uploaded_count": success_count,
            "total_count": total_count,
            "results": results,
            "instructions": "Open Garmin Connect app and sync your watch to download the workouts."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-month-to-garmin")
async def send_month_to_garmin(request: GarminBatchUpload):
    """Send an entire month's workouts to Garmin."""
    # Uses the same logic as week upload
    return await send_week_to_garmin(request)


class PlanAdjustmentRequest(BaseModel):
    """Request to adjust a plan based on current health data."""
    plan_id: Optional[int] = None
    plan_data: Dict[str, Any]
    body_battery: int
    sleep_score: Optional[int] = None
    resting_hr: Optional[int] = None
    stress_level: Optional[int] = None
    recent_training_load: Optional[float] = None


@router.post("/adjust-plan")
async def adjust_plan_for_readiness(request: PlanAdjustmentRequest):
    """
    Dynamically adjust a plan based on current health/readiness data.
    
    Adjustment rules:
    - Body Battery < 30: Reduce intensity 50%, add rest days
    - Body Battery 30-50: Reduce intensity 25%
    - Body Battery > 70: Can increase intensity 10%
    - Sleep Score < 50: Prioritize recovery
    - High stress (>60): Favor easy workouts
    """
    try:
        plan = request.plan_data
        adjustments_made = []
        
        # Calculate adjustment factor
        adjustment_factor = 1.0
        needs_more_recovery = False
        can_push_harder = False
        
        # Body Battery assessment
        if request.body_battery < 30:
            adjustment_factor = 0.5
            needs_more_recovery = True
            adjustments_made.append("Body Battery critically low - reducing intensity 50%")
        elif request.body_battery < 50:
            adjustment_factor = 0.75
            adjustments_made.append("Body Battery low - reducing intensity 25%")
        elif request.body_battery > 70:
            can_push_harder = True
            adjustment_factor = 1.1
            adjustments_made.append("Body Battery high - can increase intensity 10%")
        
        # Sleep assessment
        if request.sleep_score and request.sleep_score < 50:
            adjustment_factor *= 0.9
            needs_more_recovery = True
            adjustments_made.append("Sleep score low - prioritizing recovery")
        
        # Stress assessment
        if request.stress_level and request.stress_level > 60:
            adjustment_factor *= 0.85
            adjustments_made.append("High stress detected - favoring easy workouts")
        
        # Apply adjustments to workouts
        adjusted_workouts = []
        workouts = plan.get("workouts", [])
        
        for workout in workouts:
            adjusted = workout.copy()
            
            if needs_more_recovery and workout.get("intensity") == "high":
                # Convert high intensity to moderate
                adjusted["intensity"] = "moderate"
                adjusted["original_intensity"] = "high"
                adjusted["adjustment_reason"] = "Reduced for recovery"
                if adjusted.get("duration_minutes"):
                    adjusted["duration_minutes"] = int(adjusted["duration_minutes"] * 0.8)
            
            elif can_push_harder and workout.get("intensity") == "moderate":
                # Can optionally increase
                adjusted["can_intensify"] = True
                adjusted["suggestion"] = "Body is ready - can push harder if feeling good"
            
            # Adjust duration based on factor
            if adjusted.get("duration_minutes") and adjustment_factor != 1.0:
                original_duration = adjusted["duration_minutes"]
                adjusted["duration_minutes"] = int(original_duration * adjustment_factor)
                if adjusted["duration_minutes"] != original_duration:
                    adjusted["duration_adjusted"] = True
            
            adjusted_workouts.append(adjusted)
        
        # Build response
        adjusted_plan = plan.copy()
        adjusted_plan["workouts"] = adjusted_workouts
        adjusted_plan["adjustment_applied"] = True
        adjusted_plan["adjustment_factor"] = adjustment_factor
        adjusted_plan["adjustments"] = adjustments_made
        adjusted_plan["readiness_summary"] = {
            "body_battery": request.body_battery,
            "sleep_score": request.sleep_score,
            "stress_level": request.stress_level,
            "recommendation": "Recovery focus" if needs_more_recovery else "Ready to train" if can_push_harder else "Normal training"
        }
        
        return {
            "success": True,
            "adjusted_plan": adjusted_plan,
            "adjustments_made": adjustments_made,
            "adjustment_factor": adjustment_factor
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
