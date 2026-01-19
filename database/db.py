"""Database initialization and session management."""

from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Generator
import json

from sqlalchemy import create_engine, select, func, and_, delete
from sqlalchemy.orm import sessionmaker, Session

from config import settings
from .models import (
    Base, Activity, HealthStats, SleepData, 
    WorkoutPlan, ScheduledWorkout, UserGoal, 
    ChatHistory, HealthInsight
)

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            echo=settings.app_debug,
            future=True
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    return _SessionLocal


def init_db():
    """Initialize the database, creating all tables if they don't exist."""
    engine = get_engine()
    # checkfirst=True is default, but be explicit to avoid "table exists" errors
    Base.metadata.create_all(bind=engine, checkfirst=True)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DatabaseManager:
    """High-level database operations manager."""
    
    # ==================== Activities ====================
    
    @staticmethod
    def save_activity(activity_data: Dict[str, Any]) -> Optional[Activity]:
        """Save or update an activity."""
        with get_db_session() as session:
            garmin_id = str(activity_data.get("activityId", ""))
            if not garmin_id:
                return None
            
            # Check if exists
            existing = session.execute(
                select(Activity).where(Activity.garmin_id == garmin_id)
            ).scalar_one_or_none()
            
            if existing:
                activity = existing
            else:
                activity = Activity(garmin_id=garmin_id)
                session.add(activity)
            
            # Map fields
            activity.activity_type = activity_data.get("activityType", {}).get("typeKey", "other")
            activity.activity_name = activity_data.get("activityName", "")
            activity.start_time = _parse_datetime(activity_data.get("startTimeLocal"))
            activity.duration_seconds = int(activity_data.get("duration", 0))
            activity.distance_meters = activity_data.get("distance")
            activity.calories = activity_data.get("calories")
            activity.avg_hr = activity_data.get("averageHR")
            activity.max_hr = activity_data.get("maxHR")
            activity.avg_speed = activity_data.get("averageSpeed")
            activity.max_speed = activity_data.get("maxSpeed")
            activity.elevation_gain = activity_data.get("elevationGain")
            activity.elevation_loss = activity_data.get("elevationLoss")
            activity.steps = activity_data.get("steps")
            activity.training_effect_aerobic = activity_data.get("aerobicTrainingEffect")
            activity.training_effect_anaerobic = activity_data.get("anaerobicTrainingEffect")
            activity.vo2_max = activity_data.get("vO2MaxValue")
            activity.raw_data = activity_data
            
            session.commit()
            return activity
    
    @staticmethod
    def save_activities(activities: List[Dict[str, Any]]) -> int:
        """Bulk save activities. Returns count of saved activities."""
        count = 0
        for activity_data in activities:
            if DatabaseManager.save_activity(activity_data):
                count += 1
        return count
    
    @staticmethod
    def get_activities(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        activity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Activity]:
        """Get activities with optional filters."""
        with get_db_session() as session:
            query = select(Activity)
            
            conditions = []
            if start_date:
                conditions.append(Activity.start_time >= datetime.combine(start_date, datetime.min.time()))
            if end_date:
                conditions.append(Activity.start_time <= datetime.combine(end_date, datetime.max.time()))
            if activity_type:
                conditions.append(Activity.activity_type == activity_type)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(Activity.start_time.desc()).limit(limit)
            
            result = session.execute(query).scalars().all()
            return list(result)
    
    @staticmethod
    def get_activity_stats(days: int = 30) -> Dict[str, Any]:
        """Get aggregated activity statistics."""
        with get_db_session() as session:
            start_date = datetime.now() - timedelta(days=days)
            
            result = session.execute(
                select(
                    func.count(Activity.id).label("total_activities"),
                    func.sum(Activity.duration_seconds).label("total_duration"),
                    func.sum(Activity.calories).label("total_calories"),
                    func.sum(Activity.distance_meters).label("total_distance"),
                    func.avg(Activity.avg_hr).label("avg_hr"),
                )
                .where(Activity.start_time >= start_date)
            ).first()
            
            # Activity type breakdown
            type_counts = session.execute(
                select(Activity.activity_type, func.count(Activity.id))
                .where(Activity.start_time >= start_date)
                .group_by(Activity.activity_type)
            ).all()
            
            return {
                "total_activities": result.total_activities or 0,
                "total_duration_minutes": (result.total_duration or 0) / 60,
                "total_calories": result.total_calories or 0,
                "total_distance_km": (result.total_distance or 0) / 1000,
                "avg_hr": round(result.avg_hr or 0),
                "activity_types": {t: c for t, c in type_counts}
            }
    
    # ==================== Health Stats ====================
    
    @staticmethod
    def save_health_stats(stats_date: date, stats_data: Dict[str, Any]) -> HealthStats:
        """Save or update daily health stats."""
        with get_db_session() as session:
            existing = session.execute(
                select(HealthStats).where(HealthStats.date == stats_date)
            ).scalar_one_or_none()
            
            if existing:
                stats = existing
            else:
                stats = HealthStats(date=stats_date)
                session.add(stats)
            
            # Map fields from Garmin API response
            stats.steps = stats_data.get("totalSteps")
            stats.steps_goal = stats_data.get("dailyStepGoal")
            stats.distance_meters = stats_data.get("totalDistanceMeters")
            stats.active_calories = stats_data.get("activeKilocalories")
            stats.total_calories = stats_data.get("totalKilocalories")
            stats.active_minutes = stats_data.get("highlyActiveSeconds", 0) // 60 + stats_data.get("activeSeconds", 0) // 60
            stats.sedentary_minutes = stats_data.get("sedentarySeconds", 0) // 60
            stats.floors_climbed = stats_data.get("floorsAscended")
            
            stats.resting_hr = stats_data.get("restingHeartRate")
            stats.min_hr = stats_data.get("minHeartRate")
            stats.max_hr = stats_data.get("maxHeartRate")
            
            stats.avg_stress = stats_data.get("averageStressLevel")
            stats.max_stress = stats_data.get("maxStressLevel")
            
            stats.avg_respiration = stats_data.get("avgWakingRespirationValue")
            stats.avg_spo2 = stats_data.get("averageSpo2")
            
            stats.raw_data = stats_data
            
            session.commit()
            return stats
    
    @staticmethod
    def get_health_stats(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[HealthStats]:
        """Get health stats for date range."""
        with get_db_session() as session:
            query = select(HealthStats)
            
            conditions = []
            if start_date:
                conditions.append(HealthStats.date >= start_date)
            if end_date:
                conditions.append(HealthStats.date <= end_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(HealthStats.date.desc())
            
            result = session.execute(query).scalars().all()
            return list(result)
    
    @staticmethod
    def get_health_summary(days: int = 7) -> Dict[str, Any]:
        """Get aggregated health summary."""
        with get_db_session() as session:
            start_date = date.today() - timedelta(days=days)
            
            result = session.execute(
                select(
                    func.avg(HealthStats.steps).label("avg_steps"),
                    func.sum(HealthStats.steps).label("total_steps"),
                    func.avg(HealthStats.resting_hr).label("avg_resting_hr"),
                    func.avg(HealthStats.avg_stress).label("avg_stress"),
                    func.sum(HealthStats.active_minutes).label("total_active_minutes"),
                    func.sum(HealthStats.total_calories).label("total_calories"),
                )
                .where(HealthStats.date >= start_date)
            ).first()
            
            return {
                "avg_steps": int(result.avg_steps or 0),
                "total_steps": int(result.total_steps or 0),
                "avg_resting_hr": int(result.avg_resting_hr or 0),
                "avg_stress": int(result.avg_stress or 0),
                "total_active_minutes": int(result.total_active_minutes or 0),
                "total_calories": int(result.total_calories or 0),
            }
    
    # ==================== Sleep Data ====================
    
    @staticmethod
    def save_sleep_data(sleep_date: date, sleep_data: Dict[str, Any]) -> SleepData:
        """Save or update sleep data."""
        with get_db_session() as session:
            existing = session.execute(
                select(SleepData).where(SleepData.date == sleep_date)
            ).scalar_one_or_none()
            
            if existing:
                sleep = existing
            else:
                sleep = SleepData(date=sleep_date)
                session.add(sleep)
            
            # Parse sleep data
            daily_sleep = sleep_data.get("dailySleepDTO", {})
            
            sleep.sleep_start = _parse_datetime(daily_sleep.get("sleepStartTimestampLocal"))
            sleep.sleep_end = _parse_datetime(daily_sleep.get("sleepEndTimestampLocal"))
            sleep.total_sleep_seconds = daily_sleep.get("sleepTimeSeconds")
            
            sleep.deep_sleep_seconds = daily_sleep.get("deepSleepSeconds")
            sleep.light_sleep_seconds = daily_sleep.get("lightSleepSeconds")
            sleep.rem_sleep_seconds = daily_sleep.get("remSleepSeconds")
            sleep.awake_seconds = daily_sleep.get("awakeSleepSeconds")
            
            sleep.sleep_score = sleep_data.get("sleepScores", {}).get("overall", {}).get("value")
            
            sleep.avg_hr = daily_sleep.get("averageHeartRate")
            sleep.min_hr = daily_sleep.get("lowestHeartRate")
            sleep.max_hr = daily_sleep.get("highestHeartRate")
            sleep.avg_hrv = daily_sleep.get("averageHRV")
            sleep.avg_respiration = daily_sleep.get("averageRespirationValue")
            sleep.avg_spo2 = daily_sleep.get("averageSPO2Value")
            
            sleep.sleep_levels = sleep_data.get("sleepLevels")
            sleep.raw_data = sleep_data
            
            session.commit()
            return sleep
    
    @staticmethod
    def get_sleep_data(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[SleepData]:
        """Get sleep data for date range."""
        with get_db_session() as session:
            query = select(SleepData)
            
            conditions = []
            if start_date:
                conditions.append(SleepData.date >= start_date)
            if end_date:
                conditions.append(SleepData.date <= end_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(SleepData.date.desc())
            
            result = session.execute(query).scalars().all()
            return list(result)
    
    @staticmethod
    def get_sleep_summary(days: int = 7) -> Dict[str, Any]:
        """Get aggregated sleep summary."""
        with get_db_session() as session:
            start_date = date.today() - timedelta(days=days)
            
            result = session.execute(
                select(
                    func.avg(SleepData.total_sleep_seconds).label("avg_sleep_seconds"),
                    func.avg(SleepData.sleep_score).label("avg_sleep_score"),
                    func.avg(SleepData.deep_sleep_seconds).label("avg_deep"),
                    func.avg(SleepData.rem_sleep_seconds).label("avg_rem"),
                    func.avg(SleepData.avg_hrv).label("avg_hrv"),
                )
                .where(SleepData.date >= start_date)
            ).first()
            
            avg_hours = (result.avg_sleep_seconds or 0) / 3600
            
            return {
                "avg_sleep_hours": round(avg_hours, 1),
                "avg_sleep_score": int(result.avg_sleep_score or 0),
                "avg_deep_hours": round((result.avg_deep or 0) / 3600, 1),
                "avg_rem_hours": round((result.avg_rem or 0) / 3600, 1),
                "avg_hrv": round(result.avg_hrv or 0, 1),
            }
    
    # ==================== Workout Plans ====================
    
    @staticmethod
    def save_workout_plan(plan_data: Dict[str, Any]) -> WorkoutPlan:
        """Save a new workout plan."""
        with get_db_session() as session:
            plan = WorkoutPlan(
                plan_name=plan_data.get("plan_name", "Workout Plan"),
                plan_type=plan_data.get("plan_type", "weekly"),
                start_date=_parse_date(plan_data.get("start_date")) or date.today(),
                end_date=_parse_date(plan_data.get("end_date")),
                primary_goal=plan_data.get("primary_goal"),
                target_days_per_week=plan_data.get("target_days_per_week"),
                plan_summary=plan_data.get("plan_summary"),
                plan_data=plan_data,
                total_workouts=plan_data.get("total_sessions", 0),
                ai_model=plan_data.get("ai_model"),
            )
            session.add(plan)
            session.flush()
            
            # Add scheduled workouts
            for day_data in plan_data.get("days", []):
                workout = ScheduledWorkout(
                    plan_id=plan.id,
                    scheduled_date=_parse_date(day_data.get("date")) or date.today(),
                    workout_type=day_data.get("workout_type", "other"),
                    title=day_data.get("title"),
                    description=day_data.get("description"),
                    duration_minutes=day_data.get("duration_minutes"),
                    intensity=day_data.get("intensity"),
                    exercises=day_data.get("exercises"),
                    target_hr_zone=day_data.get("target_hr_zone"),
                    estimated_calories=day_data.get("estimated_calories"),
                )
                session.add(workout)
            
            session.commit()
            return plan
    
    @staticmethod
    def get_active_plan() -> Optional[WorkoutPlan]:
        """Get the current active workout plan."""
        with get_db_session() as session:
            result = session.execute(
                select(WorkoutPlan)
                .where(WorkoutPlan.is_active == True)
                .order_by(WorkoutPlan.created_at.desc())
            ).scalar_one_or_none()
            return result
    
    @staticmethod
    def get_scheduled_workouts(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        plan_id: Optional[int] = None
    ) -> List[ScheduledWorkout]:
        """Get scheduled workouts for date range."""
        with get_db_session() as session:
            query = select(ScheduledWorkout)
            
            conditions = []
            if start_date:
                conditions.append(ScheduledWorkout.scheduled_date >= start_date)
            if end_date:
                conditions.append(ScheduledWorkout.scheduled_date <= end_date)
            if plan_id:
                conditions.append(ScheduledWorkout.plan_id == plan_id)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(ScheduledWorkout.scheduled_date)
            
            result = session.execute(query).scalars().all()
            return list(result)
    
    @staticmethod
    def complete_workout(workout_id: int, actual_data: Dict[str, Any]) -> bool:
        """Mark a scheduled workout as complete."""
        with get_db_session() as session:
            workout = session.get(ScheduledWorkout, workout_id)
            if workout:
                workout.is_completed = True
                workout.completed_at = datetime.utcnow()
                workout.actual_duration_minutes = actual_data.get("duration_minutes")
                workout.actual_calories = actual_data.get("calories")
                workout.linked_activity_id = actual_data.get("activity_id")
                workout.notes = actual_data.get("notes")
                
                # Update plan progress
                if workout.plan:
                    workout.plan.completed_workouts = (workout.plan.completed_workouts or 0) + 1
                
                session.commit()
                return True
            return False
    
    # ==================== User Goals ====================
    
    @staticmethod
    def save_goal(goal_data: Dict[str, Any]) -> UserGoal:
        """Save a new user goal."""
        with get_db_session() as session:
            goal = UserGoal(
                name=goal_data.get("name", "Goal"),
                description=goal_data.get("description"),
                category=goal_data.get("category"),
                target_value=goal_data.get("target_value", 0),
                current_value=goal_data.get("current_value", 0),
                unit=goal_data.get("unit"),
                timeframe=goal_data.get("timeframe"),
                start_date=_parse_date(goal_data.get("start_date")) or date.today(),
                target_date=_parse_date(goal_data.get("target_date")),
                ai_recommended=goal_data.get("ai_recommended", False),
                difficulty=goal_data.get("difficulty"),
                priority=goal_data.get("priority", 0),
            )
            session.add(goal)
            session.commit()
            return goal
    
    @staticmethod
    def get_active_goals() -> List[UserGoal]:
        """Get all active goals."""
        with get_db_session() as session:
            result = session.execute(
                select(UserGoal)
                .where(UserGoal.is_active == True)
                .order_by(UserGoal.priority.desc(), UserGoal.created_at)
            ).scalars().all()
            return list(result)
    
    @staticmethod
    def update_goal_progress(goal_id: int, current_value: float) -> bool:
        """Update goal progress."""
        with get_db_session() as session:
            goal = session.get(UserGoal, goal_id)
            if goal:
                goal.current_value = current_value
                if current_value >= goal.target_value:
                    goal.is_completed = True
                    goal.completed_at = datetime.utcnow()
                session.commit()
                return True
            return False
    
    # ==================== Chat History ====================
    
    @staticmethod
    def save_chat_message(
        session_id: str,
        role: str,
        content: str,
        context_data: Optional[Dict] = None
    ) -> ChatHistory:
        """Save a chat message."""
        with get_db_session() as session:
            message = ChatHistory(
                session_id=session_id,
                role=role,
                content=content,
                context_data=context_data,
            )
            session.add(message)
            session.commit()
            return message
    
    @staticmethod
    def get_chat_history(session_id: str, limit: int = 50) -> List[ChatHistory]:
        """Get chat history for a session."""
        with get_db_session() as session:
            result = session.execute(
                select(ChatHistory)
                .where(ChatHistory.session_id == session_id)
                .order_by(ChatHistory.created_at.desc())
                .limit(limit)
            ).scalars().all()
            return list(reversed(result))
    
    # ==================== Health Insights ====================
    
    @staticmethod
    def save_health_insight(insight_data: Dict[str, Any]) -> HealthInsight:
        """Save a health insight."""
        with get_db_session() as session:
            insight_date = _parse_date(insight_data.get("date")) or date.today()
            period = insight_data.get("period", "weekly")
            
            # Check if exists
            existing = session.execute(
                select(HealthInsight)
                .where(and_(
                    HealthInsight.insight_date == insight_date,
                    HealthInsight.period == period
                ))
            ).scalar_one_or_none()
            
            if existing:
                insight = existing
            else:
                insight = HealthInsight(insight_date=insight_date, period=period)
                session.add(insight)
            
            insight.overall_score = insight_data.get("overall_score")
            insight.summary = insight_data.get("overall_assessment")
            insight.insights_data = insight_data
            insight.ai_model = insight_data.get("ai_model")
            
            session.commit()
            return insight
    
    @staticmethod
    def get_latest_insight(period: str = "weekly") -> Optional[HealthInsight]:
        """Get the most recent health insight."""
        with get_db_session() as session:
            result = session.execute(
                select(HealthInsight)
                .where(HealthInsight.period == period)
                .order_by(HealthInsight.insight_date.desc())
            ).scalar_one_or_none()
            return result
    
    # ==================== Workout Plans ====================
    
    @staticmethod
    def save_workout_plan(
        plan_name: str,
        plan_type: str,
        start_date: date,
        end_date: date,
        primary_goal: str,
        plan_data: Dict[str, Any],
        ai_model: str = "gemini"
    ) -> Optional[int]:
        """Save a new workout plan."""
        with get_db_session() as session:
            plan = WorkoutPlan(
                plan_name=plan_name,
                plan_type=plan_type,
                start_date=start_date,
                end_date=end_date,
                primary_goal=primary_goal,
                plan_data=plan_data,
                plan_summary=plan_data.get("rationale") or plan_data.get("mesocycle_overview"),
                ai_model=ai_model,
                is_active=True,
                total_workouts=0,
                completed_workouts=0,
            )
            session.add(plan)
            session.commit()
            return plan.id
    
    @staticmethod
    def get_workout_plan(plan_id: int) -> Optional[WorkoutPlan]:
        """Get a workout plan by ID."""
        with get_db_session() as session:
            result = session.execute(
                select(WorkoutPlan).where(WorkoutPlan.id == plan_id)
            ).scalar_one_or_none()
            return result
    
    @staticmethod
    def get_active_workout_plans() -> List[WorkoutPlan]:
        """Get all active workout plans."""
        with get_db_session() as session:
            result = session.execute(
                select(WorkoutPlan)
                .where(WorkoutPlan.is_active == True)
                .order_by(WorkoutPlan.start_date.desc())
            ).scalars().all()
            return list(result)
    
    @staticmethod
    def delete_workout_plan(plan_id: int) -> bool:
        """Delete a workout plan and its scheduled workouts."""
        with get_db_session() as session:
            plan = session.execute(
                select(WorkoutPlan).where(WorkoutPlan.id == plan_id)
            ).scalar_one_or_none()
            
            if not plan:
                return False
            
            # Delete associated scheduled workouts
            session.execute(
                delete(ScheduledWorkout).where(ScheduledWorkout.plan_id == plan_id)
            )
            
            # Delete the plan
            session.delete(plan)
            session.commit()
            return True
    
    # ==================== Scheduled Workouts ====================
    
    @staticmethod
    def save_scheduled_workout(
        plan_id: int,
        scheduled_date: date,
        workout_type: str,
        title: str,
        description: str = "",
        duration_minutes: Optional[int] = None,
        intensity: str = "moderate",
        exercises: Optional[List] = None,
        target_hr_zone: Optional[str] = None,
    ) -> Optional[int]:
        """Save a scheduled workout."""
        with get_db_session() as session:
            workout = ScheduledWorkout(
                plan_id=plan_id,
                scheduled_date=scheduled_date,
                workout_type=workout_type,
                title=title,
                description=description,
                duration_minutes=duration_minutes,
                intensity=intensity,
                exercises=exercises or [],
                target_hr_zone=target_hr_zone,
                is_completed=False,
            )
            session.add(workout)
            
            # Update plan's total workouts count
            plan = session.execute(
                select(WorkoutPlan).where(WorkoutPlan.id == plan_id)
            ).scalar_one_or_none()
            if plan:
                plan.total_workouts = (plan.total_workouts or 0) + 1
            
            session.commit()
            return workout.id
    
    @staticmethod
    def get_scheduled_workouts(plan_id: int) -> List[ScheduledWorkout]:
        """Get all scheduled workouts for a plan."""
        with get_db_session() as session:
            result = session.execute(
                select(ScheduledWorkout)
                .where(ScheduledWorkout.plan_id == plan_id)
                .order_by(ScheduledWorkout.scheduled_date)
            ).scalars().all()
            return list(result)
    
    @staticmethod
    def get_scheduled_workout(workout_id: int) -> Optional[ScheduledWorkout]:
        """Get a scheduled workout by ID."""
        with get_db_session() as session:
            result = session.execute(
                select(ScheduledWorkout).where(ScheduledWorkout.id == workout_id)
            ).scalar_one_or_none()
            return result
    
    @staticmethod
    def get_scheduled_workouts_by_date(target_date: date) -> List[ScheduledWorkout]:
        """Get all scheduled workouts for a specific date."""
        with get_db_session() as session:
            result = session.execute(
                select(ScheduledWorkout)
                .join(WorkoutPlan)
                .where(and_(
                    ScheduledWorkout.scheduled_date == target_date,
                    WorkoutPlan.is_active == True
                ))
            ).scalars().all()
            return list(result)
    
    @staticmethod
    def complete_scheduled_workout(
        workout_id: int,
        activity_id: str,
        actual_duration: Optional[float] = None,
        actual_calories: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Mark a scheduled workout as complete with linked activity."""
        with get_db_session() as session:
            workout = session.execute(
                select(ScheduledWorkout).where(ScheduledWorkout.id == workout_id)
            ).scalar_one_or_none()
            
            if not workout:
                return False
            
            workout.is_completed = True
            workout.completed_at = datetime.now()
            workout.linked_activity_id = activity_id
            workout.actual_duration_minutes = int(actual_duration) if actual_duration else None
            workout.actual_calories = actual_calories
            workout.notes = notes
            
            # Update plan's completed workouts count
            plan = session.execute(
                select(WorkoutPlan).where(WorkoutPlan.id == workout.plan_id)
            ).scalar_one_or_none()
            if plan:
                plan.completed_workouts = (plan.completed_workouts or 0) + 1
            
            session.commit()
            return True


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000)  # Garmin uses milliseconds
    return None


def _parse_date(value: Any) -> Optional[date]:
    """Parse date from various formats."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
    return None
