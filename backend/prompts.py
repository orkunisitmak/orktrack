"""
Structured AI Prompts for the Physiological Engine.

Based on the VDOT/Polarized Training approach with autoregulation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


def safe_format(value, fmt=",") -> str:
    """Safely format a value, handling N/A and None."""
    if value is None or value == 'N/A':
        return 'N/A'
    try:
        if fmt == ",":
            return f"{value:,}"
        elif fmt == ".1f":
            return f"{value:.1f}"
        elif fmt == ".0f":
            return f"{value:.0f}"
        else:
            return str(value)
    except (ValueError, TypeError):
        return str(value) if value else 'N/A'


class PromptEngine:
    """
    Builds structured prompts for AI interactions.
    
    Philosophy:
    1. Polarized Training (80/20): 80% low intensity, 20% high intensity
    2. Jack Daniels VDOT System: All paces mathematically derived from VDOT
    3. Autoregulation: Adjust based on recovery metrics
    """
    
    # VDOT Pace Calculator (approximate)
    VDOT_PACES = {
        # VDOT: (E-pace min/km, M-pace min/km, T-pace min/km, I-pace min/km, R-pace min/km)
        30: ("7:30", "6:40", "6:15", "5:45", "5:15"),
        35: ("6:50", "6:05", "5:40", "5:15", "4:45"),
        40: ("6:20", "5:35", "5:12", "4:48", "4:20"),
        45: ("5:55", "5:12", "4:50", "4:28", "4:00"),
        50: ("5:35", "4:52", "4:30", "4:10", "3:45"),
        55: ("5:18", "4:35", "4:14", "3:54", "3:32"),
        60: ("5:03", "4:20", "4:00", "3:40", "3:20"),
        65: ("4:50", "4:08", "3:48", "3:28", "3:10"),
        70: ("4:38", "3:56", "3:37", "3:18", "3:00"),
    }
    
    @classmethod
    def get_vdot_paces(cls, vdot: float) -> Dict[str, str]:
        """Get training paces for a given VDOT score."""
        vdot_keys = list(cls.VDOT_PACES.keys())
        closest = min(vdot_keys, key=lambda x: abs(x - vdot))
        paces = cls.VDOT_PACES[closest]
        
        return {
            "easy": paces[0],
            "marathon": paces[1],
            "threshold": paces[2],
            "interval": paces[3],
            "repetition": paces[4],
        }
    
    @classmethod
    def build_workout_prompt(
        cls,
        user_profile: Dict[str, Any],
        vdot_score: float,
        primary_goal: str,
        training_phase: str,
        scheduled_workout_type: str,
        health_telemetry: Dict[str, Any],
        activity_history: Dict[str, Any],
    ) -> str:
        """Build a structured workout generation prompt."""
        
        paces = cls.get_vdot_paces(vdot_score)
        
        system_prompt = """### SYSTEM ROLE
You are the "Physiological Engine," an expert AI Running Coach and Exercise Physiologist. Your training philosophy is strictly grounded in:
1. **Polarized Training (80/20):** 80% volume at low intensity, 20% at moderate-to-high.
2. **Jack Daniels VDOT System:** All paces must be mathematically derived from the user's VDOT score.

### OPERATIONAL CONSTRAINTS
1. **Safety First (Autoregulation):** Analyze the User Readiness Data before generating a workout.
   - If `Body Battery` < 30 OR `Sleep Score` < 40: MUST override and prescribe "REST" or "RECOVERY RUN" (Zone 1).
   - If `HRV Status` is "Unbalanced (Low)": MUST reduce intensity (downgrade Intervals to Tempo, or Tempo to Base).
   - If `User RPE/Soreness` > 7: Consider recovery workout.
2. **No Hallucinated Paces:** Output specific pace ranges (e.g., "4:25 - 4:30 min/km") calculated from VDOT.
3. **JSON Output Only:** Output must be valid JSON adhering to the schema below.

### OUTPUT SCHEMA (JSON)
{
  "workout_name": "String",
  "rationale": "Brief chain-of-thought explaining why this workout fits the current physiological state.",
  "autoregulation_applied": true/false,
  "autoregulation_reason": "String or null",
  "total_distance_estimate_km": Number,
  "total_duration_estimate_min": Number,
  "training_zones": {
    "zone1_percent": Number,
    "zone2_percent": Number,
    "zone3_percent": Number,
    "zone4_percent": Number,
    "zone5_percent": Number
  },
  "steps": [
    {
      "type": "warmup | work | recovery | cooldown | rest",
      "description": "String",
      "duration_type": "time | distance",
      "duration_value": "e.g., '10:00' or '1000m'",
      "target_type": "pace | heart_rate_zone | open",
      "target_value_min": "String (min/km)",
      "target_value_max": "String (min/km)",
      "notes": "Optional coaching cues"
    }
  ],
  "post_workout_notes": "Recovery recommendations"
}
"""
        
        user_prompt = f"""### USER CONTEXT
**Profile:**
- Name: {user_profile.get('displayName', 'Athlete')}
- Current VDOT: {vdot_score}
- E-Pace: {paces['easy']} min/km
- M-Pace: {paces['marathon']} min/km
- T-Pace: {paces['threshold']} min/km
- I-Pace: {paces['interval']} min/km
- R-Pace: {paces['repetition']} min/km
- Primary Goal: {primary_goal}
- Training Phase: {training_phase}

**Garmin Health Telemetry (Readiness):**
- Body Battery (0-100): {health_telemetry.get('body_battery', 'N/A')}
- Sleep Score (0-100): {health_telemetry.get('sleep_score', 'N/A')} (Deep Sleep: {health_telemetry.get('deep_sleep_mins', 'N/A')} mins)
- HRV Status: {health_telemetry.get('hrv_status', 'Unknown')}
- Resting Heart Rate: {health_telemetry.get('resting_hr', 'N/A')} bpm (7-day Avg: {health_telemetry.get('resting_hr_avg', 'N/A')} bpm)
- Subjective Soreness (1-10): {health_telemetry.get('user_rpe', 5)}

**Garmin Activity History (Load):**
- Acute Load (7-day): {activity_history.get('acute_load', 'N/A')}
- Chronic Load (28-day): {activity_history.get('chronic_load', 'N/A')}
- Yesterday's Workout TE: Aerobic {activity_history.get('yesterday_te_aerobic', 0)} / Anaerobic {activity_history.get('yesterday_te_anaerobic', 0)}

### INSTRUCTION
Today is scheduled to be a: **{scheduled_workout_type}**
Current Date: {datetime.now().strftime('%A, %B %d, %Y')}

**Task:**
1. Evaluate the Health Telemetry against the Autoregulation Logic.
2. If the user is physiologically compromised (Low Body Battery, Unbalanced HRV, High Soreness), **downgrade** the scheduled workout.
3. If the user is ready, construct the precise workout using VDOT paces.
4. Consider the training phase and adjust volume/intensity accordingly.

Generate the JSON workout file now."""

        return system_prompt + "\n\n" + user_prompt
    
    @classmethod
    def build_insights_prompt(
        cls,
        user_profile: Dict[str, Any],
        health_data: Dict[str, Any],
        sleep_data: List[Dict[str, Any]],
        activities: List[Dict[str, Any]],
        period: str = "week",
        focus_areas: Optional[List[str]] = None,
    ) -> str:
        """Build a structured health insights prompt."""
        
        # Calculate sleep averages safely
        avg_sleep = 0
        avg_deep = 0
        if sleep_data:
            try:
                total_sleep = sum(
                    (s.get("dailySleepDTO", {}).get("sleepTimeSeconds", 0) or 0) / 3600
                    for s in sleep_data
                )
                avg_sleep = total_sleep / len(sleep_data)
                
                total_deep = sum(
                    (s.get("dailySleepDTO", {}).get("deepSleepSeconds", 0) or 0) / 3600
                    for s in sleep_data
                )
                avg_deep = total_deep / len(sleep_data)
            except Exception:
                pass
        
        # Calculate activity metrics safely
        total_activities = len(activities) if activities else 0
        total_duration = 0
        if activities:
            try:
                total_duration = sum(
                    (a.get("duration", 0) or 0) / 60
                    for a in activities
                )
            except Exception:
                pass
        
        system_prompt = """### SYSTEM ROLE
