"""Garmin Connect API service wrapper."""

import os
import re
import traceback
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from garminconnect import Garmin, GarminConnectAuthenticationError
import garth

from config import settings
from database import DatabaseManager


# Activity classification patterns for better detection
ACTIVITY_PATTERNS = {
    'yoga': [r'yoga', r'stretch', r'flexibility', r'flow'],
    'breathing': [r'breath', r'wim\s*hof', r'pranayama', r'meditat'],
    'cold_plunge': [r'cold', r'ice\s*bath', r'plunge', r'cold\s*water', r'cryotherapy'],
    'strength': [r'strength', r'gym', r'weight', r'lift', r'resistance', r'dumbbell', r'barbell', r'kettlebell'],
    'mobility': [r'mobility', r'foam\s*roll', r'recovery', r'myofascial'],
    'running': [r'run', r'jog', r'sprint', r'tempo', r'interval', r'fartlek', r'trail'],
    'cycling': [r'cycl', r'bike', r'spin', r'peloton'],
    'swimming': [r'swim', r'pool', r'lap'],
    'walking': [r'walk', r'hike', r'trek'],
    'hiit': [r'hiit', r'circuit', r'crossfit', r'tabata', r'bootcamp'],
}


def classify_activity(activity: Dict[str, Any]) -> str:
    """
    Better classify an activity based on name and type.
    Returns enhanced activity type.
    """
    raw_type = activity.get("activityType", {})
    if isinstance(raw_type, dict):
        type_key = raw_type.get("typeKey", "other")
    else:
        type_key = str(raw_type) if raw_type else "other"
    
    # If already a specific type, return it
    if type_key not in ['other', 'uncategorized', 'multi_sport']:
        return type_key
    
    # Try to classify from activity name
    name = (activity.get("activityName", "") or "").lower()
    description = (activity.get("description", "") or "").lower()
    search_text = f"{name} {description}"
    
    for activity_type, patterns in ACTIVITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                return activity_type
    
    return type_key


