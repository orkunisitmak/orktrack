"""
Structured AI Prompts for the Physiological Engine.

Based on the VDOT/Polarized Training approach with autoregulation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


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
        # New comprehensive data parameters
        body_battery: Optional[List[Dict[str, Any]]] = None,
        hrv_data: Optional[List[Dict[str, Any]]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        today_readiness: Optional[Dict[str, Any]] = None,
        personal_records: Optional[Dict[str, Any]] = None,
        intensity_minutes: Optional[Dict[str, Any]] = None,
        hr_zones: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build a structured health insights prompt with comprehensive data."""
        
        # Initialize optional data
        body_battery = body_battery or []
        hrv_data = hrv_data or []
        performance_metrics = performance_metrics or {}
        today_readiness = today_readiness or {}
        personal_records = personal_records or {}
        intensity_minutes = intensity_minutes or {}
        hr_zones = hr_zones or {}
        
        # Calculate sleep averages safely
        avg_sleep = 0
        avg_deep = 0
        avg_rem = 0
        avg_light = 0
        sleep_scores = []
        if sleep_data:
            try:
                for s in sleep_data:
                    dto = s.get("dailySleepDTO", {})
                    if dto.get("sleepTimeSeconds"):
                        avg_sleep += (dto.get("sleepTimeSeconds", 0) or 0) / 3600
                    if dto.get("deepSleepSeconds"):
                        avg_deep += (dto.get("deepSleepSeconds", 0) or 0) / 3600
                    if dto.get("remSleepSeconds"):
                        avg_rem += (dto.get("remSleepSeconds", 0) or 0) / 3600
                    if dto.get("lightSleepSeconds"):
                        avg_light += (dto.get("lightSleepSeconds", 0) or 0) / 3600
                    if dto.get("sleepScores", {}).get("overall", {}).get("value"):
                        sleep_scores.append(dto["sleepScores"]["overall"]["value"])
                
                if len(sleep_data) > 0:
                    avg_sleep /= len(sleep_data)
                    avg_deep /= len(sleep_data)
                    avg_rem /= len(sleep_data)
                    avg_light /= len(sleep_data)
            except Exception:
                pass
        
        avg_sleep_score = sum(sleep_scores) / len(sleep_scores) if sleep_scores else 0
        
        # Calculate activity metrics safely
        total_activities = len(activities) if activities else 0
        total_duration = 0
        total_distance = 0
        total_calories = 0
        avg_hr = []
        training_effects = []
        activity_breakdown = {}
        
        if activities:
            try:
                for a in activities:
                    duration = (a.get("duration", 0) or 0) / 60
                    total_duration += duration
                    total_distance += (a.get("distance", 0) or 0) / 1000  # Convert to km
                    total_calories += a.get("calories", 0) or 0
                    
                    if a.get("averageHR"):
                        avg_hr.append(a["averageHR"])
                    
                    te = a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic")
                    if te:
                        training_effects.append(te)
                    
                    # Track activity types
                    act_type = a.get("classified_type") or a.get("activityType", {}).get("typeKey", "other")
                    activity_breakdown[act_type] = activity_breakdown.get(act_type, 0) + 1
            except Exception:
                pass
        
        avg_workout_hr = sum(avg_hr) / len(avg_hr) if avg_hr else 0
        avg_training_effect = sum(training_effects) / len(training_effects) if training_effects else 0
        
        # Calculate body battery trend
        bb_values = []
        bb_trend = "stable"
        for bb in body_battery:
            if bb.get("current_value"):
                bb_values.append(bb["current_value"])
        if len(bb_values) >= 2:
            if bb_values[0] > bb_values[-1] + 10:
                bb_trend = "declining"
            elif bb_values[0] < bb_values[-1] - 10:
                bb_trend = "improving"
        
        # Calculate HRV trend
        hrv_values = []
        hrv_statuses = []
        hrv_trend = "stable"
        for hrv in hrv_data:
            summary = hrv.get("hrvSummary", {})
            if summary.get("lastNightAvg"):
                hrv_values.append(summary["lastNightAvg"])
            if summary.get("status"):
                hrv_statuses.append(summary["status"])
        if len(hrv_values) >= 2:
            if hrv_values[0] > hrv_values[-1] + 5:
                hrv_trend = "declining"
            elif hrv_values[0] < hrv_values[-1] - 5:
                hrv_trend = "improving"
        
        system_prompt = """### SYSTEM ROLE
You are a certified Health Coach and Exercise Physiologist specializing in data-driven wellness optimization. 
Analyze the provided comprehensive health telemetry and provide detailed, actionable, personalized insights.

### ANALYSIS FRAMEWORK
1. **Sleep Quality:** Analyze duration, deep/REM/light sleep distribution, sleep scores, and consistency
2. **Recovery Status:** Evaluate HRV trends, resting HR, body battery patterns, and training readiness
3. **Training Load:** Assess volume, intensity distribution, training effect, and recovery balance
4. **Performance Metrics:** Analyze VO2max, fitness age, endurance score, and training status
5. **Stress Management:** Identify stress patterns and recommend interventions
6. **Body Composition:** Track body battery energy management and charging/draining patterns

### CONSTRAINTS
1. Be specific with numbers, percentages, and trends
2. Compare to recommended guidelines (7-9hrs sleep, <60bpm RHR for fit individuals, HRV baseline)
3. Provide 2-3 actionable recommendations per area with specific timing
4. Acknowledge positive trends while addressing areas for improvement
5. Include comparisons to previous periods when data is available
6. Output must be valid JSON

### OUTPUT SCHEMA (JSON)
{
  "overall_score": Number (0-100),
  "overall_assessment": "String - detailed summary of health status",
  "period_summary": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "total_activities": Number,
    "total_duration_hours": Number,
    "total_distance_km": Number,
    "avg_sleep_hours": Number,
    "avg_sleep_score": Number
  },
  "highlights": [
    {
      "type": "positive | warning | info | achievement",
      "category": "sleep | activity | recovery | stress | performance",
      "title": "String",
      "description": "String - detailed explanation",
      "metric": "String",
      "value": "String",
      "trend": "improving | stable | declining | null",
      "action": "String - specific action to take"
    }
  ],
  "sleep_analysis": {
    "quality_rating": "Excellent | Good | Fair | Poor",
    "avg_duration_hours": Number,
    "avg_sleep_score": Number,
    "sleep_stages": {
      "deep_hours": Number,
      "rem_hours": Number,
      "light_hours": Number,
      "deep_percentage": Number
    },
    "consistency_score": Number (0-100),
    "sleep_debt_hours": Number,
    "insights": ["String - specific findings"],
    "recommendations": ["String - actionable advice with timing"]
  },
  "activity_analysis": {
    "consistency_rating": "Excellent | Good | Fair | Poor",
    "volume_trend": "increasing | stable | decreasing",
    "total_distance_km": Number,
    "avg_training_effect": Number,
    "intensity_distribution": {
      "low_percentage": Number,
      "moderate_percentage": Number,
      "high_percentage": Number
    },
    "activity_breakdown": {"activity_type": count},
    "wellness_activities": {
      "yoga_sessions": Number,
      "cold_plunge_sessions": Number,
      "breathing_sessions": Number,
      "other_wellness": Number,
      "wellness_assessment": "String - assessment of recovery/wellness practices"
    },
    "training_load_status": "Optimal | High | Low | Recovery Needed",
    "insights": ["String - include insights about ALL activity types including wellness"],
    "recommendations": ["String - include recommendations for both training AND recovery activities"]
  },
  "recovery_analysis": {
    "status": "Excellent | Good | Fair | Needs Attention",
    "avg_resting_hr": Number,
    "resting_hr_trend": "improving | stable | elevated",
    "hrv_analysis": {
      "avg_hrv": Number,
      "hrv_trend": "improving | stable | declining",
      "hrv_status": "Balanced | Unbalanced | Low"
    },
    "body_battery_analysis": {
      "current_level": Number,
      "trend": "improving | stable | declining",
      "avg_charge": Number,
      "avg_drain": Number
    },
    "recovery_time_hours": Number,
    "insights": ["String"],
    "recommendations": ["String"]
  },
  "performance_analysis": {
    "vo2_max": Number,
    "vo2_max_trend": "improving | stable | declining",
    "fitness_age": Number,
    "fitness_age_vs_actual": Number,
    "endurance_score": Number,
    "training_status": "String",
    "training_status_description": "String",
    "insights": ["String"],
    "recommendations": ["String"]
  },
  "stress_analysis": {
    "avg_stress_level": Number,
    "stress_trend": "improving | stable | worsening",
    "high_stress_periods": ["String - time patterns"],
    "insights": ["String"],
    "recommendations": ["String"]
  },
  "weekly_focus": "String - One key area to prioritize based on the analysis period",
  "action_plan": [
    {
      "priority": 1,
      "area": "String",
      "action": "String - specific action",
      "timing": "String - when to do it",
      "expected_impact": "String"
    }
  ],
  "motivational_message": "String - Personalized encouragement based on data"
}
"""

        focus_str = ", ".join(focus_areas) if focus_areas else "Overall health and fitness"
        
        # Safely format health data values
        avg_steps = safe_format(health_data.get('avg_steps', 0))
        total_steps = safe_format(health_data.get('total_steps', 0))
        avg_rhr = health_data.get('avg_resting_hr') or 'N/A'
        avg_stress = health_data.get('avg_stress') or 'N/A'
        active_mins = safe_format(health_data.get('total_active_minutes', 0))
        total_cals_health = safe_format(health_data.get('total_calories', 0))
        
        # Format performance metrics
        vo2max = performance_metrics.get("vo2_max") or "N/A"
        fitness_age = performance_metrics.get("fitness_age") or "N/A"
        endurance_score = performance_metrics.get("endurance_score") or "N/A"
        training_status = performance_metrics.get("training_status") or "N/A"
        training_load_7d = performance_metrics.get("training_load_7d") or "N/A"
        recovery_time = performance_metrics.get("recovery_time_hours") or "N/A"
        
        # Format today's readiness
        current_bb = today_readiness.get("body_battery") or "N/A"
        current_hrv_status = today_readiness.get("hrv_status") or "Unknown"
        current_hrv_avg = today_readiness.get("hrv_avg") or "N/A"
        readiness_score = today_readiness.get("readiness_score") or "N/A"
        
        # Format HRV data
        avg_hrv_value = sum(hrv_values) / len(hrv_values) if hrv_values else "N/A"
        most_common_hrv_status = max(set(hrv_statuses), key=hrv_statuses.count) if hrv_statuses else "Unknown"
        
        # Format intensity minutes
        weekly_vigorous = intensity_minutes.get("weeklyVigorous", 0) or 0
        weekly_moderate = intensity_minutes.get("weeklyModerate", 0) or 0
        weekly_goal = intensity_minutes.get("weeklyGoal", 150) or 150
        
        # Format activity breakdown
        activity_breakdown_str = ", ".join([f"{k}: {v}" for k, v in sorted(activity_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]]) or "N/A"
        
        # Format detailed activity list with ALL activities including wellness
        detailed_activities_list = ""
        if activities:
            for i, a in enumerate(activities[:30], 1):  # Show up to 30 activities
                act_name = a.get("activityName", "Unnamed")
                act_type = a.get("classifiedType") or a.get("classifiedTypeName") or a.get("activityType", {}).get("typeKey", "other")
                if isinstance(a.get("activityType"), dict):
                    act_type = a.get("classifiedType") or a["activityType"].get("typeKey", "other")
                
                duration_mins = (a.get("duration", 0) or 0) / 60
                distance_km = (a.get("distance", 0) or 0) / 1000
                avg_hr = a.get("averageHR") or a.get("avgHR") or "N/A"
                max_hr = a.get("maxHR") or "N/A"
                calories = a.get("calories") or "N/A"
                training_effect = a.get("aerobicTrainingEffect") or a.get("trainingEffectAerobic") or "N/A"
                start_time = a.get("startTimeLocal", "")[:10] if a.get("startTimeLocal") else "Unknown date"
                
                # Determine if it's a wellness/recovery activity
                is_wellness = act_type in ['yoga', 'cold_plunge', 'breathing', 'meditation', 'sauna', 'stretching', 'other'] or \
                              any(kw in act_name.lower() for kw in ['yoga', 'cold', 'plunge', 'breath', 'meditat', 'stretch', 'sauna'])
                
                activity_label = f"[WELLNESS] " if is_wellness else ""
                
                detailed_activities_list += f"""
{i}. {activity_label}**{act_name}** ({act_type})
   - Date: {start_time}
   - Duration: {duration_mins:.0f} min
   - Distance: {distance_km:.1f} km
   - Avg HR: {avg_hr} bpm | Max HR: {max_hr} bpm
   - Calories: {calories} | Training Effect: {training_effect}
"""
        else:
            detailed_activities_list = "No activities recorded in this period."
        
        user_prompt = f"""### USER CONTEXT
**Profile:**
- Name: {user_profile.get('displayName', 'Athlete')}
- Age: {user_profile.get('age', 'Unknown')}

**Analysis Period:** Last {1 if period == 'day' else (7 if period == 'week' else 30)} days (from {(datetime.now() - timedelta(days=1 if period == 'day' else (7 if period == 'week' else 30))).strftime('%B %d')} to {datetime.now().strftime('%B %d, %Y')})
**Focus Areas:** {focus_str}
**Generated:** {datetime.now().strftime('%A, %B %d, %Y')}

---
### DAILY METRICS SUMMARY

**Steps & Activity:**
- Average Daily Steps: {avg_steps}
- Total Steps: {total_steps}
- Total Active Minutes: {active_mins}
- Total Calories Burned: {total_cals_health}
- Intensity Minutes (Week): Vigorous: {weekly_vigorous} | Moderate: {weekly_moderate} | Goal: {weekly_goal}

**Heart & Recovery:**
- Average Resting HR: {avg_rhr} bpm
- Average Stress Level: {avg_stress}/100
- Current Body Battery: {current_bb}/100
- Body Battery Trend: {bb_trend}

**HRV Analysis:**
- Current HRV Status: {current_hrv_status}
- Average HRV (Last Night): {current_hrv_avg} ms
- Weekly Average HRV: {avg_hrv_value if isinstance(avg_hrv_value, str) else f"{avg_hrv_value:.0f}"} ms
- HRV Trend: {hrv_trend}
- Most Common Status: {most_common_hrv_status}

---
### SLEEP ANALYSIS ({len(sleep_data) if sleep_data else 0} nights)

- Average Sleep Duration: {avg_sleep:.1f} hours
- Average Sleep Score: {avg_sleep_score:.0f}/100
- Average Deep Sleep: {avg_deep:.1f} hours ({(avg_deep/avg_sleep*100) if avg_sleep > 0 else 0:.0f}%)
- Average REM Sleep: {avg_rem:.1f} hours ({(avg_rem/avg_sleep*100) if avg_sleep > 0 else 0:.0f}%)
- Average Light Sleep: {avg_light:.1f} hours ({(avg_light/avg_sleep*100) if avg_sleep > 0 else 0:.0f}%)

---
### ACTIVITY SUMMARY ({total_activities} activities)

- Total Workout Duration: {total_duration:.0f} minutes ({total_duration/60:.1f} hours)
- Total Distance: {total_distance:.1f} km
- Total Workout Calories: {total_calories:,}
- Average Workout HR: {avg_workout_hr:.0f} bpm
- Average Training Effect: {avg_training_effect:.1f}/5.0
- Activity Type Breakdown: {activity_breakdown_str}
- Most Common Type: {_get_most_common_activity(activities)}

---
### DETAILED ACTIVITY LOG (ALL ACTIVITIES IN PERIOD)

**IMPORTANT:** Analyze ALL activities below including wellness activities (yoga, cold plunge, breathing, etc.)
Wellness activities are marked with [WELLNESS] - these contribute to recovery and mental health.

{detailed_activities_list}

---
### PERFORMANCE METRICS

- VO2 Max: {vo2max}
- Fitness Age: {fitness_age}
- Endurance Score: {endurance_score}/100
- Training Status: {training_status}
- 7-Day Training Load: {training_load_7d}
- Recommended Recovery Time: {recovery_time} hours

---
### TODAY'S READINESS

- Readiness Score: {readiness_score}/100
- Body Battery: {current_bb}/100
- HRV Status: {current_hrv_status}
- Sleep Score (Last Night): {sleep_scores[0] if sleep_scores else 'N/A'}/100
- Recommendation: {today_readiness.get('adjustment_reason', 'No adjustments needed')}

---
### INSTRUCTION
Analyze ALL the health data above and generate comprehensive insights following the JSON schema.

**CRITICAL - ANALYZE ALL ACTIVITIES:**
1. Review EVERY activity in the detailed activity log above
2. Include wellness activities (yoga, cold plunge, breathing, etc.) in your analysis
3. Recognize that wellness activities contribute to recovery even if they don't have high training effect
4. Count and acknowledge each activity type when generating activity_breakdown and wellness_activities

**Focus Areas:**
- Training volume and intensity patterns
- Recovery practices (cold plunge, yoga, breathing are POSITIVE for recovery)
- Sleep quality and consistency
- Stress management and body battery trends
- Actionable recommendations for improvement

Be encouraging but honest about areas needing improvement.
Reference specific activities by name when relevant.

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
                
                # New metrics
                avg_stress = a.get('avgStressLevel') or ''
                avg_respiration = a.get('avgRespirationRate') or ''
                performance_cond = a.get('performanceCondition') or a.get('firstBeatPerformanceCondition') or ''
                
                # Calculate pace if running/walking
                pace_str = ""
                if distance_km > 0 and duration_mins > 0 and activity_type in ['running', 'walking', 'trail_running', 'treadmill_running']:
                    pace = duration_mins / distance_km
                    pace_mins = int(pace)
                    pace_secs = int((pace - pace_mins) * 60)
                    pace_str = f", Pace: {pace_mins}:{pace_secs:02d}/km"
                
                # Build extra metrics string
                extra_metrics = ""
                if avg_stress:
                    extra_metrics += f", Stress: {avg_stress}"
                if avg_respiration:
                    extra_metrics += f", Resp: {avg_respiration:.1f}brpm" if isinstance(avg_respiration, (int, float)) else ""
                if performance_cond:
                    extra_metrics += f", PC: {'+' if performance_cond > 0 else ''}{performance_cond}"
                
                activities_summary += f"{i+1}. [{start_time}] {activity_name} ({activity_type}) - {duration_mins:.0f}min, {distance_km:.2f}km, HR: {avg_hr}/{max_hr}, TE: {te_aerobic}/{te_anaerobic}{pace_str}{extra_metrics}\n"
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
            supplementary_text += "\n\n**CRITICAL - YOU MUST FOLLOW USER'S FREQUENCY:**"
            supplementary_text += "\n- If user selected 7x/week (Every day), that activity MUST appear in EVERY day's supplementary array"
            supplementary_text += "\n- For example, if Cold Plunge is 7x/week, add it to all 7 days"
            supplementary_text += "\n- Each day's 'supplementary' array must contain ALL activities scheduled for that day"
            supplementary_text += "\n- Include specific time recommendations (Morning, Pre-workout, Evening 6h+ post-run, etc.)"
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
          "description": "Step with SPECIFIC PACE (e.g., 'Easy Jog', 'Threshold', 'Recovery Jog')",
          "duration_minutes": Number (REQUIRED - duration in minutes),
          "distance_meters": Number (REQUIRED for distance-based steps, e.g., 2000 for 2km),
          "target_pace_min": "min/km (REQUIRED for run workouts, e.g., '4:50')",
          "target_pace_max": "min/km (REQUIRED for run workouts, e.g., '4:55')",
          "target_hr_bpm": "e.g., 150-160 bpm" (optional)
        }
      ],
      "// CRITICAL STEPS RULES": [
        "1. EVERY step MUST have either duration_minutes OR distance_meters (or both)",
        "2. For INTERVALS (e.g., 3x2km): Create SEPARATE steps for each repeat and recovery",
        "   Example for 3x2km @ T-Pace with 400m recovery:",
        "   - {type: 'work', description: 'Threshold Interval 1', distance_meters: 2000, target_pace_min: '4:50', target_pace_max: '4:55'}",
        "   - {type: 'recovery', description: 'Recovery Jog', distance_meters: 400, target_pace_min: '6:00', target_pace_max: '6:30'}",
        "   - {type: 'work', description: 'Threshold Interval 2', distance_meters: 2000, ...}",
        "   - {type: 'recovery', description: 'Recovery Jog', distance_meters: 400, ...}",
        "   - {type: 'work', description: 'Threshold Interval 3', distance_meters: 2000, ...}",
        "3. Warmup/Cooldown: Use duration_minutes (e.g., 10 minutes)",
        "4. Long runs/Easy runs: Use duration_minutes",
        "5. Tempo/Threshold: Use either duration_minutes OR distance_meters",
        "6. Track intervals (400m, 800m, 1km, 2km): Use distance_meters"
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
    "// IMPORTANT": "Schedule EXACTLY as user requested - if 7x/week, list all 7 days",
    "wim_hof": ["Example: Mon AM, Tue AM, Wed AM, Thu AM, Fri AM, Sat AM, Sun AM if 7x/week"],
    "mobility": ["Example: Daily AM if 7x/week"],
    "yoga": ["Example: All 7 days if 7x/week, or specific days if less"],
    "cold_plunge": ["Example: All 7 days if 7x/week"],
    "gym": ["Example: Mon, Wed, Fri if 3x/week"]
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
7. **CRITICAL - WORKOUT STEPS STRUCTURE:**
   - EVERY step MUST have duration_minutes (e.g., 10) AND/OR distance_meters (e.g., 2000 for 2km)
   - For INTERVAL workouts: Create SEPARATE steps for EACH repeat and recovery period
   - Example: "3x2km @ T-Pace" becomes 6 steps: work-recovery-work-recovery-work (no trailing recovery)
   - Warmup/Cooldown: Use duration_minutes (e.g., 10)
   - Track intervals (400m, 800m, 1km, 2km): Use distance_meters
   - Tempo runs: Use duration_minutes OR distance_meters
   - DO NOT use shorthand like "3x2km" in a single step - expand into separate steps
8. **SUPPLEMENTARY ACTIVITIES ARE MANDATORY:**
   - Each workout's "supplementary" array MUST include ALL activities scheduled for that day
   - If user requested 7x/week for an activity, it MUST appear in ALL 7 days
   - Even REST days should include the appropriate supplementary activities
   - Include proper timing (Morning, Evening, Pre-workout, Post-workout 6h+)

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
            supplementary_text += "\n\n**CRITICAL - YOU MUST FOLLOW USER'S FREQUENCY:**"
            supplementary_text += "\n- If user selected 7x/week (Every day), that activity MUST appear in EVERY day's supplementary array"
            supplementary_text += "\n- Each day's 'supplementary' array must contain ALL activities scheduled for that day"
        
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
  "key_focus": "Primary training benefit",
  "steps": [
    {
      "type": "warmup|work|recovery|cooldown",
      "description": "Step description (e.g., 'Easy Jog', 'Threshold', 'Recovery Jog')",
      "duration_minutes": Number (REQUIRED for time-based steps),
      "distance_meters": Number (REQUIRED for distance-based steps, e.g., 2000 for 2km),
      "target_pace_min": "X:XX (REQUIRED for running)",
      "target_pace_max": "X:XX (REQUIRED for running)"
    }
  ],
  "supplementary": [
    {"activity": "wim_hof|mobility|yoga|cold_plunge|gym", "timing": "morning|pre_workout|post_workout|evening", "duration_minutes": N, "notes": "..."}
  ]
}

### CRITICAL - WORKOUT STEPS RULES:
1. EVERY step MUST have either "duration_minutes" OR "distance_meters" (or both)
2. For INTERVAL workouts (e.g., 3x2km @ T-Pace): Create SEPARATE steps for EACH repeat and recovery:
   - Step 1: {type: "warmup", description: "Easy Jog", duration_minutes: 10, target_pace_min: "5:50", target_pace_max: "6:10"}
   - Step 2: {type: "work", description: "Threshold Interval 1", distance_meters: 2000, target_pace_min: "4:50", target_pace_max: "4:55"}
   - Step 3: {type: "recovery", description: "Recovery Jog", distance_meters: 400, target_pace_min: "6:00", target_pace_max: "6:30"}
   - Step 4: {type: "work", description: "Threshold Interval 2", distance_meters: 2000, target_pace_min: "4:50", target_pace_max: "4:55"}
   - Step 5: {type: "recovery", description: "Recovery Jog", distance_meters: 400, target_pace_min: "6:00", target_pace_max: "6:30"}
   - Step 6: {type: "work", description: "Threshold Interval 3", distance_meters: 2000, target_pace_min: "4:50", target_pace_max: "4:55"}
   - Step 7: {type: "cooldown", description: "Easy Jog", duration_minutes: 10, target_pace_min: "5:50", target_pace_max: "6:10"}
3. DO NOT use shorthand like "3x2km" in a single step - expand into separate steps
4. Warmup/Cooldown: Use duration_minutes
5. Track intervals (400m, 800m, 1km, 2km): Use distance_meters
6. Tempo/Long runs: Use either duration_minutes OR distance_meters
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
7. **SUPPLEMENTARY ACTIVITIES ARE MANDATORY:**
   - Each workout's "supplementary" array MUST include ALL activities scheduled for that day
   - If user requested 7x/week, that activity MUST appear in ALL 7 days of EACH week
   - Even REST days should include appropriate supplementary activities
   - Include proper timing (Morning, Evening, Pre-workout, Post-workout 6h+)
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
        
        # New metrics: stress, respiration, performance condition, stride length, power
        avg_stress = activity.get("avgStressLevel") or "N/A"
        max_stress = activity.get("maxStressLevel") or "N/A"
        avg_respiration = activity.get("avgRespirationRate") or "N/A"
        max_respiration = activity.get("maxRespirationRate") or "N/A"
        performance_condition = activity.get("performanceCondition") or activity.get("firstBeatPerformanceCondition") or "N/A"
        avg_stride_length = activity.get("avgStrideLength")
        if avg_stride_length:
            avg_stride_length = f"{avg_stride_length / 100:.2f}m"  # Convert cm to m
        else:
            avg_stride_length = "N/A"
        avg_power = activity.get("avgPower") or "N/A"
        max_power = activity.get("maxPower") or "N/A"
        norm_power = activity.get("normPower") or "N/A"
        training_load = activity.get("trainingLoad") or "N/A"
        recovery_time = activity.get("recoveryTimeInMinutes")
        if recovery_time:
            recovery_hours = recovery_time // 60
            recovery_mins = recovery_time % 60
            recovery_time_str = f"{recovery_hours}h {recovery_mins}m" if recovery_hours else f"{recovery_mins}m"
        else:
            recovery_time_str = "N/A"
        
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
        
        # Determine if this is a recovery/wellness activity based on name and type
        activity_name_lower = activity_name.lower()
        activity_type_lower = activity_type.lower()
        combined_lower = f"{activity_name_lower} {activity_type_lower}"
        
        # Recovery/wellness activities - check both name AND type
        recovery_keywords = [
            'cold plunge', 'ice bath', 'cold', 'plunge', 'sauna', 'meditation', 
            'breathing', 'wim hof', 'breathwork', 'yoga', 'stretch', 'stretching',
            'mobility', 'recovery', 'massage', 'foam roll', 'foam rolling',
            'rest', 'relax', 'mindfulness', 'wellness', 'cooldown', 'warmup'
        ]
        is_recovery_activity = any(keyword in combined_lower for keyword in recovery_keywords)
        
        # Also check if it's "other" type with recovery-related name
        if activity_type_lower == 'other' and any(kw in activity_name_lower for kw in ['cold', 'plunge', 'ice', 'sauna', 'breath', 'meditation', 'yoga', 'stretch']):
            is_recovery_activity = True
        
        is_strength_activity = any(keyword in combined_lower for keyword in [
            'strength', 'weight', 'gym', 'lift', 'resistance', 'crossfit', 'hiit'
        ]) and not is_recovery_activity
        
        is_cardio_activity = any(keyword in combined_lower for keyword in [
            'run', 'cycling', 'bike', 'swim', 'row', 'elliptical', 'walk', 'hike', 'cardio'
        ]) and not is_recovery_activity
        
        # Build context-aware system prompt
        if is_recovery_activity:
            system_prompt = f"""### SYSTEM ROLE