You are a certified Health Coach and Exercise Physiologist specializing in data-driven wellness optimization. 
Analyze the provided health telemetry and provide actionable, personalized insights.

### ANALYSIS FRAMEWORK
1. **Sleep Quality:** Analyze duration, deep sleep %, and consistency
2. **Recovery Status:** Evaluate HRV, resting HR trends, body battery
3. **Training Load:** Assess volume, intensity distribution, and recovery balance
4. **Stress Management:** Identify stress patterns and recommend interventions

### CONSTRAINTS
1. Be specific with numbers and percentages
2. Compare to recommended guidelines (7-9hrs sleep, <60bpm RHR for fit individuals)
3. Provide 2-3 actionable recommendations per area
4. Acknowledge positive trends while addressing areas for improvement
5. Output must be valid JSON

### OUTPUT SCHEMA (JSON)
{
  "overall_score": Number (0-100),
  "overall_assessment": "String summary",
  "period_summary": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "total_activities": Number,
    "total_duration_hours": Number,
    "avg_sleep_hours": Number
  },
  "highlights": [
    {
      "type": "positive | warning | info",
      "category": "sleep | activity | recovery | stress",
      "title": "String",
      "description": "String",
      "metric": "String",
      "value": "String"
    }
  ],
  "sleep_analysis": {
    "quality_rating": "Excellent | Good | Fair | Poor",
    "avg_duration_hours": Number,
    "avg_deep_sleep_hours": Number,
    "consistency_score": Number,
    "insights": ["String"],
    "recommendations": ["String"]
  },
  "activity_analysis": {
    "consistency_rating": "Excellent | Good | Fair | Poor",
    "volume_trend": "increasing | stable | decreasing",
    "intensity_distribution": {
      "low": Number,
      "moderate": Number,
      "high": Number
    },
    "insights": ["String"],
    "recommendations": ["String"]
  },
  "recovery_analysis": {
    "status": "Excellent | Good | Fair | Needs Attention",
    "avg_resting_hr": Number,
    "hrv_trend": "improving | stable | declining",
    "insights": ["String"],
    "recommendations": ["String"]
  },
  "weekly_focus": "String - One key area to prioritize",
  "motivational_message": "String - Personalized encouragement"
}
"""

        focus_str = ", ".join(focus_areas) if focus_areas else "Overall health and fitness"
        
        # Safely format health data values
        avg_steps = safe_format(health_data.get('avg_steps', 0))
        total_steps = safe_format(health_data.get('total_steps', 0))
        avg_rhr = health_data.get('avg_resting_hr') or 'N/A'
        avg_stress = health_data.get('avg_stress') or 'N/A'
        active_mins = safe_format(health_data.get('total_active_minutes', 0))
        total_cals = safe_format(health_data.get('total_calories', 0))
        
        user_prompt = f"""### USER CONTEXT
**Profile:**
- Name: {user_profile.get('displayName', 'Athlete')}

**Analysis Period:** Last {period} ({7 if period == 'week' else 30} days)
**Focus Areas:** {focus_str}
**Generated:** {datetime.now().strftime('%A, %B %d, %Y')}

**Health Metrics Summary:**
- Average Daily Steps: {avg_steps}
- Total Steps: {total_steps}
- Average Resting HR: {avg_rhr} bpm
- Average Stress Level: {avg_stress}/100
- Total Active Minutes: {active_mins}
- Total Calories Burned: {total_cals}

**Sleep Summary:**
- Average Sleep Duration: {avg_sleep:.1f} hours
- Average Deep Sleep: {avg_deep:.1f} hours
- Data Points: {len(sleep_data) if sleep_data else 0} nights

**Activity Summary:**
- Total Workouts: {total_activities}
- Total Duration: {total_duration:.0f} minutes
- Most Common Type: {_get_most_common_activity(activities)}

### INSTRUCTION
Analyze the health data and generate comprehensive insights following the JSON schema.
Focus on actionable recommendations that will help improve overall fitness and well-being.
Be encouraging but honest about areas needing improvement.

Generate the JSON insights now."""

        return system_prompt + "\n\n" + user_prompt
    
    @classmethod
    def build_chat_context_prompt(
        cls,
        user_profile: Dict[str, Any],
        health_summary: Dict[str, Any],
        recent_activities: List[Dict[str, Any]],
        user_query: str,
    ) -> str:
        """Build a context-rich chat prompt with FULL activity details."""
        
        system_prompt = """### SYSTEM ROLE
You are OrkTrack AI, an expert fitness coach integrated into a Garmin activity dashboard.
You have access to the user's COMPLETE health and fitness data including ALL activity details.

### CAPABILITIES
- Analyze workout patterns and performance trends with specific metrics
- Provide personalized training recommendations based on actual heart rate, pace, and power data
- Offer insights on sleep, recovery, and stress using Garmin metrics
- Help users understand their heart rate zones, training effect, and VO2max
- Create customized workout suggestions based on historical performance
- Identify areas for improvement while celebrating achievements
- Count and analyze activities by type, month, or any time period

### GUIDELINES
1. Be encouraging and supportive while honest about areas for improvement
2. Base all recommendations on actual data - reference specific numbers
3. When asked about activity counts, CAREFULLY count from the provided data
4. Use specific numbers, percentages, and comparisons
5. Always verify counts by looking at the actual activity list provided
6. When discussing activities, reference specific metrics like avg HR, max HR, pace, distance, elevation
7. For date-based questions, use the startTimeLocal field to determine when activities occurred

