"""Workouts API Router - Workout Plans and Scheduling."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import DatabaseManager

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


class GarminWorkoutCreate(BaseModel):
    """Workout structure to send to Garmin."""
    title: str
    description: str
    type: str  # running, cycling, strength, etc.
    duration_minutes: int
    steps: Optional[List[Dict[str, Any]]] = None
    target_hr_zone: Optional[str] = None


@router.post("/send-to-garmin")
async def send_workout_to_garmin(workout: GarminWorkoutCreate):
    """
    Send a workout to Garmin Connect.
    Note: This requires Garmin workout API access which has limited availability.
    Currently returns a placeholder response.
    """
    try:
        # TODO: Implement actual Garmin workout upload
        # The Garmin Connect API for creating workouts is limited and requires
        # specific API access. For now, we return a helpful message.
        
        # Build workout structure for Garmin
        garmin_workout = {
            "workoutName": workout.title,
            "description": workout.description,
            "sport": workout.type.upper() if workout.type else "RUNNING",
            "estimatedDurationInSecs": workout.duration_minutes * 60,
            "workoutSegments": [],
        }
        
        # Convert steps to Garmin format
        if workout.steps:
            for step in workout.steps:
                segment = {
                    "segmentOrder": len(garmin_workout["workoutSegments"]) + 1,
                    "sportType": workout.type.upper() if workout.type else "RUNNING",
                    "workoutSteps": [{
                        "type": step.get("type", "interval").upper(),
                        "stepOrder": 1,
                        "description": step.get("description", ""),
                        "durationType": "TIME",
                        "durationValue": step.get("duration_minutes", 5) * 60000,  # milliseconds
                    }]
                }
                
                # Add pace target if available
                if step.get("target_pace_min"):
                    # Convert pace to speed (m/s) for Garmin
                    pace_parts = step["target_pace_min"].split(":")
                    if len(pace_parts) == 2:
                        total_seconds = int(pace_parts[0]) * 60 + int(pace_parts[1])
                        speed_ms = 1000 / total_seconds
                        segment["workoutSteps"][0]["targetType"] = "SPEED"
                        segment["workoutSteps"][0]["targetValueLow"] = speed_ms * 0.95
                        segment["workoutSteps"][0]["targetValueHigh"] = speed_ms * 1.05
                
                garmin_workout["workoutSegments"].append(segment)
        
        return {
            "success": True,
            "message": f"Workout '{workout.title}' prepared for Garmin",
            "note": "Direct Garmin upload requires additional API access. For now, you can manually create this workout in Garmin Connect.",
            "workout_data": garmin_workout,
            "manual_creation_url": "https://connect.garmin.com/modern/workouts"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