def enrich_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich activity with better classification and additional metadata."""
    enriched = activity.copy()
    
    # Better classify the activity
    classified_type = classify_activity(activity)
    enriched["classifiedType"] = classified_type
    
    # Add a friendly type name
    type_names = {
        'yoga': 'Yoga',
        'breathing': 'Breathing Exercise',
        'cold_plunge': 'Cold Plunge',
        'strength': 'Strength Training',
        'mobility': 'Mobility Work',
        'running': 'Running',
        'cycling': 'Cycling',
        'swimming': 'Swimming',
        'walking': 'Walking',
        'hiit': 'HIIT',
        'other': 'Other',
    }
    enriched["classifiedTypeName"] = type_names.get(classified_type, classified_type.replace('_', ' ').title())
    
    return enriched


class GarminService:
    """Service class for interacting with Garmin Connect API."""
    
    def __init__(self):
        self.client: Optional[Garmin] = None
        self.is_authenticated = False
        self.user_profile: Optional[Dict[str, Any]] = None
        self._token_path = Path(settings.garmin_token_path)
    
    def login(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        use_saved_tokens: bool = True
    ) -> bool:
        """
        Authenticate with Garmin Connect.
        
        Args:
            email: Garmin account email (uses settings if not provided)
            password: Garmin account password (uses settings if not provided)
            use_saved_tokens: Try to use saved OAuth tokens first
            
        Returns:
            True if authentication successful, False otherwise
        """
        email = email or settings.garmin_email
        password = password or settings.garmin_password
        
        if not email or not password:
            raise ValueError("Garmin email and password are required")
        
        try:
            self.client = Garmin(email, password)
            
            # Try to use saved tokens first
            token_path_str = str(self._token_path)
            if use_saved_tokens and self._token_path.exists():
                try:
                    self.client.login(token_path_str)
                    self.is_authenticated = True
                    self._load_user_profile()
                    return True
                except Exception:
                    pass  # Fall through to fresh login
            
            # Fresh login
            self.client.login()
            
            # Save tokens for future use
            self._token_path.mkdir(parents=True, exist_ok=True)
            self.client.garth.dump(token_path_str)
            
            self.is_authenticated = True
            self._load_user_profile()
            return True
            
        except GarminConnectAuthenticationError as e:
            self.is_authenticated = False
            raise AuthenticationError(f"Authentication failed: {str(e)}")
        except Exception as e:
            self.is_authenticated = False
            raise AuthenticationError(f"Login error: {str(e)}")
    
    def logout(self):
        """Clear authentication state."""
        self.client = None
        self.is_authenticated = False
        self.user_profile = None
    
    def _load_user_profile(self):
        """Load user profile data."""
        if self.client:
            try:
                full_name = self.client.get_full_name()
                # Handle both string and dict responses
                if isinstance(full_name, str):
                    self.user_profile = {"displayName": full_name}
                elif isinstance(full_name, dict):
                    self.user_profile = full_name
                else:
                    self.user_profile = {"displayName": str(full_name) if full_name else "User"}
            except Exception:
                self.user_profile = {"displayName": "User"}
    
    def _ensure_authenticated(self):
        """Ensure client is authenticated."""
        if not self.is_authenticated or not self.client:
            raise AuthenticationError("Not authenticated. Please login first.")
    
    # ==================== User Info ====================
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile information."""
        self._ensure_authenticated()
        try:
            profile = self.client.get_user_profile()
            return profile
        except Exception as e:
            return self.user_profile or {"displayName": "User"}
    
    def get_user_settings(self) -> Dict[str, Any]:
        """Get user settings including units and preferences."""
        self._ensure_authenticated()
        try:
            return self.client.get_user_settings()
        except Exception:
            return {}
    
    # ==================== Activities ====================
    
    def get_activities(
        self,
        start: int = 0,
        limit: int = 100,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of activities.
        
        Args:
            start: Pagination start index
            limit: Number of activities to fetch
            activity_type: Filter by activity type (e.g., 'running', 'cycling')
            
        Returns:
            List of activity dictionaries
        """
        self._ensure_authenticated()
        try:
            if activity_type:
                activities = self.client.get_activities_by_type(activity_type, start, limit)
            else:
                activities = self.client.get_activities(start, limit)
            
            # Enrich activities with better classification
            enriched_activities = [enrich_activity(a) for a in activities]
            
            # Cache to database
            DatabaseManager.save_activities(enriched_activities)
            
            return enriched_activities
        except Exception as e:
            # Fall back to cached data
            cached = DatabaseManager.get_activities(limit=limit)
            if cached:
                return [enrich_activity(a.raw_data) for a in cached if a.raw_data]
            raise DataFetchError(f"Failed to fetch activities: {str(e)}")
    
    def get_activity_details(self, activity_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific activity."""
        self._ensure_authenticated()
        try:
            return self.client.get_activity(activity_id)
        except Exception as e:
            raise DataFetchError(f"Failed to fetch activity {activity_id}: {str(e)}")
    
    def get_activities_by_date(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get activities within a date range."""
        self._ensure_authenticated()
        end_date = end_date or date.today()
        
        try:
            # Fetch all activities and filter
            all_activities = []
            start = 0
            batch_size = 100
            
            while True:
                batch = self.client.get_activities(start, batch_size)
                if not batch:
                    break
                
                for activity in batch:
                    activity_date_str = activity.get("startTimeLocal", "")[:10]
                    try:
                        activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        continue
                    
                    if activity_date < start_date:
                        # Activities are sorted by date desc, so we can stop
                        return all_activities
                    
                    if activity_date <= end_date:
                        if activity_type is None or activity.get("activityType", {}).get("typeKey") == activity_type:
                            all_activities.append(enrich_activity(activity))
                
                start += batch_size
                
                # Safety limit
                if start > 1000:
                    break
            
            # Cache activities
            DatabaseManager.save_activities(all_activities)
            
            return all_activities
            
        except Exception as e:
            # Fall back to cached data
            cached = DatabaseManager.get_activities(
                start_date=start_date,
                end_date=end_date,
                activity_type=activity_type
            )
            if cached:
                return [a.raw_data for a in cached if a.raw_data]
            raise DataFetchError(f"Failed to fetch activities: {str(e)}")
    
    # ==================== Daily Stats ====================
    
    def get_stats(self, stats_date: date) -> Dict[str, Any]:
        """Get daily statistics for a specific date."""
        self._ensure_authenticated()
        try:
            date_str = stats_date.strftime("%Y-%m-%d")
            stats = self.client.get_stats(date_str)
            
            # Cache to database
            DatabaseManager.save_health_stats(stats_date, stats)
            
            return stats
        except Exception as e:
            # Fall back to cached data
            cached = DatabaseManager.get_health_stats(start_date=stats_date, end_date=stats_date)
            if cached:
                return cached[0].raw_data or {}
            raise DataFetchError(f"Failed to fetch stats for {stats_date}: {str(e)}")
    
    def get_stats_range(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get daily statistics for a date range."""
        end_date = end_date or date.today()
        stats_list = []
        
        current_date = start_date
        while current_date <= end_date:
            try:
                stats = self.get_stats(current_date)
                stats["date"] = current_date.strftime("%Y-%m-%d")
                stats_list.append(stats)
            except Exception:
                pass  # Skip failed days
            current_date += timedelta(days=1)
        
        return stats_list
    
    # ==================== Heart Rate ====================
    
    def get_heart_rates(self, hr_date: date) -> Dict[str, Any]:
        """Get heart rate data for a specific date."""
        self._ensure_authenticated()
        try:
            date_str = hr_date.strftime("%Y-%m-%d")
            return self.client.get_heart_rates(date_str)
        except Exception as e:
            raise DataFetchError(f"Failed to fetch heart rate data: {str(e)}")
    
    def get_hrv_data(self, hrv_date: date) -> Dict[str, Any]:
        """Get HRV (Heart Rate Variability) data for a specific date."""
        self._ensure_authenticated()
        try:
            date_str = hrv_date.strftime("%Y-%m-%d")
            return self.client.get_hrv_data(date_str)
        except Exception as e:
            return {}
    
    def get_hr_zones(self) -> Dict[str, Any]:
        """Get user's heart rate zones from Garmin settings."""
        self._ensure_authenticated()
        try:
            # Try to get from user settings
            user_settings = self.client.get_user_settings()
            
            # Extract max HR and zones
            max_hr = user_settings.get("userData", {}).get("maxHeartRate", 185)
            resting_hr = user_settings.get("userData", {}).get("restingHeartRate", 60)
            
            # Try to get actual HR zone settings
            try:
                # Some Garmin accounts have specific zone data
                hr_zones_data = self.client.get_user_heart_rate_zones()
                if hr_zones_data:
                    return {
                        "max_hr": max_hr,
                        "resting_hr": resting_hr,
                        "zones": hr_zones_data,
                        "source": "garmin_zones"
                    }
            except Exception:
                pass
            
            # Calculate default zones based on max HR (Karvonen method)
            hr_reserve = max_hr - resting_hr
            zones = {
                "zone1": {
                    "name": "Recovery",
                    "min_bpm": resting_hr + int(hr_reserve * 0.50),
                    "max_bpm": resting_hr + int(hr_reserve * 0.60),
                    "min_pct": 50,
                    "max_pct": 60
                },
                "zone2": {
                    "name": "Aerobic Base",
                    "min_bpm": resting_hr + int(hr_reserve * 0.60),
                    "max_bpm": resting_hr + int(hr_reserve * 0.70),
                    "min_pct": 60,
                    "max_pct": 70
                },
                "zone3": {
                    "name": "Tempo",
                    "min_bpm": resting_hr + int(hr_reserve * 0.70),
                    "max_bpm": resting_hr + int(hr_reserve * 0.80),
                    "min_pct": 70,
                    "max_pct": 80
                },
                "zone4": {
                    "name": "Threshold",
                    "min_bpm": resting_hr + int(hr_reserve * 0.80),
                    "max_bpm": resting_hr + int(hr_reserve * 0.90),
                    "min_pct": 80,
                    "max_pct": 90
                },
                "zone5": {
                    "name": "VO2max/Anaerobic",
                    "min_bpm": resting_hr + int(hr_reserve * 0.90),
                    "max_bpm": max_hr,
                    "min_pct": 90,
                    "max_pct": 100
                }
            }
            
            return {
                "max_hr": max_hr,
                "resting_hr": resting_hr,
                "zones": zones,
                "source": "calculated"
            }
        except Exception as e:
            # Return default zones if all else fails
            return {
                "max_hr": 185,
                "resting_hr": 60,
                "zones": {
                    "zone1": {"name": "Recovery", "min_bpm": 93, "max_bpm": 111, "min_pct": 50, "max_pct": 60},
                    "zone2": {"name": "Aerobic Base", "min_bpm": 111, "max_bpm": 130, "min_pct": 60, "max_pct": 70},
                    "zone3": {"name": "Tempo", "min_bpm": 130, "max_bpm": 148, "min_pct": 70, "max_pct": 80},
                    "zone4": {"name": "Threshold", "min_bpm": 148, "max_bpm": 167, "min_pct": 80, "max_pct": 90},
                    "zone5": {"name": "VO2max/Anaerobic", "min_bpm": 167, "max_bpm": 185, "min_pct": 90, "max_pct": 100}
                },
                "source": "default"
            }
    
    def get_today_readiness(self) -> Dict[str, Any]:
        """Get TODAY's readiness data for autoregulation (daily, not weekly)."""
        self._ensure_authenticated()
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        readiness = {
            "date": today.strftime("%Y-%m-%d"),
            "body_battery": None,
            "sleep_score": None,
            "hrv_status": "Unknown",
            "hrv_avg": None,
            "hrv_weekly_avg": None,
            "resting_hr": None,
            "stress_level": None,
            "readiness_score": 50,  # Default
            "should_reduce_intensity": False,
            "should_rest": False,
            "adjustment_reason": None
        }
        
        # Try to get body battery directly from the dedicated endpoint (more reliable)
        # Try today first, then yesterday as fallback
        for check_date in [today, yesterday]:
            if readiness["body_battery"] is not None:
                break
            try:
                date_str = check_date.strftime("%Y-%m-%d")
                battery_data = self.client.get_body_battery(date_str) or []
                if battery_data and isinstance(battery_data, list):
                    all_values = []
                    for item in battery_data:
                        if not isinstance(item, dict):
                            continue
                        # Try bodyBatteryValuesArray format: [[timestamp, value], ...]
                        values_array = item.get("bodyBatteryValuesArray", [])
                        if values_array and isinstance(values_array, list):
                            for entry in values_array:
                                if isinstance(entry, list) and len(entry) >= 2 and entry[1] is not None:
                                    all_values.append(entry[1])
                        # Also try direct bodyBatteryLevel format
                        if item.get("bodyBatteryLevel") is not None:
                            all_values.append(item.get("bodyBatteryLevel"))
                    
                    if all_values:
                        readiness["body_battery"] = all_values[-1]  # Most recent
            except Exception as e:
                print(f"Error fetching body battery for {check_date}: {e}")
        
        # Try to get today's stats
        try:
            stats = self.get_stats(today)
            if stats:
                # Use most recent value for current body battery if not already set
                if readiness["body_battery"] is None:
                    readiness["body_battery"] = stats.get("bodyBatteryMostRecentValue") or stats.get("bodyBatteryHighestValue")
                readiness["stress_level"] = stats.get("averageStressLevel")
                readiness["resting_hr"] = stats.get("restingHeartRate")
        except Exception:
            pass
        
        # If still no resting HR, try yesterday's stats
        if readiness["resting_hr"] is None:
            try:
                yesterday_stats = self.get_stats(yesterday)
                if yesterday_stats:
                    readiness["resting_hr"] = yesterday_stats.get("restingHeartRate")
            except Exception:
                pass
        
        # Try to get last night's sleep (could be logged under today or yesterday)
        sleep_score_found = False
        for sleep_date in [today, yesterday]:
            if sleep_score_found:
                break
            try:
                sleep = self.get_sleep_data(sleep_date)
                if sleep:
                    # Sleep score can be at root level or inside dailySleepDTO
                    # First try root level sleepScores
                    sleep_scores = sleep.get("sleepScores")
                    if isinstance(sleep_scores, dict):
                        overall = sleep_scores.get("overall", {})
                        if isinstance(overall, dict):
                            score = overall.get("value") or overall.get("qualifierKey")
                            if score:
                                readiness["sleep_score"] = score
                                sleep_score_found = True
                                print(f"[Sleep] Found score at root level: {score}")
                    
                    # If not found at root, try dailySleepDTO
                    if not sleep_score_found:
                        dto = sleep.get("dailySleepDTO", {})
                        if dto:
                            dto_scores = dto.get("sleepScores")
                            if isinstance(dto_scores, dict):
                                overall = dto_scores.get("overall", {})
                                if isinstance(overall, dict):
                                    score = overall.get("value") or overall.get("qualifierKey")
                                    if score:
                                        readiness["sleep_score"] = score
                                        sleep_score_found = True
                                        print(f"[Sleep] Found score in dto: {score}")
                            
                            # As last resort, calculate from sleep time
                            if not sleep_score_found:
                                sleep_seconds = dto.get("sleepTimeSeconds", 0) or 0
                                if sleep_seconds > 0:
                                    sleep_hours = sleep_seconds / 3600
                                    readiness["sleep_score"] = min(100, int(sleep_hours / 8 * 100))
                                    sleep_score_found = True
                                    print(f"[Sleep] Calculated score from duration: {readiness['sleep_score']}")
            except Exception as e:
                print(f"Error fetching sleep for {sleep_date}: {e}")
        
        # Get HRV status - try today first, then yesterday
        for hrv_date in [today, yesterday]:
            if readiness["hrv_status"] != "Unknown":
                break
            try:
                hrv = self.get_hrv_data(hrv_date)
                if hrv and isinstance(hrv, dict):
                    hrv_summary = hrv.get("hrvSummary", {})
                    if hrv_summary:
                        hrv_status = hrv_summary.get("status")
                        if hrv_status:
                            readiness["hrv_status"] = hrv_status
                            # Also get the average HRV value
                            readiness["hrv_avg"] = hrv_summary.get("lastNightAvg")
                            readiness["hrv_weekly_avg"] = hrv_summary.get("weeklyAvg")
            except Exception as e:
                print(f"Error fetching HRV for {hrv_date}: {e}")
        
        try:
            # Get training readiness if available
            training = self.get_training_readiness(today)
            if training and training.get("score"):
                readiness["readiness_score"] = training.get("score")
        except Exception:
            pass
        
        # Calculate readiness score if not available from Garmin
        if readiness["readiness_score"] == 50:
            score = 70  # Base score
            
            bb = readiness["body_battery"]
            if bb is not None:
                if bb >= 70:
                    score += 15
                elif bb >= 50:
                    score += 5
                elif bb < 30:
                    score -= 20
                elif bb < 50:
                    score -= 10
            
            ss = readiness["sleep_score"]
            if ss is not None:
                if ss >= 80:
                    score += 10
                elif ss >= 60:
                    score += 5
                elif ss < 40:
                    score -= 15
            
            stress = readiness["stress_level"]
            if stress is not None:
                if stress < 25:
                    score += 5
                elif stress > 60:
                    score -= 10
            
            readiness["readiness_score"] = max(0, min(100, score))
        
        # Apply autoregulation rules (from prompt.txt)
        bb = readiness["body_battery"]
        ss = readiness["sleep_score"]
        hrv = readiness["hrv_status"]
        
        # REST required if Body Battery < 30 OR Sleep Score < 40
        if (bb is not None and bb < 30) or (ss is not None and ss < 40):
            readiness["should_rest"] = True
            readiness["adjustment_reason"] = f"REST REQUIRED: Body Battery={bb}, Sleep Score={ss}"
        # Reduce intensity if HRV is unbalanced or readiness is low
        elif hrv and "unbalanced" in str(hrv).lower():
            readiness["should_reduce_intensity"] = True
            readiness["adjustment_reason"] = f"REDUCE INTENSITY: HRV Status is {hrv}"
        elif readiness["readiness_score"] < 50:
            readiness["should_reduce_intensity"] = True
            readiness["adjustment_reason"] = f"REDUCE INTENSITY: Readiness Score={readiness['readiness_score']}"
        
        return readiness
    
    # ==================== Sleep ====================
    
    def get_sleep_data(self, sleep_date: date) -> Dict[str, Any]:
        """Get sleep data for a specific date."""
        self._ensure_authenticated()
        try:
            date_str = sleep_date.strftime("%Y-%m-%d")
            sleep_data = self.client.get_sleep_data(date_str)
            
            # Cache to database
            DatabaseManager.save_sleep_data(sleep_date, sleep_data)
            
            return sleep_data
        except Exception as e:
            # Fall back to cached data
            cached = DatabaseManager.get_sleep_data(start_date=sleep_date, end_date=sleep_date)
            if cached:
                return cached[0].raw_data or {}
            raise DataFetchError(f"Failed to fetch sleep data: {str(e)}")
    
    def get_sleep_range(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get sleep data for a date range."""
        end_date = end_date or date.today()
        sleep_list = []
        
        current_date = start_date
        while current_date <= end_date:
            try:
                sleep = self.get_sleep_data(current_date)
                sleep["date"] = current_date.strftime("%Y-%m-%d")
                sleep_list.append(sleep)
            except Exception:
                pass
            current_date += timedelta(days=1)
        
        return sleep_list
    
    # ==================== Stress ====================
    
    def get_stress_data(self, stress_date: date) -> Dict[str, Any]:
        """Get stress data for a specific date."""
        self._ensure_authenticated()
        try:
            date_str = stress_date.strftime("%Y-%m-%d")
            return self.client.get_stress_data(date_str)
        except Exception as e:
            return {}
    
    # ==================== Body Composition ====================
    
    def get_body_composition(self, comp_date: date) -> Dict[str, Any]:
        """Get body composition data."""
        self._ensure_authenticated()
        try:
            date_str = comp_date.strftime("%Y-%m-%d")
            return self.client.get_body_composition(date_str)
        except Exception:
            return {}
    
    def get_weigh_ins(self, start_date: date, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get weight measurements for date range."""
        self._ensure_authenticated()
        end_date = end_date or date.today()
        try:
            return self.client.get_weigh_ins(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
        except Exception:
            return []
    
    # ==================== Training Status ====================
    
    def get_training_status(self, status_date: date) -> Dict[str, Any]:
        """Get training status and readiness."""
        self._ensure_authenticated()
        try:
            date_str = status_date.strftime("%Y-%m-%d")
            return self.client.get_training_status(date_str)
        except Exception:
            return {}
    
    def get_training_readiness(self, readiness_date: date) -> Dict[str, Any]:
        """Get training readiness score."""
        self._ensure_authenticated()
        try:
            date_str = readiness_date.strftime("%Y-%m-%d")
            return self.client.get_training_readiness(date_str)
        except Exception:
            return {}
    
    def get_morning_training_readiness(self, readiness_date: date) -> Dict[str, Any]:
        """Get morning training readiness data."""
        self._ensure_authenticated()
        try:
            date_str = readiness_date.strftime("%Y-%m-%d")
            return self.client.get_morning_training_readiness(date_str) or {}
        except Exception:
            return {}
    
    # ==================== Advanced Performance Metrics ====================
    
    def get_race_predictions(self) -> Dict[str, Any]:
        """Get race time predictions (5K, 10K, Half, Marathon)."""
        self._ensure_authenticated()
        try:
            return self.client.get_race_predictions() or {}
        except Exception:
            return {}
    
    def get_endurance_score(self) -> Dict[str, Any]:
        """Get endurance score data."""
        self._ensure_authenticated()
        try:
            return self.client.get_endurance_score() or {}
        except Exception:
            return {}
    
    def get_hill_score(self) -> Dict[str, Any]:
        """Get hill score for trail running."""
        self._ensure_authenticated()
        try:
            return self.client.get_hill_score() or {}
        except Exception:
            return {}
    
    def get_max_metrics(self, metrics_date: date) -> Dict[str, Any]:
        """Get max metrics (VO2max, training load, etc.)."""
        self._ensure_authenticated()
        try:
            date_str = metrics_date.strftime("%Y-%m-%d")
            return self.client.get_max_metrics(date_str) or {}
        except Exception:
            return {}
    
    def get_fitness_age(self, age_date: date) -> Dict[str, Any]:
        """Get fitness age data."""
        self._ensure_authenticated()
        try:
            date_str = age_date.strftime("%Y-%m-%d")
            return self.client.get_fitnessage_data(date_str) or {}
        except Exception:
            return {}
    
    def get_lactate_threshold(self) -> Dict[str, Any]:
        """Get lactate threshold data (for pace zones)."""
        self._ensure_authenticated()
        try:
            return self.client.get_lactate_threshold() or {}
        except Exception:
            return {}
    
    def get_personal_records(self) -> Dict[str, Any]:
        """Get personal records."""
        self._ensure_authenticated()
        try:
            return self.client.get_personal_record() or {}
        except Exception:
            return {}
    
    # ==================== Body Battery & Energy ====================
    
    def get_body_battery_detailed(self, bb_date: date) -> Dict[str, Any]:
        """Get detailed body battery data including events."""
        self._ensure_authenticated()
        try:
            date_str = bb_date.strftime("%Y-%m-%d")
            battery_data = self.client.get_body_battery(date_str) or []
            events = self.client.get_body_battery_events(date_str) or []
            
            # Process battery data - extract values from different possible formats
            current_value = None
            highest = None
            lowest = None
            all_values = []
            
            if battery_data and isinstance(battery_data, list):
                for item in battery_data:
                    if not isinstance(item, dict):
                        continue
                    
                    # Try bodyBatteryValuesArray format: [[timestamp, value], ...]
                    values_array = item.get("bodyBatteryValuesArray", [])
                    if values_array and isinstance(values_array, list):
                        for entry in values_array:
                            if isinstance(entry, list) and len(entry) >= 2 and entry[1] is not None:
                                all_values.append(entry[1])
                    
                    # Also try direct bodyBatteryLevel format
                    if item.get("bodyBatteryLevel") is not None:
                        all_values.append(item.get("bodyBatteryLevel"))
                    
                    # Try charged/drained values as fallback
                    if item.get("charged") is not None:
                        all_values.append(item.get("charged"))
            
            if all_values:
                current_value = all_values[-1]  # Most recent
                highest = max(all_values)
                lowest = min(all_values)
            
            return {
                "date": date_str,
                "current_value": current_value,
                "highest": highest,
                "lowest": lowest,
                "timeline": battery_data,
                "events": events,
                "charged_total": sum(e.get("bodyBatteryChange", 0) or 0 for e in events if (e.get("bodyBatteryChange") or 0) > 0),
                "drained_total": abs(sum(e.get("bodyBatteryChange", 0) or 0 for e in events if (e.get("bodyBatteryChange") or 0) < 0)),
            }
        except Exception as e:
            print(f"Error in get_body_battery_detailed: {e}")
            return {"date": bb_date.strftime("%Y-%m-%d"), "current_value": None}
    
    # ==================== Respiration & SpO2 ====================
    
    def get_respiration_data(self, resp_date: date) -> Dict[str, Any]:
        """Get respiration rate data."""
        self._ensure_authenticated()
        try:
            date_str = resp_date.strftime("%Y-%m-%d")
            return self.client.get_respiration_data(date_str) or {}
        except Exception:
            return {}
    
    def get_spo2_data(self, spo2_date: date) -> Dict[str, Any]:
        """Get SpO2 (blood oxygen) data."""
        self._ensure_authenticated()
        try:
            date_str = spo2_date.strftime("%Y-%m-%d")
            return self.client.get_spo2_data(date_str) or {}
        except Exception:
            return {}
    
    # ==================== Hydration ====================
    
    def get_hydration_data(self, hydration_date: date) -> Dict[str, Any]:
        """Get hydration data."""
        self._ensure_authenticated()
        try:
            date_str = hydration_date.strftime("%Y-%m-%d")
            return self.client.get_hydration_data(date_str) or {}
        except Exception:
            return {}
    
    # ==================== Steps & Floors ====================
    
    def get_steps_data(self, steps_date: date) -> List[Dict[str, Any]]:
        """Get detailed steps data with timeline."""
        self._ensure_authenticated()
        try:
            date_str = steps_date.strftime("%Y-%m-%d")
            return self.client.get_steps_data(date_str) or []
        except Exception:
            return []
    
    def get_floors_data(self, floors_date: date) -> Dict[str, Any]:
        """Get floors climbed data."""
        self._ensure_authenticated()
        try:
            date_str = floors_date.strftime("%Y-%m-%d")
            return self.client.get_floors(date_str) or {}
        except Exception:
            return {}
    
    def get_daily_steps(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get daily steps for a date range."""
        self._ensure_authenticated()
        try:
            return self.client.get_daily_steps(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            ) or []
        except Exception:
            return []
    
    # ==================== Intensity Minutes ====================
    
    def get_intensity_minutes(self, im_date: date) -> Dict[str, Any]:
        """Get intensity minutes data."""
        self._ensure_authenticated()
        try:
            date_str = im_date.strftime("%Y-%m-%d")
            return self.client.get_intensity_minutes_data(date_str) or {}
        except Exception:
            return {}
    
    def get_weekly_intensity_minutes(self, weeks: int = 4) -> List[Dict[str, Any]]:
        """Get weekly intensity minutes for trend analysis."""
        self._ensure_authenticated()
        try:
            end_date = date.today().strftime("%Y-%m-%d")
            return self.client.get_weekly_intensity_minutes(end_date, weeks) or []
        except Exception:
            return []
    
    # ==================== Activity Details ====================
    
    def get_activity_splits(self, activity_id: str) -> Dict[str, Any]:
        """Get activity splits data (laps, segments)."""
        self._ensure_authenticated()
        try:
            return self.client.get_activity_splits(activity_id) or {}
        except Exception:
            return {}
    
    def get_activity_hr_zones(self, activity_id: str) -> Dict[str, Any]:
        """Get HR zone distribution for an activity."""
        self._ensure_authenticated()
        try:
            return self.client.get_activity_hr_in_timezones(activity_id) or {}
        except Exception:
            return {}
    
    def get_activity_weather(self, activity_id: str) -> Dict[str, Any]:
        """Get weather data during an activity."""
        self._ensure_authenticated()
        try:
            return self.client.get_activity_weather(activity_id) or {}
        except Exception:
            return {}
    
    def get_activity_exercise_sets(self, activity_id: str) -> Dict[str, Any]:
        """Get exercise sets for strength activities."""
        self._ensure_authenticated()
        try:
            return self.client.get_activity_exercise_sets(activity_id) or {}
        except Exception:
            return {}
    
    def get_activity_gear(self, activity_id: str) -> Dict[str, Any]:
        """Get gear used for an activity."""
        self._ensure_authenticated()
        try:
            return self.client.get_activity_gear(activity_id) or {}
        except Exception:
            return {}
    
    def get_activity_typed_splits(self, activity_id: str) -> Dict[str, Any]:
        """Get typed splits data for an activity (includes more detailed lap info)."""
        self._ensure_authenticated()
        try:
            return self.client.get_activity_typed_splits(activity_id) or {}
        except Exception:
            return {}
    
    def get_activity_split_summaries(self, activity_id: str) -> Dict[str, Any]:
        """Get split summaries for an activity."""
        self._ensure_authenticated()
        try:
            return self.client.get_activity_split_summaries(activity_id) or {}
        except Exception:
            return {}
    
    def get_comprehensive_activity_data(self, activity_id: str) -> Dict[str, Any]:
        """
        Get comprehensive activity data including all available metrics.
        This includes: basic details, splits, HR zones, weather, exercise sets,
        gear, typed splits, and split summaries.
        
        Useful for detailed activity analysis and chart display.
        """
        self._ensure_authenticated()
        
        result = {
            "activity_id": activity_id,
            "activity": {},
            "splits": {},
            "typed_splits": {},
            "split_summaries": {},
            "hr_zones": {},
            "weather": {},
            "exercise_sets": {},
            "gear": {},
            "metrics": {
                "has_stress": False,
                "has_respiration": False,
                "has_performance_condition": False,
                "has_pace": False,
                "has_cadence": False,
                "has_power": False,
                "has_stride_length": False,
                "has_stamina": False,
            }
        }
        
        # Get basic activity details
        try:
            activity = self.client.get_activity(activity_id)
            result["activity"] = activity or {}
            
            # Check what metrics are available in the activity
            if activity:
                # Check for various metrics
                result["metrics"]["has_pace"] = bool(activity.get("averageSpeed"))
                result["metrics"]["has_cadence"] = bool(
                    activity.get("averageRunningCadenceInStepsPerMinute") or 
                    activity.get("averageCadence")
                )
                result["metrics"]["has_stride_length"] = bool(activity.get("avgStrideLength"))
                result["metrics"]["has_performance_condition"] = bool(
                    activity.get("performanceCondition") or
                    activity.get("firstBeatPerformanceCondition")
                )
                result["metrics"]["has_stamina"] = bool(
                    activity.get("aerobicTrainingEffectMessage") or 
                    activity.get("anaerobicTrainingEffectMessage")
                )
                result["metrics"]["has_power"] = bool(
                    activity.get("avgPower") or 
                    activity.get("normPower")
                )
        except Exception as e:
            print(f"Error fetching activity {activity_id}: {e}")
        
        # Get detailed splits (contains HR/pace/cadence timeline data)
        try:
            splits = self.client.get_activity_splits(activity_id)
            result["splits"] = splits or {}
        except Exception as e:
            print(f"Error fetching splits: {e}")
        
        # Get typed splits (more structured split data)
        try:
            typed_splits = self.client.get_activity_typed_splits(activity_id)
            result["typed_splits"] = typed_splits or {}
        except Exception as e:
            print(f"Error fetching typed splits: {e}")
        
        # Get split summaries
        try:
            split_summaries = self.client.get_activity_split_summaries(activity_id)
            result["split_summaries"] = split_summaries or {}
        except Exception as e:
            print(f"Error fetching split summaries: {e}")
        
        # Get HR zone distribution
        try:
            hr_zones = self.client.get_activity_hr_in_timezones(activity_id)
            result["hr_zones"] = hr_zones or {}
        except Exception as e:
            print(f"Error fetching HR zones: {e}")
        
        # Get weather data
        try:
            weather = self.client.get_activity_weather(activity_id)
            result["weather"] = weather or {}
        except Exception as e:
            print(f"Error fetching weather: {e}")
        
        # Get exercise sets (for strength training)
        try:
            exercise_sets = self.client.get_activity_exercise_sets(activity_id)
            result["exercise_sets"] = exercise_sets or {}
        except Exception as e:
            print(f"Error fetching exercise sets: {e}")
        
        # Get gear
        try:
            gear = self.client.get_activity_gear(activity_id)
            result["gear"] = gear or {}
        except Exception as e:
            print(f"Error fetching gear: {e}")
        
        # Extract key metrics from the activity for easy access
        activity = result.get("activity", {})
        result["summary"] = {
            "name": activity.get("activityName"),
            "type": activity.get("activityType", {}).get("typeKey", "other") if isinstance(activity.get("activityType"), dict) else "other",
            "duration_seconds": activity.get("duration", 0),
            "distance_meters": activity.get("distance", 0),
            "calories": activity.get("calories", 0),
            "avg_hr": activity.get("averageHR"),
            "max_hr": activity.get("maxHR"),
            "avg_speed": activity.get("averageSpeed"),
            "max_speed": activity.get("maxSpeed"),
            "elevation_gain": activity.get("elevationGain"),
            "elevation_loss": activity.get("elevationLoss"),
            "avg_cadence": activity.get("averageRunningCadenceInStepsPerMinute") or activity.get("averageCadence"),
            "max_cadence": activity.get("maxRunningCadenceInStepsPerMinute") or activity.get("maxCadence"),
            "avg_stride_length": activity.get("avgStrideLength"),
            "performance_condition": activity.get("performanceCondition") or activity.get("firstBeatPerformanceCondition"),
            "training_effect_aerobic": activity.get("aerobicTrainingEffect") or activity.get("trainingEffectAerobic"),
            "training_effect_anaerobic": activity.get("anaerobicTrainingEffect") or activity.get("trainingEffectAnaerobic"),
            "avg_respiration": activity.get("avgRespirationRate"),
            "max_respiration": activity.get("maxRespirationRate"),
            "avg_stress": activity.get("avgStressLevel"),
            "max_stress": activity.get("maxStressLevel"),
            "vo2max": activity.get("vO2MaxValue"),
            "avg_power": activity.get("avgPower"),
            "max_power": activity.get("maxPower"),
            "normalized_power": activity.get("normPower"),
            "training_load": activity.get("trainingLoad"),
            "recovery_time": activity.get("recoveryTimeInMinutes"),
            "start_time": activity.get("startTimeLocal"),
        }
        
        # Update metrics flags based on summary
        summary = result["summary"]
        result["metrics"]["has_stress"] = summary["avg_stress"] is not None
        result["metrics"]["has_respiration"] = summary["avg_respiration"] is not None
        result["metrics"]["has_performance_condition"] = summary["performance_condition"] is not None
        
        return result
    
    def get_all_day_stress(self, stress_date: date) -> Dict[str, Any]:
        """Get all-day stress data with timeline for a specific date."""
        self._ensure_authenticated()
        try:
            date_str = stress_date.strftime("%Y-%m-%d")
            return self.client.get_all_day_stress(date_str) or {}
        except Exception as e:
            print(f"Error fetching all-day stress: {e}")
            return {}
    
    # ==================== Workouts & Training Plans ====================
    
    def get_workouts(self, start: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Get saved workouts from Garmin Connect."""
        self._ensure_authenticated()
        try:
            return self.client.get_workouts(start, limit) or {}
        except Exception:
            return {}
    
    def get_training_plans(self) -> Dict[str, Any]:
        """Get active training plans."""
        self._ensure_authenticated()
        try:
            return self.client.get_training_plans() or {}
        except Exception:
            return {}
    
    def upload_workout(self, workout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a workout to Garmin Connect."""
        self._ensure_authenticated()
        try:
            result = self.client.upload_workout(workout_data)
            return result or {"success": True}
        except Exception as e:
            return {"error": str(e)}
    
    def upload_running_workout_structured(self, workout_name: str, steps: List[Dict[str, Any]], 
                                          estimated_duration_secs: int = 3600) -> Dict[str, Any]:
        """Upload a properly structured running workout to Garmin Connect.
        
        Uses the official garminconnect.workout typed models for proper API compatibility.
        
        Args:
            workout_name: Name of the workout
            steps: List of workout steps with type, duration, and targets
            estimated_duration_secs: Total estimated duration in seconds
        
        Returns:
            Dict with upload result or error
        """
        self._ensure_authenticated()
        try:
            # Try to use the typed workout models from garminconnect
            try:
                from garminconnect.workout import (
                    RunningWorkout, WorkoutSegment, ExecutableStep, RepeatGroup,
                    create_warmup_step, create_interval_step, create_recovery_step, create_cooldown_step,
                    create_repeat_group, StepType, ConditionType, TargetType
                )
                
                # Build workout steps using typed models
                workout_steps = []
                step_order = 1
                
                for step in steps:
                    garmin_step = self._build_typed_garmin_step(step, step_order)
                    if garmin_step:
                        workout_steps.append(garmin_step)
                        step_order += 1
                
                # Create the workout using typed models
                workout = RunningWorkout(
                    workoutName=workout_name,
                    estimatedDurationInSecs=estimated_duration_secs,
                    workoutSegments=[
                        WorkoutSegment(
                            segmentOrder=1,
                            sportType={"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
                            workoutSteps=workout_steps
                        )
                    ]
                )
                
                # Upload using the typed method
                result = self.client.upload_running_workout(workout)
                
            except ImportError:
                # Fallback to dict-based upload if typed models not available
                workout_steps = []
                step_order = 1
                
                for step in steps:
                    garmin_step = self._build_garmin_step_dict(step, step_order)
                    workout_steps.append(garmin_step)
                    step_order += 1
                
                workout_data = {
                    "workoutName": workout_name,
                    "sportType": {
                        "sportTypeId": 1,
                        "sportTypeKey": "running",
                        "displayOrder": 1
                    },
                    "estimatedDurationInSecs": estimated_duration_secs,
                    "workoutSegments": [{
                        "segmentOrder": 1,
                        "sportType": {
                            "sportTypeId": 1,
                            "sportTypeKey": "running",
                            "displayOrder": 1
                        },
                        "workoutSteps": workout_steps
                    }]
                }
                
                result = self.client.upload_workout(workout_data)
            
            if result:
                return {
                    "success": True,
                    "workoutId": result.get("workoutId"),
                    "workoutName": workout_name,
                    "message": f"Workout '{workout_name}' uploaded successfully to Garmin Connect"
                }
            return {"success": True, "message": "Workout uploaded"}
            
        except Exception as e:
            return {"error": str(e), "details": traceback.format_exc(), "success": False}
    
    def _build_typed_garmin_step(self, step: Dict[str, Any], order: int):
        """Build a Garmin workout step using typed models."""
        try:
            from garminconnect.workout import (
                ExecutableStep, StepType, ConditionType, TargetType
            )
            
            step_type = step.get("type", "active").lower()
            duration_minutes = step.get("duration_minutes", 0)
            duration_seconds = duration_minutes * 60 if duration_minutes else 300
            
            # Map step types
            type_map = {
                "warmup": (StepType.WARMUP, "warmup"),
                "cooldown": (StepType.COOLDOWN, "cooldown"),
                "active": (StepType.INTERVAL, "interval"),
                "interval": (StepType.INTERVAL, "interval"),
                "recovery": (StepType.RECOVERY, "recovery"),
                "rest": (StepType.REST, "rest"),
            }
            
            step_type_id, step_type_key = type_map.get(step_type, (StepType.INTERVAL, "interval"))
            
            # Build target type
            target_type = step.get("target_type", "open")
            target_pace_min = step.get("target_pace_min")
            
            target_dict = {
                "workoutTargetTypeId": TargetType.NO_TARGET,
                "workoutTargetTypeKey": "no.target",
                "displayOrder": 1
            }
            
            # For pace targets, we need to set speed values
            target_value_one = None
            target_value_two = None
            
            if target_type == "pace" and target_pace_min and isinstance(target_pace_min, str) and ":" in target_pace_min:
                try:
                    parts = target_pace_min.split(":")
                    if len(parts) == 2:
                        minutes = int(parts[0])
                        seconds = int(parts[1])
                        total_secs = minutes * 60 + seconds
                        if total_secs > 0:
                            speed_ms = 1000 / total_secs
                            # Speed target - low is slower pace (lower speed), high is faster pace (higher speed)
                            target_value_one = round(speed_ms * 0.95, 4)  # 5% slower
                            target_value_two = round(speed_ms * 1.05, 4)  # 5% faster
                            target_dict = {
                                "workoutTargetTypeId": TargetType.SPEED,
                                "workoutTargetTypeKey": "speed.zone",
                                "displayOrder": 4
                            }
                except:
                    pass
            
            return ExecutableStep(
                stepOrder=order,
                stepType={
                    "stepTypeId": step_type_id,
                    "stepTypeKey": step_type_key,
                    "displayOrder": step_type_id
                },
                endCondition={
                    "conditionTypeId": ConditionType.TIME,
                    "conditionTypeKey": "time",
                    "displayOrder": 2,
                    "displayable": True
                },
                endConditionValue=float(duration_seconds),
                targetType=target_dict,
                targetValueOne=target_value_one,
                targetValueTwo=target_value_two
            )
            
        except Exception as e:
            print(f"Error building typed step: {e}")
            return None
    
    def _build_garmin_step_dict(self, step: Dict[str, Any], order: int) -> Dict[str, Any]:
        """Build a single Garmin workout step as a dictionary (fallback method)."""
        step_type = step.get("type", "active").lower()
        
        # Map step types to Garmin step types (using official IDs from garminconnect.workout)
        type_map = {
            "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
            "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
            "interval": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
            "active": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
            "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
            "rest": {"stepTypeId": 5, "stepTypeKey": "rest", "displayOrder": 5},
            "repeat": {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6},
        }
        
        step_type_info = type_map.get(step_type, {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3})
        
        garmin_step = {
            "type": "ExecutableStepDTO",
            "stepOrder": order,
            "stepType": step_type_info,
            "childStepId": None,
        }
        
        # Set duration
        duration_minutes = step.get("duration_minutes")
        distance_meters = step.get("distance_meters")
        
        if duration_minutes:
            garmin_step["endCondition"] = {
                "conditionTypeId": 2,
                "conditionTypeKey": "time",
                "displayOrder": 2,
                "displayable": True
            }
            garmin_step["endConditionValue"] = float(duration_minutes * 60)  # seconds
        elif distance_meters:
            garmin_step["endCondition"] = {
                "conditionTypeId": 1,
                "conditionTypeKey": "distance",
                "displayOrder": 1,
                "displayable": True
            }
            garmin_step["endConditionValue"] = float(distance_meters)  # meters
        else:
            garmin_step["endCondition"] = {
                "conditionTypeId": 1,
                "conditionTypeKey": "lap.button",
                "displayOrder": 1,
                "displayable": True
            }
            garmin_step["endConditionValue"] = None
        
        # Set target (pace or heart rate)
        target_type = step.get("target_type", "open")
        target_pace_min = step.get("target_pace_min")
        target_hr_zone = step.get("target_hr_zone")
        
        if target_type == "pace" and target_pace_min and isinstance(target_pace_min, str) and ":" in target_pace_min:
            try:
                pace_parts = target_pace_min.split(":")
                if len(pace_parts) == 2:
                    minutes = int(pace_parts[0])
                    seconds = int(pace_parts[1])
                    total_seconds = minutes * 60 + seconds
                    if total_seconds > 0:
                        speed_ms = 1000 / total_seconds
                        speed_ms_low = speed_ms * 0.95
                        
                        target_pace_max = step.get("target_pace_max")
                        if target_pace_max and isinstance(target_pace_max, str) and ":" in target_pace_max:
                            pace_parts_max = target_pace_max.split(":")
                            if len(pace_parts_max) == 2:
                                max_total_seconds = int(pace_parts_max[0]) * 60 + int(pace_parts_max[1])
                                if max_total_seconds > 0:
                                    speed_ms_low = 1000 / max_total_seconds
                        
                        garmin_step["targetType"] = {
                            "workoutTargetTypeId": 4,
                            "workoutTargetTypeKey": "speed.zone",
                            "displayOrder": 4
                        }
                        garmin_step["targetValueOne"] = round(speed_ms_low, 4)
                        garmin_step["targetValueTwo"] = round(speed_ms * 1.05, 4)
            except (ValueError, TypeError):
                pass
        
        if "targetType" not in garmin_step and target_type == "heart_rate" and target_hr_zone:
            garmin_step["targetType"] = {
                "workoutTargetTypeId": 2,
                "workoutTargetTypeKey": "heart.rate.zone",
                "displayOrder": 2
            }
            garmin_step["targetValueOne"] = target_hr_zone
            garmin_step["targetValueTwo"] = None
        
        if "targetType" not in garmin_step:
            garmin_step["targetType"] = {
                "workoutTargetTypeId": 1,
                "workoutTargetTypeKey": "no.target",
                "displayOrder": 1
            }
            garmin_step["targetValueOne"] = None
            garmin_step["targetValueTwo"] = None
        
        # Handle repeat steps
        if step_type == "repeat" and step.get("repeat_steps"):
            garmin_step["type"] = "RepeatGroupDTO"
            garmin_step["numberOfIterations"] = step.get("repeat_count", 1)
            garmin_step["smartRepeat"] = False
            child_steps = []
            for i, child in enumerate(step.get("repeat_steps", [])):
                child_steps.append(self._build_garmin_step_dict(child, i + 1))
            garmin_step["workoutSteps"] = child_steps
        
        return garmin_step
    
    def schedule_workout(self, workout_id: int, schedule_date: str) -> Dict[str, Any]:
        """Schedule a workout for a specific date.
        
        Args:
            workout_id: The ID of the workout to schedule
            schedule_date: Date in YYYY-MM-DD format
        
        Returns:
            Dict with schedule result
        """
        self._ensure_authenticated()
        try:
            # Garmin API for scheduling workouts
            # This creates a scheduled workout entry
            result = self.client.schedule_workout(workout_id, schedule_date)
            return result or {"success": True}
        except AttributeError:
            # Method might not exist in all versions
            return {"error": "Workout scheduling not supported in this version", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    # ==================== Devices ====================
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """Get list of Garmin devices."""
        self._ensure_authenticated()
        try:
            return self.client.get_devices() or []
        except Exception:
            return []
    
    def get_primary_training_device(self) -> Dict[str, Any]:
        """Get primary training device info."""
        self._ensure_authenticated()
        try:
            return self.client.get_primary_training_device() or {}
        except Exception:
            return {}
    
    # ==================== Goals & Badges ====================
    
    def get_goals(self) -> Dict[str, Any]:
        """Get fitness goals."""
        self._ensure_authenticated()
        try:
            return self.client.get_goals() or {}
        except Exception:
            return {}
    
    def get_earned_badges(self) -> List[Dict[str, Any]]:
        """Get earned badges."""
        self._ensure_authenticated()
        try:
            return self.client.get_earned_badges() or []
        except Exception:
            return []
    
    # ==================== Full Health Snapshot ====================
    
    def get_full_health_snapshot(self, snapshot_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get a complete health snapshot for a date, including all available metrics.
        This is useful for AI analysis and dashboard display.
        """
        snapshot_date = snapshot_date or date.today()
        date_str = snapshot_date.strftime("%Y-%m-%d")
        
        snapshot = {
            "date": date_str,
            "daily_stats": {},
            "body_battery": {},
            "sleep": {},
            "stress": {},
            "hrv": {},
            "heart_rate": {},
            "respiration": {},
            "spo2": {},
            "hydration": {},
            "steps": {},
            "floors": {},
            "intensity_minutes": {},
            "training_readiness": {},
            "training_status": {},
        }
        
        # Collect all available data
        try:
            snapshot["daily_stats"] = self.get_stats(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["body_battery"] = self.get_body_battery_detailed(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["sleep"] = self.get_sleep_data(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["stress"] = self.get_stress_data(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["hrv"] = self.get_hrv_data(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["heart_rate"] = self.get_heart_rates(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["respiration"] = self.get_respiration_data(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["spo2"] = self.get_spo2_data(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["hydration"] = self.get_hydration_data(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["steps"] = self.get_steps_data(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["floors"] = self.get_floors_data(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["intensity_minutes"] = self.get_intensity_minutes(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["training_readiness"] = self.get_training_readiness(snapshot_date)
        except Exception:
            pass
        
        try:
            snapshot["training_status"] = self.get_training_status(snapshot_date)
        except Exception:
            pass
        
        return snapshot
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get all performance-related metrics for training planning.
        Includes VO2max, race predictions, training load, etc.
        """
        metrics = {
            "race_predictions": {},
            "endurance_score": {},
            "hill_score": {},
            "max_metrics": {},
            "fitness_age": {},
            "lactate_threshold": {},
            "personal_records": {},
            "hr_zones": {},
        }
        
        today = date.today()
        
        try:
            metrics["race_predictions"] = self.get_race_predictions()
        except Exception:
            pass
        
        try:
            metrics["endurance_score"] = self.get_endurance_score()
        except Exception:
            pass
        
        try:
            metrics["hill_score"] = self.get_hill_score()
        except Exception:
            pass
        
        try:
            metrics["max_metrics"] = self.get_max_metrics(today)
        except Exception:
            pass
        
        try:
            metrics["fitness_age"] = self.get_fitness_age(today)
        except Exception:
            pass
        
        try:
            metrics["lactate_threshold"] = self.get_lactate_threshold()
        except Exception:
            pass
        
        try:
            metrics["personal_records"] = self.get_personal_records()
        except Exception:
            pass
        
        try:
            metrics["hr_zones"] = self.get_hr_zones()
        except Exception:
            pass
        
        return metrics
    
    # ==================== Aggregated Data ====================
    
    def get_comprehensive_data(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive health and activity data for AI context.
        
        Args:
            days: Number of days of history to fetch
            
        Returns:
            Dictionary containing all relevant health data
        """
        self._ensure_authenticated()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        yesterday = end_date - timedelta(days=1)
        
        data = {
            "user_profile": self.get_user_profile(),
            "activities": [],
            "daily_stats": [],
            "sleep_data": [],
            "health_summary": {},
            "activity_summary": {},
            # New comprehensive data
            "body_battery": [],
            "hrv_data": [],
            "stress_data": [],
            "performance_metrics": {},
            "today_readiness": {},
            "personal_records": {},
            "intensity_minutes": {},
            "training_status": {},
        }
        
        try:
            # Fetch activities with enriched details (already enriched in get_activities_by_date)
            activities = self.get_activities_by_date(start_date, end_date)
            data["activities"] = activities
            print(f"[Comprehensive Data] Fetched {len(activities)} activities from {start_date} to {end_date}")
        except Exception as e:
            print(f"[Comprehensive Data] Error fetching activities: {e}")
            traceback.print_exc()
        
        try:
            # Fetch daily stats for recent days (limit to avoid rate limiting)
            for i in range(min(days, 14)):
                current_date = end_date - timedelta(days=i)
                try:
                    stats = self.get_stats(current_date)
                    stats["date"] = current_date.strftime("%Y-%m-%d")
                    data["daily_stats"].append(stats)
                except Exception:
                    pass
        except Exception:
            pass
        
        try:
            # Fetch sleep data for recent days
            for i in range(min(days, 14)):
                current_date = end_date - timedelta(days=i)
                try:
                    sleep = self.get_sleep_data(current_date)
                    sleep["date"] = current_date.strftime("%Y-%m-%d")
                    data["sleep_data"].append(sleep)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Fetch body battery data for trend analysis
        try:
            for i in range(min(days, 7)):
                current_date = end_date - timedelta(days=i)
                try:
                    bb = self.get_body_battery_detailed(current_date)
                    if bb and bb.get("current_value"):
                        data["body_battery"].append(bb)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Fetch HRV data for trend analysis
        try:
            for i in range(min(days, 7)):
                current_date = end_date - timedelta(days=i)
                try:
                    hrv = self.get_hrv_data(current_date)
                    if hrv and isinstance(hrv, dict) and hrv.get("hrvSummary"):
                        hrv["date"] = current_date.strftime("%Y-%m-%d")
                        data["hrv_data"].append(hrv)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Fetch today's readiness
        try:
            data["today_readiness"] = self.get_today_readiness()
        except Exception:
            pass
        
        # Fetch performance metrics (VO2max, fitness age, etc.)
        try:
            max_metrics = self.get_max_metrics(yesterday)
            fitness_age = self.get_fitness_age(yesterday)
            endurance = self.get_endurance_score(yesterday)
            hill_score = self.get_hill_score(yesterday)
            
            data["performance_metrics"] = {
                "vo2_max": max_metrics.get("generic", {}).get("vo2MaxPreciseValue") if max_metrics else None,
                "vo2_max_running": max_metrics.get("cycling", {}).get("vo2MaxPreciseValue") if max_metrics else None,
                "fitness_age": fitness_age.get("chronologicalAge") if fitness_age else None,
                "endurance_score": endurance.get("overallScore") if endurance else None,
                "hill_score": hill_score.get("hillScore") if hill_score else None,
                "training_load_7d": max_metrics.get("generic", {}).get("trainingLoad7d") if max_metrics else None,
                "training_status": max_metrics.get("generic", {}).get("trainingStatus") if max_metrics else None,
                "training_status_description": max_metrics.get("generic", {}).get("trainingStatusDescription") if max_metrics else None,
                "recovery_time_hours": max_metrics.get("generic", {}).get("recoveryTimeInHours") if max_metrics else None,
            }
        except Exception:
            pass
        
        # Fetch personal records
        try:
            data["personal_records"] = self.get_personal_records()
        except Exception:
            pass
        
        # Fetch intensity minutes
        try:
            data["intensity_minutes"] = self.get_intensity_minutes()
        except Exception:
            pass
        
        # Fetch HR zones
        try:
            data["hr_zones"] = self.get_hr_zones()
        except Exception:
            pass
        
        # Calculate summaries from database
        data["health_summary"] = DatabaseManager.get_health_summary(days=7)
        data["health_summary"]["avg_sleep_hours"] = DatabaseManager.get_sleep_summary(days=7).get("avg_sleep_hours", 0)
        data["activity_summary"] = DatabaseManager.get_activity_stats(days=days)
        
        return data
    
    def get_health_metrics_for_ai(self, days: int = 7) -> Dict[str, Any]:
        """Get health metrics formatted for AI prompts."""
        health_summary = DatabaseManager.get_health_summary(days=days)
        sleep_summary = DatabaseManager.get_sleep_summary(days=days)
        activity_stats = DatabaseManager.get_activity_stats(days=days)
        
        return {
            "avg_steps": health_summary.get("avg_steps", 0),
            "avg_resting_hr": health_summary.get("avg_resting_hr", 0),
            "avg_stress": health_summary.get("avg_stress", 0),
            "total_active_minutes": health_summary.get("total_active_minutes", 0),
            "total_calories": health_summary.get("total_calories", 0),
            "avg_sleep_hours": sleep_summary.get("avg_sleep_hours", 0),
            "avg_sleep_score": sleep_summary.get("avg_sleep_score", 0),
            "avg_hrv": sleep_summary.get("avg_hrv", 0),
            "total_activities": activity_stats.get("total_activities", 0),
            "primary_activity": max(
                activity_stats.get("activity_types", {"other": 0}).items(),
                key=lambda x: x[1],
                default=("other", 0)
            )[0] if activity_stats.get("activity_types") else "other",
            "recovery_status": "Good" if health_summary.get("avg_stress", 50) < 40 else "Normal" if health_summary.get("avg_stress", 50) < 60 else "Elevated",
        }


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class DataFetchError(Exception):
    """Raised when data fetching fails."""
    pass