### IMPORTANT
- For medical concerns, always recommend consulting a healthcare professional.
- ALWAYS count activities from the actual data provided - do not estimate.
"""

        # Define activity type groups for better categorization
        RUNNING_TYPES = {'running', 'treadmill_running', 'trail_running', 'track_running', 'ultra_run', 'virtual_run'}
        CYCLING_TYPES = {'cycling', 'indoor_cycling', 'virtual_cycling', 'mountain_biking', 'gravel_cycling'}
        STRENGTH_TYPES = {'strength_training', 'functional_strength', 'hiit'}
        CARDIO_TYPES = {'indoor_cardio', 'elliptical', 'stair_climbing', 'rowing'}
        
        def get_activity_category(atype: str) -> str:
            if atype in RUNNING_TYPES:
                return 'running (all types)'
            elif atype in CYCLING_TYPES:
                return 'cycling (all types)'
            elif atype in STRENGTH_TYPES:
                return 'strength training'
            elif atype in CARDIO_TYPES:
                return 'cardio'
            return atype
        
        # Organize activities by type and month
        activity_by_type: Dict[str, List] = {}
        activity_by_category: Dict[str, List] = {}
        activity_by_month: Dict[str, List] = {}
        
        for a in recent_activities:
            if not isinstance(a, dict):
                continue
            atype = a.get('activityType', {}).get('typeKey', 'other') if isinstance(a.get('activityType'), dict) else 'other'
            category = get_activity_category(atype)
            
            if atype not in activity_by_type:
                activity_by_type[atype] = []
            activity_by_type[atype].append(a)
            
            if category not in activity_by_category:
                activity_by_category[category] = []
            activity_by_category[category].append(a)
            
            # Parse month
            start_time = a.get('startTimeLocal', '')
            if start_time:
                try:
                    month_key = start_time[:7]  # YYYY-MM format
                    if month_key not in activity_by_month:
                        activity_by_month[month_key] = []
                    activity_by_month[month_key].append(a)
                except Exception:
                    pass
        
        # Build activity summary by category (grouped types)
        category_summary = ""
        for cat, acts in sorted(activity_by_category.items(), key=lambda x: -len(x[1])):
            category_summary += f"- {cat}: {len(acts)} activities\n"
        
        # Build activity summary by specific type
        type_summary = ""
        for atype, acts in sorted(activity_by_type.items(), key=lambda x: -len(x[1])):
            type_summary += f"- {atype}: {len(acts)}\n"
        
        # Build activity summary by month with category counts
        month_summary = ""
        for month, acts in sorted(activity_by_month.items(), reverse=True):
            # Count by category within month
            month_cats: Dict[str, int] = {}
            for a in acts:
                t = a.get('activityType', {}).get('typeKey', 'other') if isinstance(a.get('activityType'), dict) else 'other'
                cat = get_activity_category(t)
                month_cats[cat] = month_cats.get(cat, 0) + 1
            
            cat_breakdown = ", ".join([f"{v} {k}" for k, v in sorted(month_cats.items(), key=lambda x: -x[1])])
            month_summary += f"- {month}: {len(acts)} total ({cat_breakdown})\n"

        # Format ALL activities with details (not just 10)
        activities_summary = ""
        if recent_activities:
            for i, a in enumerate(recent_activities):
                if not isinstance(a, dict):
                    continue
                    
                activity_type = 'other'
                if isinstance(a.get('activityType'), dict):
                    activity_type = a.get('activityType', {}).get('typeKey', 'other')
                
                activity_name = a.get('activityName', activity_type)
                duration_mins = (a.get('duration', 0) or 0) / 60
                distance_km = (a.get('distance', 0) or 0) / 1000
                calories = a.get('calories', 0) or 0
                avg_hr = a.get('averageHR') or a.get('averageHeartRate') or 'N/A'
                max_hr = a.get('maxHR') or a.get('maxHeartRate') or 'N/A'
                elevation = a.get('elevationGain', 0) or 0
                te_aerobic = a.get('aerobicTrainingEffect') or a.get('trainingEffectAerobic') or 'N/A'
                te_anaerobic = a.get('anaerobicTrainingEffect') or a.get('trainingEffectAnaerobic') or 'N/A'
                start_time = a.get('startTimeLocal', 'Unknown date')
                
                # Calculate pace if running/walking
                pace_str = ""
                if distance_km > 0 and duration_mins > 0 and activity_type in ['running', 'walking', 'trail_running', 'treadmill_running']:
                    pace = duration_mins / distance_km
                    pace_mins = int(pace)
                    pace_secs = int((pace - pace_mins) * 60)
                    pace_str = f", Pace: {pace_mins}:{pace_secs:02d}/km"
                
                activities_summary += f"{i+1}. [{start_time}] {activity_name} ({activity_type}) - {duration_mins:.0f}min, {distance_km:.2f}km, HR: {avg_hr}/{max_hr}, TE: {te_aerobic}/{te_anaerobic}{pace_str}\n"
        else:
            activities_summary = "No activities recorded."

        # Format health summary with safe values
        avg_steps = safe_format(health_summary.get('avg_steps', 0))
        avg_rhr = health_summary.get('avg_resting_hr') or 'N/A'
        avg_sleep = health_summary.get('avg_sleep_hours') or 'N/A'
        avg_stress = health_summary.get('avg_stress') or 'N/A'
        active_mins = safe_format(health_summary.get('total_active_minutes', 0))
        total_cals = safe_format(health_summary.get('total_calories', 0))
        avg_hrv = health_summary.get('avg_hrv') or 'N/A'
        recovery = health_summary.get('recovery_status', 'Unknown')

        user_prompt = f"""### USER CONTEXT
**Profile:** {user_profile.get('displayName', 'User')}
**Current Date:** {datetime.now().strftime('%A, %B %d, %Y')}

**Health Summary (Last 30 Days):**
- Average Daily Steps: {avg_steps}
- Average Resting HR: {avg_rhr} bpm
- Average Sleep Duration: {avg_sleep} hours
- Average Stress Level: {avg_stress}/100
- Total Active Minutes: {active_mins}
- Total Calories Burned: {total_cals}
- Average HRV: {avg_hrv}
- Recovery Status: {recovery}

**Activity Summary by Category (grouped):**
Total Activities: {len(recent_activities)}
{category_summary}

**Activity Summary by Specific Type:**
{type_summary}

**Activity Summary by Month:**
{month_summary}

**Complete Activity List ({len(recent_activities)} activities):**
{activities_summary}

---

### USER QUESTION
{user_query}

---

