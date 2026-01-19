"""Application configuration using Pydantic settings."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Garmin Connect credentials
    garmin_email: str = Field(default="", description="Garmin Connect email")
    garmin_password: str = Field(default="", description="Garmin Connect password")
    garmin_token_path: str = Field(
        default=str(Path.home() / ".garminconnect"),
        description="Path to store Garmin OAuth tokens"
    )
    
    # Google Gemini API
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model to use")
    
    # Database settings
    database_url: str = Field(
        default="sqlite:///garmin_data.db",
        description="SQLAlchemy database URL"
    )
    
    # App settings
    app_debug: bool = Field(default=False, description="Enable debug mode")
    app_name: str = Field(default="OrkTrack", description="Application name")
    
    # Data fetching settings
    default_days_to_fetch: int = Field(default=30, description="Default number of days to fetch")
    max_days_to_fetch: int = Field(default=365, description="Maximum days to fetch at once")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Activity type mappings for display
ACTIVITY_TYPES = {
    "running": "🏃 Running",
    "cycling": "🚴 Cycling",
    "swimming": "🏊 Swimming",
    "walking": "🚶 Walking",
    "hiking": "🥾 Hiking",
    "strength_training": "💪 Strength Training",
    "yoga": "🧘 Yoga",
    "other": "🏋️ Other",
}

# Heart rate zones (percentage of max HR)
HR_ZONES = {
    "zone1": {"name": "Recovery", "min": 50, "max": 60, "color": "#3498db"},
    "zone2": {"name": "Aerobic", "min": 60, "max": 70, "color": "#2ecc71"},
    "zone3": {"name": "Tempo", "min": 70, "max": 80, "color": "#f1c40f"},
    "zone4": {"name": "Threshold", "min": 80, "max": 90, "color": "#e67e22"},
    "zone5": {"name": "Anaerobic", "min": 90, "max": 100, "color": "#e74c3c"},
}

# Sleep stage colors
SLEEP_STAGES = {
    "deep": {"name": "Deep Sleep", "color": "#1a237e"},
    "light": {"name": "Light Sleep", "color": "#5c6bc0"},
    "rem": {"name": "REM Sleep", "color": "#7e57c2"},
    "awake": {"name": "Awake", "color": "#ef5350"},
}

# Chart color palette
CHART_COLORS = {
    "primary": "#6366f1",
    "secondary": "#22c55e",
    "accent": "#f59e0b",
    "danger": "#ef4444",
    "info": "#3b82f6",
    "success": "#10b981",
    "warning": "#f59e0b",
    "muted": "#6b7280",
}
