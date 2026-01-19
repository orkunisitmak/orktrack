"""Data processing utilities for transforming Garmin data."""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple


class DataProcessor:
    """Utility class for processing and transforming Garmin data."""
    
    @staticmethod
    def activities_to_dataframe(activities: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert activity list to pandas DataFrame.
        
        Args:
            activities: List of activity dictionaries from Garmin API
            
        Returns:
            Processed DataFrame with activity data
        """
        if not activities:
            return pd.DataFrame()
        
        records = []
        for activity in activities:
            record = {
                "activity_id": activity.get("activityId"),
                "activity_type": activity.get("activityType", {}).get("typeKey", "other"),
                "activity_name": activity.get("activityName", ""),
                "start_time": pd.to_datetime(activity.get("startTimeLocal")),
                "duration_minutes": (activity.get("duration", 0) or 0) / 60,
                "distance_km": (activity.get("distance", 0) or 0) / 1000,
                "calories": activity.get("calories", 0) or 0,
                "avg_hr": activity.get("averageHR"),
                "max_hr": activity.get("maxHR"),
                "avg_speed_kmh": ((activity.get("averageSpeed", 0) or 0) * 3.6),
                "max_speed_kmh": ((activity.get("maxSpeed", 0) or 0) * 3.6),
                "elevation_gain": activity.get("elevationGain", 0) or 0,
                "steps": activity.get("steps"),
                "training_effect": activity.get("aerobicTrainingEffect"),
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        if not df.empty and "start_time" in df.columns:
            df["date"] = df["start_time"].dt.date
            df["day_of_week"] = df["start_time"].dt.day_name()
            df["hour"] = df["start_time"].dt.hour
        
        return df
    
    @staticmethod
    def health_stats_to_dataframe(stats_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert health stats list to pandas DataFrame.
        
        Args:
            stats_list: List of daily stats dictionaries
            
        Returns:
            Processed DataFrame with health stats
        """
        if not stats_list:
            return pd.DataFrame()
        
        records = []
        for stats in stats_list:
            record = {
                "date": pd.to_datetime(stats.get("date", stats.get("calendarDate"))),
                "steps": stats.get("totalSteps", 0) or 0,
                "steps_goal": stats.get("dailyStepGoal", 10000),
                "distance_km": (stats.get("totalDistanceMeters", 0) or 0) / 1000,
                "calories": stats.get("totalKilocalories", 0) or 0,
                "active_calories": stats.get("activeKilocalories", 0) or 0,
                "active_minutes": (
                    (stats.get("highlyActiveSeconds", 0) or 0) + 
                    (stats.get("activeSeconds", 0) or 0)
                ) // 60,
                "sedentary_minutes": (stats.get("sedentarySeconds", 0) or 0) // 60,
                "resting_hr": stats.get("restingHeartRate"),
                "min_hr": stats.get("minHeartRate"),
                "max_hr": stats.get("maxHeartRate"),
                "avg_stress": stats.get("averageStressLevel"),
                "floors": stats.get("floorsAscended", 0) or 0,
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df["steps_pct"] = (df["steps"] / df["steps_goal"] * 100).clip(0, 200)
        
        return df
    
    @staticmethod
    def sleep_to_dataframe(sleep_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert sleep data list to pandas DataFrame.
        
        Args:
            sleep_list: List of sleep data dictionaries
            
        Returns:
            Processed DataFrame with sleep data
        """
        if not sleep_list:
            return pd.DataFrame()
        
        records = []
        for sleep in sleep_list:
            daily = sleep.get("dailySleepDTO", {})
            scores = sleep.get("sleepScores", {})
            
            total_seconds = daily.get("sleepTimeSeconds", 0) or 0
            deep_seconds = daily.get("deepSleepSeconds", 0) or 0
            light_seconds = daily.get("lightSleepSeconds", 0) or 0
            rem_seconds = daily.get("remSleepSeconds", 0) or 0
            awake_seconds = daily.get("awakeSleepSeconds", 0) or 0
            
            record = {
                "date": pd.to_datetime(sleep.get("date", daily.get("calendarDate"))),
                "total_hours": total_seconds / 3600,
                "deep": deep_seconds / 3600,
                "light": light_seconds / 3600,
                "rem": rem_seconds / 3600,
                "awake": awake_seconds / 3600,
                "sleep_score": scores.get("overall", {}).get("value"),
                "avg_hr": daily.get("averageHeartRate"),
                "min_hr": daily.get("lowestHeartRate"),
                "hrv": daily.get("averageHRV"),
                "respiration": daily.get("averageRespirationValue"),
                "spo2": daily.get("averageSPO2Value"),
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
        
        return df
    
    @staticmethod
    def calculate_trends(
        current_data: pd.DataFrame,
        previous_data: pd.DataFrame,
        metrics: List[str]
    ) -> Dict[str, float]:
        """
        Calculate percentage changes between two periods.
        
        Args:
            current_data: Current period DataFrame
            previous_data: Previous period DataFrame
            metrics: List of metric column names to compare
            
        Returns:
            Dictionary of metric changes
        """
        trends = {}
        
        for metric in metrics:
            if metric in current_data.columns and metric in previous_data.columns:
                current_avg = current_data[metric].mean()
                previous_avg = previous_data[metric].mean()
                
                if previous_avg and previous_avg != 0:
                    change = ((current_avg - previous_avg) / previous_avg) * 100
                    trends[f"{metric}_change"] = round(change, 1)
                else:
                    trends[f"{metric}_change"] = 0
        
        return trends
    
    @staticmethod
    def aggregate_by_period(
        df: pd.DataFrame,
        period: str = "W",
        agg_config: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Aggregate data by time period.
        
        Args:
            df: Input DataFrame with 'date' column
            period: Pandas period string ('D', 'W', 'M')
            agg_config: Column aggregation configuration
            
        Returns:
            Aggregated DataFrame
        """
        if df.empty or "date" not in df.columns:
            return df
        
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        
        if agg_config is None:
            # Default aggregations
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            agg_config = {col: "mean" for col in numeric_cols}
            
            # Override specific columns
            for col in ["steps", "calories", "distance_km", "active_minutes"]:
                if col in agg_config:
                    agg_config[col] = "sum"
        
        return df.resample(period).agg(agg_config).reset_index()
    
    @staticmethod
    def calculate_rolling_averages(
        df: pd.DataFrame,
        columns: List[str],
        windows: List[int] = [7, 14, 30]
    ) -> pd.DataFrame:
        """
        Add rolling average columns.
        
        Args:
            df: Input DataFrame
            columns: Columns to calculate rolling averages for
            windows: List of window sizes
            
        Returns:
            DataFrame with additional rolling average columns
        """
        df = df.copy()
        
        for col in columns:
            if col in df.columns:
                for window in windows:
                    df[f"{col}_{window}d_avg"] = df[col].rolling(
                        window=window, min_periods=1
                    ).mean()
        
        return df
    
    @staticmethod
    def get_activity_summary(activities_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate activity summary statistics.
        
        Args:
            activities_df: Activities DataFrame
            
        Returns:
            Summary dictionary
        """
        if activities_df.empty:
            return {
                "total_activities": 0,
                "total_duration_hours": 0,
                "total_distance_km": 0,
                "total_calories": 0,
                "activity_types": {},
                "avg_duration": 0,
                "avg_hr": 0,
            }
        
        return {
            "total_activities": len(activities_df),
            "total_duration_hours": round(activities_df["duration_minutes"].sum() / 60, 1),
            "total_distance_km": round(activities_df["distance_km"].sum(), 1),
            "total_calories": int(activities_df["calories"].sum()),
            "activity_types": activities_df["activity_type"].value_counts().to_dict(),
            "avg_duration": round(activities_df["duration_minutes"].mean(), 1),
            "avg_hr": round(activities_df["avg_hr"].mean()) if activities_df["avg_hr"].notna().any() else 0,
            "longest_activity": round(activities_df["duration_minutes"].max(), 1),
            "most_calories": int(activities_df["calories"].max()),
        }
    
    @staticmethod
    def get_weekly_summary(
        stats_df: pd.DataFrame,
        sleep_df: pd.DataFrame,
        activities_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive weekly summary.
        
        Args:
            stats_df: Health stats DataFrame
            sleep_df: Sleep DataFrame
            activities_df: Activities DataFrame
            
        Returns:
            Weekly summary dictionary
        """
        summary = {
            "period": "week",
            "start_date": None,
            "end_date": None,
        }
        
        # Health stats summary
        if not stats_df.empty:
            summary["start_date"] = stats_df["date"].min()
            summary["end_date"] = stats_df["date"].max()
            summary["avg_steps"] = int(stats_df["steps"].mean())
            summary["total_steps"] = int(stats_df["steps"].sum())
            summary["avg_active_minutes"] = int(stats_df["active_minutes"].mean())
            summary["total_active_minutes"] = int(stats_df["active_minutes"].sum())
            summary["avg_resting_hr"] = round(stats_df["resting_hr"].mean(), 1) if stats_df["resting_hr"].notna().any() else None
            summary["avg_stress"] = round(stats_df["avg_stress"].mean(), 1) if stats_df["avg_stress"].notna().any() else None
            summary["total_calories"] = int(stats_df["calories"].sum())
        
        # Sleep summary
        if not sleep_df.empty:
            summary["avg_sleep_hours"] = round(sleep_df["total_hours"].mean(), 1)
            summary["avg_sleep_score"] = round(sleep_df["sleep_score"].mean()) if sleep_df["sleep_score"].notna().any() else None
            summary["avg_deep_sleep"] = round(sleep_df["deep"].mean(), 1)
            summary["avg_rem_sleep"] = round(sleep_df["rem"].mean(), 1)
        
        # Activity summary
        if not activities_df.empty:
            summary["total_workouts"] = len(activities_df)
            summary["total_workout_minutes"] = int(activities_df["duration_minutes"].sum())
            summary["total_workout_distance"] = round(activities_df["distance_km"].sum(), 1)
            summary["primary_activity"] = activities_df["activity_type"].mode().iloc[0] if len(activities_df) > 0 else None
        
        return summary
    
    @staticmethod
    def format_duration(minutes: float) -> str:
        """Format minutes as human-readable duration."""
        if minutes < 60:
            return f"{int(minutes)} min"
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if mins == 0:
            return f"{hours} hr"
        return f"{hours} hr {mins} min"
    
    @staticmethod
    def format_distance(km: float) -> str:
        """Format kilometers as human-readable distance."""
        if km < 1:
            return f"{int(km * 1000)} m"
        return f"{km:.2f} km"
    
    @staticmethod
    def format_pace(speed_kmh: float) -> str:
        """Convert speed (km/h) to pace (min/km)."""
        if speed_kmh <= 0:
            return "--:--"
        pace_mins = 60 / speed_kmh
        mins = int(pace_mins)
        secs = int((pace_mins - mins) * 60)
        return f"{mins}:{secs:02d}"
    
    @staticmethod
    def calculate_hr_zones(
        hr_data: List[int],
        max_hr: Optional[int] = None,
        age: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Calculate time spent in each HR zone.
        
        Args:
            hr_data: List of heart rate values
            max_hr: Maximum heart rate (estimated if not provided)
            age: User age for HR estimation
            
        Returns:
            Dictionary of minutes in each zone
        """
        if not hr_data:
            return {"zone1": 0, "zone2": 0, "zone3": 0, "zone4": 0, "zone5": 0}
        
        if max_hr is None:
            if age:
                max_hr = 220 - age
            else:
                max_hr = max(hr_data) if hr_data else 190
        
        zones = {
            "zone1": (0.5, 0.6),
            "zone2": (0.6, 0.7),
            "zone3": (0.7, 0.8),
            "zone4": (0.8, 0.9),
            "zone5": (0.9, 1.0),
        }
        
        zone_counts = {zone: 0 for zone in zones}
        
        for hr in hr_data:
            hr_pct = hr / max_hr
            for zone, (low, high) in zones.items():
                if low <= hr_pct < high:
                    zone_counts[zone] += 1
                    break
            else:
                if hr_pct >= 1.0:
                    zone_counts["zone5"] += 1
        
        # Convert counts to approximate minutes (assuming ~1 reading per second)
        return {zone: count // 60 for zone, count in zone_counts.items()}
    
    @staticmethod
    def detect_trends(
        series: pd.Series,
        window: int = 7
    ) -> Tuple[str, float]:
        """
        Detect trend direction in a time series.
        
        Args:
            series: Pandas Series with numeric values
            window: Window size for trend calculation
            
        Returns:
            Tuple of (trend direction, slope)
        """
        if len(series) < window:
            return ("neutral", 0.0)
        
        recent = series.tail(window)
        x = np.arange(len(recent))
        
        # Linear regression
        slope = np.polyfit(x, recent.fillna(recent.mean()), 1)[0]
        
        # Normalize slope relative to mean
        mean_val = recent.mean()
        if mean_val != 0:
            normalized_slope = (slope / mean_val) * 100
        else:
            normalized_slope = 0
        
        if normalized_slope > 2:
            return ("increasing", normalized_slope)
        elif normalized_slope < -2:
            return ("decreasing", normalized_slope)
        else:
            return ("stable", normalized_slope)
    
    @staticmethod
    def get_recommendations(
        stats_summary: Dict[str, Any],
        sleep_summary: Dict[str, Any],
        activity_summary: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Generate simple recommendations based on data.
        
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Steps recommendations
        avg_steps = stats_summary.get("avg_steps", 0)
        if avg_steps < 5000:
            recommendations.append({
                "category": "activity",
                "priority": "high",
                "message": "Try to increase daily steps. Aim for at least 7,000 steps to start.",
                "icon": "🚶"
            })
        elif avg_steps < 8000:
            recommendations.append({
                "category": "activity",
                "priority": "medium",
                "message": "Good step count! Try adding a short walk to reach 10,000 steps.",
                "icon": "🚶"
            })
        
        # Sleep recommendations
        avg_sleep = sleep_summary.get("avg_sleep_hours", 0)
        if avg_sleep < 6:
            recommendations.append({
                "category": "sleep",
                "priority": "high",
                "message": "You're getting less than 6 hours of sleep. Prioritize rest for better recovery.",
                "icon": "😴"
            })
        elif avg_sleep < 7:
            recommendations.append({
                "category": "sleep",
                "priority": "medium",
                "message": "Try to get 7-8 hours of sleep for optimal recovery.",
                "icon": "💤"
            })
        
        # Stress recommendations
        avg_stress = stats_summary.get("avg_stress", 0)
        if avg_stress and avg_stress > 50:
            recommendations.append({
                "category": "recovery",
                "priority": "high",
                "message": "Your stress levels are elevated. Consider relaxation or light activity.",
                "icon": "🧘"
            })
        
        # Activity recommendations
        total_workouts = activity_summary.get("total_activities", 0)
        if total_workouts < 2:
            recommendations.append({
                "category": "training",
                "priority": "medium",
                "message": "Try to fit in at least 3 workouts this week for better fitness.",
                "icon": "💪"
            })
        
        return recommendations