Provide a helpful, personalized response based on the user's complete data. Be specific and reference actual numbers. When counting activities, use the exact data provided above - count carefully from the activity list."""

        return system_prompt + "\n\n" + user_prompt


    # Supplementary activities with optimal timing guidelines
    SUPPLEMENTARY_TIMING = {
        "wim_hof": {
            "name": "Wim Hof Breathing",
            "optimal_time": "Morning (fasted) OR 2 hours before bed",
            "duration": "15-20 minutes",
            "frequency": "Daily or every other day",
            "avoid": "Immediately before intense workouts",
            "benefits": "Stress reduction, focus, cold tolerance prep"
        },
        "mobility": {
            "name": "Mobility Work",
            "optimal_time": "Morning wake-up routine OR as pre-workout warm-up",
            "duration": "10-15 minutes",
            "frequency": "Daily",
            "avoid": "As sole recovery after hard sessions",
            "benefits": "Injury prevention, range of motion, movement quality"
        },
        "yoga": {
            "name": "Yoga / Extended Stretching",
            "optimal_time": "Evening (6+ hours after intense workout) OR rest days",
            "duration": "30-60 minutes",
            "frequency": "2-3x per week",
            "avoid": "Immediately after hard running (may impair adaptation)",
            "benefits": "Flexibility, parasympathetic activation, recovery"
        },
        "cold_plunge": {
            "name": "Cold Plunge / Ice Bath",
            "optimal_time": "6+ hours after strength/hard running OR morning on easy days",
            "duration": "2-5 minutes at 10-15°C",
            "frequency": "2-4x per week",
            "avoid": "Within 4 hours after strength training (blunts hypertrophy)",
            "benefits": "Inflammation reduction, mental resilience, recovery"
        },
        "gym": {
            "name": "Gym / Strength Training",
            "optimal_time": "Separate day from hard running OR 6+ hours gap (AM run, PM gym)",
            "duration": "45-60 minutes",
            "frequency": "2-3x per week",
            "avoid": "Same day as intervals/tempo if <6h gap",
            "benefits": "Running economy, injury prevention, power"
        }
    }
    
    @classmethod
    def build_week_plan_prompt(
        cls,
        user_profile: Dict[str, Any],
        primary_goal: str,
        estimated_vdot: float,
        training_phase: str,
        health_metrics: Dict[str, Any],
        recent_activities: List[Dict[str, Any]],
        activity_summary: Dict[str, Any],
        today_readiness: Optional[Dict[str, Any]] = None,
        hr_zones: Optional[Dict[str, Any]] = None,
        supplementary_activities: Optional[List[str]] = None,
        supplementary_frequency: Optional[Dict[str, int]] = None,
        goal_time: Optional[str] = None,
        goal_distance_km: Optional[float] = None,
    ) -> str:
        """
        Build a prompt for generating a full week training plan.
        
        IMPORTANT: Autoregulation is applied ONLY to TODAY's workout.
        Future days are planned at baseline intensity - they will be
        adjusted each day based on that day's readiness.
        
        Based on the Physiological Engine approach with:
        - Polarized Training (80/20)
        - Jack Daniels VDOT System
        - DAILY Autoregulation (not weekly)
        """
        
        paces = cls.get_vdot_paces(estimated_vdot)
        today_readiness = today_readiness or {}
        hr_zones = hr_zones or {}
        supplementary_activities = supplementary_activities or []
        supplementary_frequency = supplementary_frequency or {}
        
        # Calculate training load from recent activities
        acute_load = 0
        chronic_load = 0
        yesterday_te_aerobic = 0
        yesterday_te_anaerobic = 0
        load_focus = "Balanced"
        
        if recent_activities:
            # Acute load (last 7 days)
            for a in recent_activities[:7]:
                acute_load += (a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic") or 0)
            
            # Chronic load (estimate from activities)
            for a in recent_activities:
                chronic_load += (a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic") or 0)
            chronic_load = chronic_load / max(len(recent_activities) / 7, 1)  # Weekly average
            
            # Yesterday's workout
            if recent_activities:
                yesterday_te_aerobic = recent_activities[0].get("aerobicTrainingEffect") or recent_activities[0].get("trainingEffectAerobic") or 0
                yesterday_te_anaerobic = recent_activities[0].get("anaerobicTrainingEffect") or recent_activities[0].get("trainingEffectAnaerobic") or 0
            
            # Determine load focus
            total_anaerobic = sum(a.get("anaerobicTrainingEffect") or a.get("trainingEffectAnaerobic") or 0 for a in recent_activities[:7])
            total_aerobic = sum(a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic") or 0 for a in recent_activities[:7])
            
            if total_anaerobic < total_aerobic * 0.15:
                load_focus = "Anaerobic Shortage"
            elif total_aerobic < 15:
                load_focus = "High Aerobic Shortage"
            else:
                load_focus = "Balanced"
        
        # Format recent activities
        activities_text = ""
        if recent_activities:
            for a in recent_activities[:7]:
                atype = a.get("activityType", {}).get("typeKey", "activity") if isinstance(a.get("activityType"), dict) else "activity"
                name = a.get("activityName", atype)
                duration = (a.get("duration", 0) or 0) / 60
                distance = (a.get("distance", 0) or 0) / 1000
                te_aer = a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic") or 0
                te_ana = a.get("anaerobicTrainingEffect") or a.get("trainingEffectAnaerobic") or 0
                activities_text += f"  - {name}: {duration:.0f}min, {distance:.1f}km, TE: {te_aer:.1f}/{te_ana:.1f}\n"
        else:
            activities_text = "  No recent activities"
        
        # Format HR zones if available
        hr_zones_text = ""
        if hr_zones and hr_zones.get("zones"):
            zones = hr_zones["zones"]
            max_hr = hr_zones.get("max_hr", 185)
            hr_zones_text = f"""
**Heart Rate Zones (Max HR: {max_hr} bpm):**
- Zone 1 (Recovery): {zones.get('zone1', {}).get('min_bpm', 93)}-{zones.get('zone1', {}).get('max_bpm', 111)} bpm
- Zone 2 (Aerobic): {zones.get('zone2', {}).get('min_bpm', 111)}-{zones.get('zone2', {}).get('max_bpm', 130)} bpm
- Zone 3 (Tempo): {zones.get('zone3', {}).get('min_bpm', 130)}-{zones.get('zone3', {}).get('max_bpm', 148)} bpm
- Zone 4 (Threshold): {zones.get('zone4', {}).get('min_bpm', 148)}-{zones.get('zone4', {}).get('max_bpm', 167)} bpm
- Zone 5 (VO2max): {zones.get('zone5', {}).get('min_bpm', 167)}-{zones.get('zone5', {}).get('max_bpm', 185)} bpm
"""
        
        # Determine TODAY's adjustment only
        today_day = datetime.now().strftime('%A')
        today_adjustment = ""
        today_should_rest = today_readiness.get("should_rest", False)
        today_reduce_intensity = today_readiness.get("should_reduce_intensity", False)
        today_adjustment_reason = today_readiness.get("adjustment_reason", "")
        
        if today_should_rest:
            today_adjustment = f"\n⚠️ **TODAY ({today_day}) OVERRIDE:** {today_adjustment_reason}\nToday's scheduled workout MUST be REST or RECOVERY RUN only."
        elif today_reduce_intensity:
            today_adjustment = f"\n⚠️ **TODAY ({today_day}) ADJUSTMENT:** {today_adjustment_reason}\nToday's scheduled workout should be REDUCED INTENSITY (no intervals, easy pace only)."
        
        # Format supplementary activities with user-specified frequency
        supplementary_text = ""
        if supplementary_activities:
            supplementary_list = []
            for act_id in supplementary_activities:
                if act_id in cls.SUPPLEMENTARY_TIMING:
                    act = cls.SUPPLEMENTARY_TIMING[act_id]
                    user_freq = supplementary_frequency.get(act_id, 7)  # Default to daily if not specified
                    freq_text = "Every day" if user_freq == 7 else f"{user_freq}x per week"
                    supplementary_list.append(
                        f"- **{act['name']}**: {act['duration']}, **{freq_text}** (user requested)\n"
                        f"  Optimal: {act['optimal_time']}\n"
                        f"  Avoid: {act['avoid']}\n"
                        f"  Benefits: {act['benefits']}"
                    )
            supplementary_text = "\n".join(supplementary_list)
            supplementary_text += "\n\n**IMPORTANT:** Schedule these activities with optimal timing. Include them in the daily workout plan with specific time recommendations (Morning, Pre-workout, Evening 6h+ post-run, etc.)."
        else:
            supplementary_text = "None selected - focus on running workouts only."
        
        # =====================================================
        # SYSTEM PROMPT - Based on prompt.txt Physiological Engine
        # =====================================================
        system_prompt = """### SYSTEM ROLE
You are the "Physiological Engine," an expert AI Running Coach and Exercise Physiologist. Your training philosophy is strictly grounded in two methodologies:
1. **Polarized Training (80/20):** 80% volume at low intensity, 20% at moderate-to-high.
2. **Jack Daniels VDOT System:** All paces must be mathematically derived from the user's VDOT score.

### CRITICAL: AUTOREGULATION IS DAILY, NOT WEEKLY
Body Battery, Sleep Score, and HRV are **daily metrics**. They affect TODAY's workout only.
- Generate a BASELINE week plan based on the training goal and recent load
- Apply autoregulation ONLY to TODAY's workout based on current readiness
- Future days should be planned at normal intensity - they will be adjusted each morning

### AUTOREGULATION RULES (APPLY TO TODAY ONLY)
- If TODAY's `Body Battery` < 30 OR `Sleep Score` < 40: Override TODAY's workout to REST/RECOVERY
- If TODAY's `HRV Status` is "Unbalanced": Reduce TODAY's intensity only
- Future days are NOT affected - they're re-evaluated each day

### MANDATORY: SPECIFIC PACES FOR ALL WORKOUTS
- **INTERVALS MUST HAVE EXACT PACE TARGETS** - e.g., "6 x 800m @ 4:28-4:30/km with 400m jog recovery"
- **TEMPO RUNS MUST HAVE PACE RANGES** - e.g., "20 minutes @ 4:50-4:55/km"
- **EASY RUNS MUST HAVE PACE GUIDANCE** - e.g., "45 minutes @ 5:55-6:10/km"
- NEVER use vague terms like "hard", "moderate effort", or "comfortably hard" without specific paces

### VDOT PACE REFERENCE
- **E-Pace (Easy):** 59-74% VO2max. Warmup, Cooldown, Long Runs, Recovery.
- **M-Pace (Marathon):** 75-84% VO2max. Steady state aerobic conditioning.
- **T-Pace (Threshold):** 83-88% VO2max. ~1-hour race pace.
- **I-Pace (Interval):** 95-100% VO2max. VO2max development.
- **R-Pace (Repetition):** >100% VO2max. Running economy/speed.

### SUPPLEMENTARY ACTIVITIES TIMING (CRITICAL for optimal results)
When the user includes supplementary activities, schedule them with OPTIMAL TIMING:

- **Wim Hof Breathing:** Morning (fasted) OR 2h before bed. AVOID before intense workouts. 15-20min.
- **Mobility Work:** Morning wake-up OR pre-workout warm-up. Daily, 10-15min.
- **Yoga/Stretching:** Evening 6+ hours after intense workout, or on rest days. 30-60min, 2-3x/week.
- **Cold Plunge:** 6+ hours after strength/running, OR morning on easy days. AVOID within 4h of strength training (blunts hypertrophy). 2-5min.
- **Gym/Strength:** Separate day from hard running OR 6+ hours gap (AM run, PM gym). 45-60min, 2-3x/week.

### OUTPUT SCHEMA (JSON)
{
  "plan_name": "String - Week Plan Name",
  "rationale": "Brief explanation of the week's structure and how it fits the goal.",
  "today_autoregulation": {
    "applied": true/false,
    "reason": "String explaining TODAY's adjustment only, or null if none",
    "original_workout": "String - what was scheduled for today before adjustment",
    "adjusted_workout": "String - what today's workout is now (if adjusted)"
  },
  "weekly_summary": {
    "total_workouts": Number,
    "total_duration_hours": Number,
    "estimated_distance_km": Number,
    "rest_days": Number
  },
  "intensity_distribution": {
    "low": Number (percentage, target ~80%),
    "moderate": Number (percentage),
    "high": Number (percentage)
  },
  "workouts": [
    {
      "day": "Monday",
      "title": "Workout Title",
      "type": "easy_run | tempo | interval | long_run | recovery | rest | strength | wim_hof | mobility | yoga | cold_plunge | gym",
      "is_today": true/false,
      "today_adjusted": true/false (only for today's workout if autoregulation applied),
      "duration_minutes": Number,
      "estimated_distance_km": Number or null,
      "intensity": "low | moderate | high",
      "description": "MUST include SPECIFIC PACES like '4:28/km' for runs, specific timing for supplementary activities",
      "key_focus": "Primary training benefit",
      "target_hr_zone": "Zone 1-2 / Zone 3 / Zone 4-5",
      "target_hr_bpm": "e.g., 130-145 bpm" (if HR zones provided),
      "optimal_time": "Morning | Afternoon | Evening | Post-run (6h+) | Pre-workout" (for supplementary activities),
      "steps": [
        {
          "type": "warmup | work | recovery | cooldown",
          "description": "Step with SPECIFIC PACE",
          "duration_value": "e.g., '10:00' or '800m'",
          "target_pace_min": "min/km (REQUIRED for run workouts)",
          "target_pace_max": "min/km (REQUIRED for run workouts)",
          "target_hr_bpm": "e.g., 150-160 bpm" (optional)
        }
      ],
      "supplementary": [
        {
          "type": "wim_hof | mobility | yoga | cold_plunge | gym",
          "timing": "Morning | Pre-workout | Evening (6h+ post-run) | Rest day",
          "duration_minutes": Number,
          "notes": "Specific instructions"
        }
      ]
    }
  ],
  "weekly_goals": ["Goal 1", "Goal 2", "Goal 3"],
  "recovery_recommendations": "String with specific recovery advice",
  "daily_adjustment_note": "Reminder that each day's workout will be re-evaluated based on that morning's readiness",
  "supplementary_schedule": {
    "wim_hof": ["Monday AM", "Wednesday AM", "Friday AM"],
    "mobility": ["Daily AM"],
    "yoga": ["Tuesday PM", "Thursday PM", "Sunday"],
    "cold_plunge": ["Post-long run (6h+)", "Rest day morning"],
    "gym": ["Monday PM (6h post-run)", "Thursday PM"]
  }
}
"""

        # =====================================================
        # USER PROMPT - Based on prompt.txt dynamic injection
        # =====================================================
        # Build goal info
        goal_info = ""
        if goal_time and goal_distance_km:
            race_names = {5: "5K", 10: "10K", 21.0975: "Half Marathon", 42.195: "Marathon"}
            race_name = race_names.get(goal_distance_km, f"{goal_distance_km}km")
            goal_info = f"""
**🎯 TARGET GOAL:**
- Race: {race_name}
- Target Time: {goal_time}
- Distance: {goal_distance_km} km
- Required VDOT: {estimated_vdot}
- ALL TRAINING PACES ARE CALCULATED TO ACHIEVE THIS GOAL TIME
"""
        
        user_prompt = f"""### USER CONTEXT
**Profile:**
- Name: {user_profile.get('displayName', 'Athlete')}
- Current VDOT: {estimated_vdot}
- Implied T-Pace: {paces['threshold']} min/km
- Primary Goal: {primary_goal}
- Training Phase: {training_phase}
{goal_info}

**VDOT-Calculated Training Paces (USE THESE EXACT PACES):**
- E-Pace (Easy/Recovery): {paces['easy']} min/km
- M-Pace (Marathon): {paces['marathon']} min/km  
- T-Pace (Threshold): {paces['threshold']} min/km
- I-Pace (Interval): {paces['interval']} min/km
- R-Pace (Repetition): {paces['repetition']} min/km
{hr_zones_text}
**TODAY's Readiness ({today_day}):**
- Body Battery: {today_readiness.get('body_battery', 'N/A')}/100
- Sleep Score: {today_readiness.get('sleep_score', 'N/A')}/100
- HRV Status: {today_readiness.get('hrv_status', 'Unknown')}
- Resting HR: {today_readiness.get('resting_hr', 'N/A')} bpm
- Readiness Score: {today_readiness.get('readiness_score', 50)}/100
{today_adjustment}

**Recent Training Load (for baseline planning):**
- Acute Load (7-day TE): {acute_load:.1f}
- Chronic Load (avg weekly): {chronic_load:.1f}
- Load Focus: {load_focus}
- Yesterday's TE: Aerobic {yesterday_te_aerobic:.1f} / Anaerobic {yesterday_te_anaerobic:.1f}
- Weekly Volume: {activity_summary.get('avg_weekly_volume', {}).get('duration_minutes', 0):.0f} min

**Recent Workouts (last 7):**
{activities_text}

### INSTRUCTION
Generate a complete **7-day training week** starting from **{today_day}** for the goal: **{primary_goal}**
Current Date: {datetime.now().strftime('%A, %B %d, %Y')}

**SUPPLEMENTARY ACTIVITIES REQUESTED:**
{supplementary_text}

**CRITICAL REQUIREMENTS:**
1. **TODAY'S WORKOUT:** Apply autoregulation based on today's readiness data
   - If today requires rest/recovery, adjust only today's workout
   - Mark today's workout with "is_today": true
2. **FUTURE DAYS:** Plan at baseline intensity - they will be re-evaluated daily
3. **ALL RUNNING WORKOUTS MUST HAVE SPECIFIC PACES:**
   - Intervals: "6 x 800m @ {paces['interval']}/km with 400m jog @ {paces['easy']}/km"
   - Tempo: "20 min @ {paces['threshold']}/km"
   - Easy: "45 min @ {paces['easy']}/km"
4. Ensure 80/20 polarized distribution across the week
5. Include 1-2 complete rest or recovery days
6. Address any load focus issues (e.g., Anaerobic Shortage)

Generate the JSON week plan now."""

        return system_prompt + "\n\n" + user_prompt
    
    @classmethod
    def build_month_plan_prompt(
        cls,
        user_profile: Dict[str, Any],
        primary_goal: str,
        estimated_vdot: float,
        training_phase: str,
        health_metrics: Dict[str, Any],
        recent_activities: List[Dict[str, Any]],
        activity_summary: Dict[str, Any],
        target_race_date: Optional[str] = None,
        hr_zones: Optional[Dict[str, Any]] = None,
        supplementary_activities: Optional[List[str]] = None,
        supplementary_frequency: Optional[Dict[str, int]] = None,
        goal_time: Optional[str] = None,
        goal_distance_km: Optional[float] = None,
    ) -> str:
        """
        Build a prompt for generating a 4-week training plan (mesocycle).
        """
        
        paces = cls.get_vdot_paces(estimated_vdot)
        hr_zones = hr_zones or {}
        supplementary_activities = supplementary_activities or []
        supplementary_frequency = supplementary_frequency or {}
        
        # Calculate training metrics
        acute_load = 0
        chronic_load = 0
        
        if recent_activities:
            for a in recent_activities[:7]:
                acute_load += (a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic") or 0)
            for a in recent_activities:
                chronic_load += (a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic") or 0)
            chronic_load = chronic_load / max(len(recent_activities) / 7, 1)
        
        # Format recent activities
        activities_text = ""
        if recent_activities:
            for a in recent_activities[:7]:
                atype = a.get("activityType", {}).get("typeKey", "activity") if isinstance(a.get("activityType"), dict) else "activity"
                name = a.get("activityName", atype)
                duration = (a.get("duration", 0) or 0) / 60
                distance = (a.get("distance", 0) or 0) / 1000
                te_aer = a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic") or 0
                activities_text += f"  - {name}: {duration:.0f}min, {distance:.1f}km, TE: {te_aer:.1f}\n"
        else:
            activities_text = "  No recent activities"
        
        # Format HR zones
        hr_zones_text = ""
        if hr_zones and hr_zones.get("zones"):
            zones = hr_zones["zones"]
            max_hr = hr_zones.get("max_hr", 185)
            hr_zones_text = f"""
**Heart Rate Zones (Max HR: {max_hr} bpm):**
- Zone 1: {zones.get('zone1', {}).get('min_bpm', 93)}-{zones.get('zone1', {}).get('max_bpm', 111)} bpm
- Zone 2: {zones.get('zone2', {}).get('min_bpm', 111)}-{zones.get('zone2', {}).get('max_bpm', 130)} bpm
- Zone 3: {zones.get('zone3', {}).get('min_bpm', 130)}-{zones.get('zone3', {}).get('max_bpm', 148)} bpm
- Zone 4: {zones.get('zone4', {}).get('min_bpm', 148)}-{zones.get('zone4', {}).get('max_bpm', 167)} bpm
- Zone 5: {zones.get('zone5', {}).get('min_bpm', 167)}-{zones.get('zone5', {}).get('max_bpm', 185)} bpm
"""
        
        race_info = f"\n**Target Race Date:** {target_race_date}" if target_race_date else ""
        
        # Build goal info for month plan
        goal_info = ""
        if goal_time and goal_distance_km:
            race_names = {5: "5K", 10: "10K", 21.0975: "Half Marathon", 42.195: "Marathon"}
            race_name = race_names.get(goal_distance_km, f"{goal_distance_km}km")
            goal_info = f"""
**🎯 TARGET GOAL:**
- Race: {race_name}
- Target Time: {goal_time}
- Required VDOT: {estimated_vdot}
- ALL TRAINING PACES MUST TARGET THIS GOAL TIME
"""
        
        # Format supplementary activities for month plan with user-specified frequency
        supplementary_text = ""
        if supplementary_activities:
            supplementary_list = []
            for act_id in supplementary_activities:
                if act_id in cls.SUPPLEMENTARY_TIMING:
                    act = cls.SUPPLEMENTARY_TIMING[act_id]
                    user_freq = supplementary_frequency.get(act_id, 7)  # Default to daily if not specified
                    freq_text = "Every day" if user_freq == 7 else f"{user_freq}x per week"
                    supplementary_list.append(
                        f"- **{act['name']}**: {act['duration']}, **{freq_text}** (user requested)\n"
                        f"  Optimal: {act['optimal_time']}"
                    )
            supplementary_text = "\n".join(supplementary_list)
        
        system_prompt = """### SYSTEM ROLE
You are the "Physiological Engine," generating a 4-WEEK MESOCYCLE training plan.

### TRAINING PHILOSOPHY
1. **Polarized Training (80/20):** 80% low intensity, 20% moderate-to-high
2. **Jack Daniels VDOT System:** All paces mathematically derived from VDOT
3. **Progressive Overload:** Weeks 1-3 build, Week 4 recovery
4. **Periodization:** Each week has a specific focus within the mesocycle

### MESOCYCLE STRUCTURE
- **Week 1:** Foundation - Establish base rhythm, moderate volume
- **Week 2:** Build - Increase volume 10-15%, introduce quality sessions
- **Week 3:** Peak - Highest volume/intensity of the block
- **Week 4:** Recovery - Reduce volume 40-50%, maintain intensity

### MANDATORY: SPECIFIC PACES
ALL running workouts MUST have exact paces from VDOT - no vague descriptions.

### OUTPUT SCHEMA (JSON) - CRITICAL: EACH WEEK MUST HAVE EXACTLY 7 WORKOUTS (Mon-Sun)
{
  "plan_name": "4-Week Mesocycle: [Goal]",
  "mesocycle_overview": "Description of the 4-week training block focus",
  "weeks": [
    {
      "week_number": 1,
      "week_focus": "Foundation / Build / Peak / Recovery",
      "total_workouts": 7,
      "total_duration_hours": Number,
      "total_distance_km": Number,
      "intensity_distribution": {"low": 80, "moderate": 10, "high": 10},
      "key_sessions": ["Session 1 description with pace", "Session 2"],
      "workouts": [
        // MANDATORY: Include ALL 7 days (Monday through Sunday)
        {"day": "Monday", "title": "...", "type": "...", "duration_minutes": N, ...},
        {"day": "Tuesday", "title": "...", "type": "...", "duration_minutes": N, ...},
        {"day": "Wednesday", "title": "...", "type": "...", "duration_minutes": N, ...},
        {"day": "Thursday", "title": "...", "type": "...", "duration_minutes": N, ...},
        {"day": "Friday", "title": "...", "type": "...", "duration_minutes": N, ...},
        {"day": "Saturday", "title": "...", "type": "...", "duration_minutes": N, ...},
        {"day": "Sunday", "title": "...", "type": "...", "duration_minutes": N, ...}
      ]
    },
    // Repeat for weeks 2, 3, 4 - EACH with 7 workouts
  ],
  "progression_notes": "How the weeks build upon each other",
  "key_workouts_explained": "Explanation of the most important sessions",
  "recovery_protocol": "Weekly and monthly recovery recommendations",
  "adaptation_guidelines": "How to adjust based on daily readiness"
}

### WORKOUT OBJECT SCHEMA
{
  "day": "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday",
  "title": "Workout Title",
  "type": "easy_run | tempo | interval | long_run | recovery | rest | strength | yoga | breathing | cold_plunge",
  "duration_minutes": Number,
  "estimated_distance_km": Number (0 for non-running),
  "intensity": "low | moderate | high",
  "description": "Detailed description with SPECIFIC PACES for running",
  "target_hr_zone": "Zone X-Y",
  "steps": [
    {"type": "warmup|work|recovery|cooldown", "description": "...", "duration_minutes": N, "target_pace_min": "X:XX", "target_pace_max": "X:XX"}
  ],
  "supplementary": [
    {"activity": "wim_hof|mobility|yoga|cold_plunge|gym", "timing": "morning|pre_workout|post_workout|evening", "duration_minutes": N, "notes": "..."}
  ]
}
"""

        user_prompt = f"""### USER CONTEXT
**Profile:** {user_profile.get('displayName', 'Athlete')}
**Primary Goal:** {primary_goal}
**Training Phase:** {training_phase}
**Current VDOT:** {estimated_vdot}{race_info}
{goal_info}
**VDOT Training Paces (calculated to achieve goal):**
- Easy: {paces['easy']} min/km
- Marathon: {paces['marathon']} min/km
- Threshold: {paces['threshold']} min/km
- Interval: {paces['interval']} min/km
- Repetition: {paces['repetition']} min/km
{hr_zones_text}
**Current Training Load:**
- Acute Load (7-day): {acute_load:.1f}
- Chronic Load (weekly avg): {chronic_load:.1f}
- Weekly Volume: {activity_summary.get('avg_weekly_volume', {}).get('duration_minutes', 0):.0f} min

**Recent Workouts:**
{activities_text}

**Supplementary Activities Requested:**
{supplementary_text if supplementary_text else "None - focus on running workouts only."}

### INSTRUCTION
Generate a **4-week mesocycle** for goal: **{primary_goal}**
Start Date: {datetime.now().strftime('%B %d, %Y')}

**CRITICAL REQUIREMENTS:**
1. **EVERY WEEK MUST HAVE EXACTLY 7 WORKOUTS** - one for each day Monday through Sunday
2. **ALL 4 WEEKS** must have complete daily schedules (28 total workouts)
3. Progressive overload: Weeks 1-3 build, Week 4 recovery (reduced volume, NOT fewer days)
4. ALL running workouts need SPECIFIC PACES from VDOT (e.g., "Easy @ 5:30-5:45/km")
5. Include 80/20 intensity distribution across the mesocycle
6. Rest days should still appear in the workout array with type "rest"
7. If supplementary activities selected, add them to the "supplementary" array with optimal timing
8. Include detailed steps with paces for interval/tempo workouts

**DO NOT** output fewer than 7 workouts per week. Each day must have an entry.

Generate the JSON month plan now."""

        return system_prompt + "\n\n" + user_prompt


    @classmethod
    def build_activity_analysis_prompt(
        cls,
        activity: Dict[str, Any],
        activity_details: Dict[str, Any],
        similar_activities: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        hr_zones: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build a comprehensive workout analysis prompt with comparisons.
        
        Analyzes:
        - Performance metrics vs previous similar workouts
        - Heart rate efficiency and zones
        - Pace consistency and trends
        - What went well, what didn't
        - Specific recommendations for improvement
        """
        
        hr_zones = hr_zones or {}
        
        # Extract activity details
        activity_type = activity.get("activityType", {}).get("typeKey", "activity") if isinstance(activity.get("activityType"), dict) else "other"
        activity_name = activity.get("activityName", activity_type)
        duration_mins = (activity.get("duration", 0) or 0) / 60
        distance_km = (activity.get("distance", 0) or 0) / 1000
        avg_hr = activity.get("averageHR") or activity.get("averageHeartRate") or "N/A"
        max_hr = activity.get("maxHR") or activity.get("maxHeartRate") or "N/A"
        calories = activity.get("calories", 0) or 0
        te_aerobic = activity.get("aerobicTrainingEffect") or activity.get("trainingEffectAerobic") or 0
        te_anaerobic = activity.get("anaerobicTrainingEffect") or activity.get("trainingEffectAnaerobic") or 0
        elevation = activity.get("elevationGain", 0) or 0
        avg_cadence = activity.get("averageRunningCadenceInStepsPerMinute") or 0
        start_time = activity.get("startTimeLocal", "Unknown")
        
        # Calculate pace if applicable
        pace_str = "N/A"
        if distance_km > 0 and duration_mins > 0:
            pace = duration_mins / distance_km
            pace_mins = int(pace)
            pace_secs = int((pace - pace_mins) * 60)
            pace_str = f"{pace_mins}:{pace_secs:02d}/km"
        
        # Get splits info if available
        splits_text = ""
        splits = activity_details.get("splits") or activity_details.get("splitSummaries", [])
        if splits and isinstance(splits, list):
            splits_text = "\n**Splits/Laps:**\n"
            for i, split in enumerate(splits[:10], 1):
                split_dist = (split.get("distance", 0) or 0) / 1000
                split_time = (split.get("duration", 0) or split.get("elapsedDuration", 0) or 0) / 60
                split_hr = split.get("averageHR") or split.get("averageHeartRate") or "N/A"
                if split_dist > 0 and split_time > 0:
                    split_pace = split_time / split_dist
                    split_pace_mins = int(split_pace)
                    split_pace_secs = int((split_pace - split_pace_mins) * 60)
                    splits_text += f"  {i}. {split_dist:.2f}km @ {split_pace_mins}:{split_pace_secs:02d}/km, HR: {split_hr}\n"
        
        # Get HR zone distribution if available
        hr_zones_text = ""
        hr_in_zones = activity_details.get("hr_zones") or []
        if hr_in_zones:
            hr_zones_text = "\n**Time in HR Zones:**\n"
            # Handle list format (from Garmin API)
            if isinstance(hr_in_zones, list):
                for i, zone_data in enumerate(hr_in_zones, 1):
                    if isinstance(zone_data, dict):
                        duration = (zone_data.get("secsInZone", 0) or 0) / 60
                        zone_name = zone_data.get("zoneName", f"Zone {i}")
                        if duration > 0:
                            hr_zones_text += f"  - {zone_name}: {duration:.0f} minutes\n"
            # Handle dict format
            elif isinstance(hr_in_zones, dict):
                for zone_name, zone_data in hr_in_zones.items():
                    if isinstance(zone_data, dict):
                        duration = (zone_data.get("secsInZone", 0) or 0) / 60
                        if duration > 0:
                            hr_zones_text += f"  - {zone_name}: {duration:.0f} minutes\n"
        
        # Get weather if available
        weather_text = ""
        weather = activity_details.get("weather") or {}
        if weather:
            # Garmin API returns temperature in Fahrenheit - convert to Celsius
            temp_f = weather.get("temp")
            if temp_f is not None:
                temp_c = round((temp_f - 32) * 5 / 9, 1)
            else:
                temp_c = "N/A"
            humidity = weather.get("relativeHumidity", weather.get("humidity", "N/A"))
            # Get weather description from weatherTypeDTO
            weather_type = weather.get("weatherTypeDTO", {})
            conditions = weather_type.get("desc", "N/A") if isinstance(weather_type, dict) else "N/A"
            wind_speed = weather.get("windSpeed", "N/A")
            weather_text = f"\n**Weather Conditions:**\nTemperature: {temp_c}°C, Humidity: {humidity}%, Conditions: {conditions}, Wind: {wind_speed} km/h"
        
        # Build comparison data from similar activities
        comparison_text = ""
        if similar_activities:
            comparison_text = "\n**COMPARISON WITH SIMILAR RECENT WORKOUTS:**\n"
            
            # Calculate averages for comparison
            avg_pace_list = []
            avg_hr_list = []
            avg_te_list = []
            avg_cadence_list = []
            
            for i, sim_act in enumerate(similar_activities[:5], 1):
                sim_name = sim_act.get("activityName", "Workout")
                sim_date = sim_act.get("startTimeLocal", "")[:10]
                sim_duration = (sim_act.get("duration", 0) or 0) / 60
                sim_distance = (sim_act.get("distance", 0) or 0) / 1000
                sim_hr = sim_act.get("averageHR") or sim_act.get("averageHeartRate")
                sim_te = sim_act.get("aerobicTrainingEffect") or sim_act.get("trainingEffectAerobic") or 0
                sim_cadence = sim_act.get("averageRunningCadenceInStepsPerMinute") or 0
                
                # Calculate pace
                sim_pace_str = "N/A"
                if sim_distance > 0 and sim_duration > 0:
                    sim_pace = sim_duration / sim_distance
                    sim_pace_mins = int(sim_pace)
                    sim_pace_secs = int((sim_pace - sim_pace_mins) * 60)
                    sim_pace_str = f"{sim_pace_mins}:{sim_pace_secs:02d}/km"
                    avg_pace_list.append(sim_pace)
                
                if sim_hr:
                    avg_hr_list.append(sim_hr)
                avg_te_list.append(sim_te)
                if sim_cadence > 0:
                    avg_cadence_list.append(sim_cadence)
                
                comparison_text += f"  {i}. [{sim_date}] {sim_name}: {sim_duration:.0f}min, {sim_distance:.1f}km @ {sim_pace_str}, HR: {sim_hr or 'N/A'}, TE: {sim_te:.1f}\n"
            
            # Add averages summary
            if avg_pace_list:
                avg_pace = sum(avg_pace_list) / len(avg_pace_list)
                avg_pace_mins = int(avg_pace)
                avg_pace_secs = int((avg_pace - avg_pace_mins) * 60)
                comparison_text += f"\n**Historical Averages:**\n"
                comparison_text += f"  - Avg Pace: {avg_pace_mins}:{avg_pace_secs:02d}/km\n"
            if avg_hr_list:
                comparison_text += f"  - Avg HR: {sum(avg_hr_list)/len(avg_hr_list):.0f} bpm\n"
            if avg_te_list:
                comparison_text += f"  - Avg Training Effect: {sum(avg_te_list)/len(avg_te_list):.1f}\n"
            if avg_cadence_list:
                comparison_text += f"  - Avg Cadence: {sum(avg_cadence_list)/len(avg_cadence_list):.0f} spm\n"
        else:
            comparison_text = "\n**Note:** No similar activities found for comparison. This analysis is based on this workout alone."
        
        # Format user's HR zones if available
        user_hr_zones_text = ""
        if hr_zones and hr_zones.get("zones"):
            zones = hr_zones["zones"]
            max_hr_val = hr_zones.get("max_hr", 185)
            user_hr_zones_text = f"""
**User's HR Zones (Max: {max_hr_val} bpm):**
- Zone 1 (Recovery): {zones.get('zone1', {}).get('min_bpm', 93)}-{zones.get('zone1', {}).get('max_bpm', 111)} bpm
- Zone 2 (Aerobic): {zones.get('zone2', {}).get('min_bpm', 111)}-{zones.get('zone2', {}).get('max_bpm', 130)} bpm
- Zone 3 (Tempo): {zones.get('zone3', {}).get('min_bpm', 130)}-{zones.get('zone3', {}).get('max_bpm', 148)} bpm
- Zone 4 (Threshold): {zones.get('zone4', {}).get('min_bpm', 148)}-{zones.get('zone4', {}).get('max_bpm', 167)} bpm
- Zone 5 (VO2max): {zones.get('zone5', {}).get('min_bpm', 167)}-{zones.get('zone5', {}).get('max_bpm', 185)} bpm
"""
        
        system_prompt = """### SYSTEM ROLE
You are an expert Running Coach and Exercise Physiologist specializing in workout analysis.
Provide a COMPREHENSIVE analysis of the workout with specific, actionable insights.

### ANALYSIS FRAMEWORK
1. **Performance Assessment** - How did this workout go overall?
2. **Comparison to History** - Better/worse than recent similar workouts?
3. **What Went Well** - Identify strengths and positive aspects
4. **What Needs Work** - Identify weaknesses or areas that could improve
5. **Key Metrics Analysis** - Deep dive into HR, pace, cadence, training effect
6. **Recommendations** - Specific actions for next similar workout

### GUIDELINES
- Be specific with numbers, don't use vague language
- Compare to previous workouts when data is available
- Provide 2-3 concrete, actionable recommendations
- Be encouraging but honest about areas for improvement
- Reference specific splits/segments if available
- Consider environmental factors (weather, elevation)

### OUTPUT SCHEMA (JSON)
{
  "overall_rating": "Excellent | Good | Average | Below Expectations" (number 1-10),
  "overall_score": Number (1-100),
  "one_liner": "Quick summary of the workout in one sentence",
  "performance_summary": "2-3 sentence overview of how the workout went",
  "comparison_to_history": {
    "trend": "improving | stable | declining | no_data",
    "pace_vs_avg": "faster | similar | slower | N/A",
    "pace_diff_percent": Number or null,
    "hr_vs_avg": "higher | similar | lower | N/A",
    "hr_diff_bpm": Number or null,
    "efficiency_trend": "String describing efficiency changes",
    "notable_change": "String highlighting the most significant change"
  },
  "what_went_well": [
    {
      "category": "pace | heart_rate | consistency | endurance | effort | cadence | form",
      "observation": "Specific positive observation",
      "metric": "The actual number/value",
      "significance": "Why this matters"
    }
  ],
  "what_needs_improvement": [
    {
      "category": "pace | heart_rate | consistency | endurance | pacing_strategy | cadence | form",
      "observation": "Specific area for improvement",
      "metric": "The actual number/value",
      "recommendation": "How to improve this"
    }
  ],
  "heart_rate_analysis": {
    "zone_assessment": "Which zone did most of the workout occur in?",
    "efficiency": "HR efficiency assessment (pace vs HR relationship)",
    "recommendations": ["Specific HR-related recommendations"]
  },
  "pace_analysis": {
    "consistency": "How consistent were the splits?",
    "pacing_strategy": "negative_split | positive_split | even_paced | variable",
    "recommendations": ["Specific pace-related recommendations"]
  },
  "training_effect_assessment": {
    "aerobic_rating": "Excellent | Good | Moderate | Low",
    "aerobic_insight": "What the aerobic TE means for this workout",
    "anaerobic_rating": "Excellent | Good | Moderate | Low | N/A",
    "anaerobic_insight": "What the anaerobic TE means"
  },
  "key_takeaways": [
    "Takeaway 1 - most important insight",
    "Takeaway 2 - second most important",
    "Takeaway 3 - third insight"
  ],
  "recommendations_for_next_time": [
    {
      "priority": "high | medium | low",
      "action": "Specific action to take",
      "expected_benefit": "What improvement to expect"
    }
  ],
  "recovery_suggestion": "Specific recovery recommendation based on this workout's intensity"
}
"""

        user_prompt = f"""### WORKOUT DATA TO ANALYZE
**Activity:** {activity_name}
**Type:** {activity_type}
**Date:** {start_time}
**Athlete:** {user_profile.get('displayName', 'Athlete')}

**Core Metrics:**
- Duration: {duration_mins:.0f} minutes
- Distance: {distance_km:.2f} km
- Average Pace: {pace_str}
- Average HR: {avg_hr} bpm
- Max HR: {max_hr} bpm
- Calories: {calories}
- Elevation Gain: {elevation}m
- Cadence: {avg_cadence} spm (if running)

**Training Effect:**
- Aerobic TE: {te_aerobic:.1f}/5.0
- Anaerobic TE: {te_anaerobic:.1f}/5.0
{user_hr_zones_text}
{splits_text}
{hr_zones_text}
{weather_text}
{comparison_text}

### INSTRUCTION
Analyze this workout comprehensively. Compare it to the historical data provided.
Identify what went well, what needs improvement, and provide specific recommendations.
Be encouraging but honest. Use the exact numbers from the data.

Generate the JSON analysis now."""

        return system_prompt + "\n\n" + user_prompt


def _get_most_common_activity(activities: List[Dict[str, Any]]) -> str:
    """Get the most common activity type from a list."""
    if not activities:
        return "N/A"
    
    type_counts = {}
    for a in activities:
        atype = a.get("activityType", {}).get("typeKey", "other")
        type_counts[atype] = type_counts.get(atype, 0) + 1
    
    if type_counts:
        return max(type_counts.items(), key=lambda x: x[1])[0]
    return "N/A"
