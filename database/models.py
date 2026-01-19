"""SQLAlchemy database models for caching Garmin data."""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Boolean, 
    Text, JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Activity(Base):
    """Model for storing activity/workout data."""
    
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    garmin_id = Column(String(50), unique=True, nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, index=True)
    activity_name = Column(String(255))
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    distance_meters = Column(Float)
    calories = Column(Integer)
    avg_hr = Column(Integer)
    max_hr = Column(Integer)
    avg_speed = Column(Float)
    max_speed = Column(Float)
    elevation_gain = Column(Float)
    elevation_loss = Column(Float)
    avg_cadence = Column(Float)
    steps = Column(Integer)
    training_effect_aerobic = Column(Float)
    training_effect_anaerobic = Column(Float)
    vo2_max = Column(Float)
    raw_data = Column(JSON)  # Store complete raw response
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_activities_date_type', 'start_time', 'activity_type'),
    )
    
    def __repr__(self):
        return f"<Activity(id={self.id}, type={self.activity_type}, date={self.start_time})>"


class HealthStats(Base):
    """Model for storing daily health statistics."""
    
    __tablename__ = "health_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    
    # Steps and activity
    steps = Column(Integer)
    steps_goal = Column(Integer)
    distance_meters = Column(Float)
    active_calories = Column(Integer)
    total_calories = Column(Integer)
    active_minutes = Column(Integer)
    sedentary_minutes = Column(Integer)
    floors_climbed = Column(Integer)
    
    # Heart rate
    resting_hr = Column(Integer)
    min_hr = Column(Integer)
    max_hr = Column(Integer)
    avg_hr = Column(Integer)
    hr_zone_1_minutes = Column(Integer)
    hr_zone_2_minutes = Column(Integer)
    hr_zone_3_minutes = Column(Integer)
    hr_zone_4_minutes = Column(Integer)
    hr_zone_5_minutes = Column(Integer)
    
    # Stress and body battery
    avg_stress = Column(Integer)
    max_stress = Column(Integer)
    stress_duration = Column(Integer)
    rest_stress_duration = Column(Integer)
    body_battery_charged = Column(Integer)
    body_battery_drained = Column(Integer)
    body_battery_high = Column(Integer)
    body_battery_low = Column(Integer)
    
    # Respiration
    avg_respiration = Column(Float)
    min_respiration = Column(Float)
    max_respiration = Column(Float)
    
    # SpO2
    avg_spo2 = Column(Float)
    min_spo2 = Column(Float)
    
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<HealthStats(date={self.date}, steps={self.steps})>"


class SleepData(Base):
    """Model for storing sleep data."""
    
    __tablename__ = "sleep_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    
    # Sleep times
    sleep_start = Column(DateTime)
    sleep_end = Column(DateTime)
    total_sleep_seconds = Column(Integer)
    
    # Sleep stages (in seconds)
    deep_sleep_seconds = Column(Integer)
    light_sleep_seconds = Column(Integer)
    rem_sleep_seconds = Column(Integer)
    awake_seconds = Column(Integer)
    
    # Sleep quality
    sleep_score = Column(Integer)
    sleep_quality = Column(String(20))
    
    # Additional metrics
    avg_hr = Column(Integer)
    min_hr = Column(Integer)
    max_hr = Column(Integer)
    avg_hrv = Column(Float)
    avg_respiration = Column(Float)
    avg_spo2 = Column(Float)
    
    # Sleep levels detail
    sleep_levels = Column(JSON)
    
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SleepData(date={self.date}, score={self.sleep_score})>"


class WorkoutPlan(Base):
    """Model for storing AI-generated workout plans."""
    
    __tablename__ = "workout_plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_name = Column(String(255), nullable=False)
    plan_type = Column(String(50))  # weekly, monthly, custom
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    
    # Goals
    primary_goal = Column(String(100))
    target_days_per_week = Column(Integer)
    
    # Plan content
    plan_summary = Column(Text)
    plan_data = Column(JSON, nullable=False)  # Full plan JSON
    
    # Status
    is_active = Column(Boolean, default=True)
    completed_workouts = Column(Integer, default=0)
    total_workouts = Column(Integer)
    
    # AI generation info
    ai_model = Column(String(50))
    generation_prompt = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scheduled_workouts = relationship("ScheduledWorkout", back_populates="plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WorkoutPlan(id={self.id}, name={self.plan_name})>"


class ScheduledWorkout(Base):
    """Model for individual scheduled workouts within a plan."""
    
    __tablename__ = "scheduled_workouts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=False)
    
    scheduled_date = Column(Date, nullable=False, index=True)
    workout_type = Column(String(50), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    duration_minutes = Column(Integer)
    intensity = Column(String(20))
    exercises = Column(JSON)
    target_hr_zone = Column(String(20))
    estimated_calories = Column(Integer)
    
    # Completion tracking
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    actual_duration_minutes = Column(Integer)
    actual_calories = Column(Integer)
    linked_activity_id = Column(String(50))  # Link to actual Garmin activity
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plan = relationship("WorkoutPlan", back_populates="scheduled_workouts")
    
    __table_args__ = (
        Index('ix_scheduled_workouts_date', 'scheduled_date', 'plan_id'),
    )
    
    def __repr__(self):
        return f"<ScheduledWorkout(date={self.scheduled_date}, type={self.workout_type})>"


class UserGoal(Base):
    """Model for storing user fitness goals."""
    
    __tablename__ = "user_goals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50), index=True)  # activity, sleep, strength, cardio, weight
    
    # Goal metrics
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0)
    unit = Column(String(50))
    timeframe = Column(String(20))  # daily, weekly, monthly
    
    # Progress tracking
    start_date = Column(Date, nullable=False)
    target_date = Column(Date)
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    
    # AI recommendation info
    ai_recommended = Column(Boolean, default=False)
    difficulty = Column(String(20))
    priority = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_user_goals_active', 'is_active', 'category'),
    )
    
    def __repr__(self):
        return f"<UserGoal(name={self.name}, target={self.target_value} {self.unit})>"
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage towards goal."""
        if self.target_value == 0:
            return 0
        return min((self.current_value / self.target_value) * 100, 100)


class ChatHistory(Base):
    """Model for storing AI chat history."""
    
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    
    # Context used for the response
    context_data = Column(JSON)
    
    # Token usage
    tokens_used = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ChatHistory(id={self.id}, role={self.role})>"


class HealthInsight(Base):
    """Model for storing generated health insights."""
    
    __tablename__ = "health_insights"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    insight_date = Column(Date, nullable=False, index=True)
    period = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Scores
    overall_score = Column(Integer)
    sleep_score = Column(Integer)
    activity_score = Column(Integer)
    recovery_score = Column(Integer)
    
    # Content
    summary = Column(Text)
    insights_data = Column(JSON, nullable=False)
    
    # Generation info
    ai_model = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('insight_date', 'period', name='uq_insight_date_period'),
    )
    
    def __repr__(self):
        return f"<HealthInsight(date={self.insight_date}, period={self.period})>"