You are an expert Recovery Specialist and Wellness Coach analyzing a RECOVERY/WELLNESS activity.
This is NOT a workout - it's a recovery or wellness activity: "{activity_name}".

### CRITICAL: SCORING GUIDELINES FOR RECOVERY ACTIVITIES
IMPORTANT: Recovery activities are scored DIFFERENTLY than workouts!

**Scoring Rules for Recovery Activities:**
- Cold Plunge/Ice Bath (1-5 min): Score 80-95 (excellent - cold exposure achieved)
- Cold Plunge/Ice Bath (5-10 min): Score 90-100 (exceptional cold tolerance)
- Yoga (15-30 min): Score 80-90 (good mindful practice)
- Yoga (30-60+ min): Score 85-95 (excellent practice)
- Breathing/Meditation (5-15 min): Score 80-90 (effective session)
- Stretching/Mobility (10-20 min): Score 75-85 (good recovery work)
- Sauna (10-20 min): Score 80-90 (good heat exposure)

**DO NOT penalize recovery activities for:**
- Short duration (1-5 min cold plunge is IDEAL, not a failure!)
- Zero distance (recovery activities have no distance)
- Low calorie burn (that's expected!)
- Missing pace data (not applicable)
- Low aerobic/anaerobic training effect (recovery isn't meant to train!)

### ANALYSIS FRAMEWORK FOR RECOVERY ACTIVITIES
1. **Recovery Value** - What recovery benefits did this activity provide?
2. **Execution** - Was the activity performed correctly/safely? Duration appropriate?
3. **Physiological Benefits** - Heart rate response, parasympathetic activation
4. **Recommendations** - How to optimize this recovery practice

### GUIDELINES
- A completed recovery activity IS a success - rate it positively (75+ score minimum)
- Cold plunge: Even 1-3 minutes provides significant benefits - score HIGH
- Yoga: Focus on duration and consistency, not intensity metrics
- Breathing: Focus on stress reduction benefits
- Do NOT say the activity "wasn't recorded" or is an "error" - the user completed it!
- Be encouraging and supportive about recovery practices"""
        elif is_strength_activity:
            system_prompt = """### SYSTEM ROLE
You are an expert Strength Coach and Exercise Physiologist analyzing a strength/resistance training session.
Provide a COMPREHENSIVE analysis focused on strength training metrics.

### ANALYSIS FRAMEWORK FOR STRENGTH TRAINING
1. **Session Assessment** - Overall quality of the strength session
2. **Intensity & Volume** - Based on HR, duration, and effort
3. **Recovery Impact** - Training effect and recovery needs
4. **Recommendations** - Specific actions for improvement

### GUIDELINES
- Focus on effort, heart rate patterns, and training effect
- Don't analyze pace/distance (not relevant for strength)
- Consider workout duration and intensity
- Provide strength-focused recommendations"""
        else:
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
- Consider environmental factors (weather, elevation)"""

        # Common output schema for all activity types
        output_schema = """
### OUTPUT SCHEMA (JSON)
{
  "overall_rating": "Excellent | Good | Average | Below Expectations",
  "overall_score": Number (1-100),
  "one_liner": "Quick summary of the activity in one sentence - tailor to activity type",
  "performance_summary": "2-3 sentence overview - for recovery activities focus on wellness benefits, for workouts focus on performance",
  "comparison_to_history": {
    "trend": "improving | stable | declining | no_data",
    "pace_vs_avg": "faster | similar | slower | N/A (use N/A for non-cardio activities)",
    "pace_diff_percent": Number or null,
    "hr_vs_avg": "higher | similar | lower | N/A",
    "hr_diff_bpm": Number or null,
    "efficiency_trend": "String describing efficiency/recovery quality changes",
    "notable_change": "String highlighting the most significant observation"
  },
  "what_went_well": [
    {
      "category": "recovery | relaxation | heart_rate | consistency | endurance | effort | technique | duration",
      "observation": "Specific positive observation tailored to activity type",
      "metric": "The actual number/value (e.g., '3 min duration', '75 bpm avg HR')",
      "significance": "Why this matters for recovery/performance"
    }
  ],
  "what_needs_improvement": [
    {
      "category": "technique | duration | timing | frequency | heart_rate | consistency",
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
  "stress_analysis": {
    "avg_stress": Number or null,
    "max_stress": Number or null,
    "stress_during_activity": "low | moderate | high | N/A",
    "stress_management": "How well stress was managed during the activity",
    "insight": "What the stress levels indicate about the workout"
  },
  "respiration_analysis": {
    "avg_respiration": Number or null,
    "max_respiration": Number or null,
    "breathing_efficiency": "efficient | moderate | needs_work | N/A",
    "insight": "What respiration patterns indicate about effort and recovery"
  },
  "performance_condition_analysis": {
    "value": Number or null,
    "interpretation": "above_baseline | at_baseline | below_baseline | N/A",
    "insight": "What performance condition indicates about freshness/fatigue"
  },
  "power_analysis": {
    "avg_power": Number or null,
    "normalized_power": Number or null,
    "power_efficiency": "Assessment of power output relative to HR/pace",
    "insight": "Power-related insights if available"
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
        
        # Add output schema to system prompt
        system_prompt = system_prompt + output_schema

        # Build activity type context
        activity_context = ""
        if is_recovery_activity:
            activity_context = f"""
### CRITICAL: THIS IS A RECOVERY/WELLNESS ACTIVITY - "{activity_name}"
This is a RECOVERY activity - evaluate it as such, NOT as a workout!

**For this activity, you MUST:**
- Give a score of 75-95 (this is a successfully completed recovery activity)
- Praise the user for prioritizing recovery
- Focus on wellness benefits, NOT workout metrics
- Do NOT say this is an "error", "accidental recording", or "failed to record"

**Evaluation criteria for "{activity_name}":**
- Cold plunge: Duration of 1-5 min = excellent, HR data shows cold response
- Yoga: Duration of 15+ min = good session, relaxation achieved
- The user INTENTIONALLY did this activity for recovery - acknowledge that!
"""
        elif is_strength_activity:
            activity_context = f"""
### ACTIVITY TYPE: STRENGTH/RESISTANCE TRAINING
Analyze "{activity_name}" as a strength training session.
Focus on effort, training effect, and recovery needs rather than pace/distance.
"""

        user_prompt = f"""### ACTIVITY DATA TO ANALYZE
**Activity Name:** {activity_name}
**Activity Type:** {activity_type}
**Date:** {start_time}
**Athlete:** {user_profile.get('displayName', 'Athlete')}
{activity_context}
**Core Metrics:**
- Duration: {duration_mins:.1f} minutes
- Distance: {distance_km:.2f} km {"(N/A for non-cardio activities)" if distance_km == 0 else ""}
- Average Pace: {pace_str} {"(N/A for non-cardio activities)" if pace_str == "N/A" else ""}
- Average HR: {avg_hr} bpm
- Max HR: {max_hr} bpm
- Calories: {calories}
- Elevation Gain: {elevation}m
- Cadence: {avg_cadence} spm {"(N/A for non-running activities)" if avg_cadence == 0 else ""}

**Physiological Metrics:**
- Average Stress Level: {avg_stress}
- Max Stress Level: {max_stress}
- Average Respiration Rate: {avg_respiration} brpm
- Max Respiration Rate: {max_respiration} brpm
- Performance Condition: {performance_condition}
- Average Stride Length: {avg_stride_length}

**Power Metrics (if available):**
- Average Power: {avg_power} W
- Max Power: {max_power} W
- Normalized Power: {norm_power} W

**Training Load & Recovery:**
- Training Load: {training_load}
- Recommended Recovery: {recovery_time_str}
- Aerobic TE: {te_aerobic:.1f}/5.0
- Anaerobic TE: {te_anaerobic:.1f}/5.0
{user_hr_zones_text}
{splits_text}
{hr_zones_text}
{weather_text}
{comparison_text}

### INSTRUCTION
{'''CRITICAL: This is a RECOVERY activity. You MUST:
1. Give an overall_score of 75-95 (this activity was completed successfully)
2. Set overall_rating to "Good" or "Excellent" (recovery was achieved)
3. Focus on recovery BENEFITS in your analysis
4. Do NOT mention "accidental recording", "sync error", "no data", or similar
5. Praise the user for completing this recovery practice
6. The duration shown IS the actual duration - it's not an error!''' if is_recovery_activity else "Analyze this activity comprehensively. Compare it to the historical data provided."}

Identify what went well, what needs improvement, and provide specific recommendations.
Be encouraging and supportive. Use the exact numbers from the data when available.

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
