"""AI Prompt Templates for OrkTrack."""

from typing import Dict, Any, List, Optional
from datetime import datetime


class PromptTemplates:
    """Templates for AI interactions."""
    
    SYSTEM_PROMPT = """You are OrkTrack AI, an expert fitness coach and health analyst integrated into a Garmin activity dashboard.

Your key capabilities:
- Analyze workout patterns and performance trends
- Provide personalized training recommendations based on Jack Daniels VDOT methodology
- Offer insights on sleep, recovery, and stress
- Help users understand their heart rate data and zones
- Create customized workout suggestions using Polarized Training (80/20) principles
- Identify areas for improvement while celebrating achievements

Training Philosophy:
1. **Polarized Training (80/20):** 80% volume at low intensity, 20% at moderate-to-high.
2. **Jack Daniels VDOT System:** All paces mathematically derived from VDOT scores.
3. **Autoregulation:** Adjust training based on recovery metrics.

Guidelines:
- Be encouraging and supportive while honest about areas for improvement
- Base all recommendations on actual data
- Consider recovery metrics when suggesting workouts
- Use specific numbers and comparisons
- Prioritize safety - recommend rest when recovery metrics are poor
- Be concise but thorough
- Always explain the "why" behind recommendations
- For medical concerns, always recommend consulting a healthcare professional."""

    @staticmethod
    def chat_context_prompt(
        user_data: Dict[str, Any],
        recent_activities: List[Dict],
        health_summary: Dict[str, Any],
        user_query: str
    ) -> str:
        """Build a context-rich chat prompt."""
        
        # Format recent activities
        activities_text = ""
        if recent_activities:
            for a in recent_activities[:5]:
                activity_type = a.get('activityType', {}).get('typeKey', 'Activity')
                duration = (a.get('duration', 0) or 0) / 60
                calories = a.get('calories', 0) or 0
                activities_text += f"- {activity_type}: {duration:.0f} min, {calories} cal\n"
        else:
            activities_text = "No recent activities recorded."

        return f"""### USER CONTEXT
**Profile:** {user_data.get('displayName', 'User')}

**Recent Activities:**
{activities_text}

**Health Summary (Last 7 Days):**
- Average Daily Steps: {health_summary.get('avg_steps', 'N/A'):,}
- Average Resting HR: {health_summary.get('avg_resting_hr', 'N/A')} bpm
- Average Sleep Duration: {health_summary.get('avg_sleep_hours', 'N/A')} hours
- Average Stress Level: {health_summary.get('avg_stress', 'N/A')}/100
- Total Active Minutes: {health_summary.get('total_active_minutes', 'N/A')}

**Current Date:** {datetime.now().strftime('%A, %B %d, %Y')}

---

### USER QUESTION
{user_query}

---

Provide a helpful, personalized response based on the user's data. Be specific and reference actual numbers when relevant."""

    @staticmethod
    def workout_plan_prompt(
        user_data: Dict[str, Any],
        fitness_goals: Dict[str, Any],
        recent_activities: List[Dict],
        health_metrics: Dict[str, Any],
        plan_duration: str = "week"
    ) -> str:
        """Build a workout plan generation prompt."""
        
        activities_summary = ""
        if recent_activities:
            for a in recent_activities[:7]:
                activity_type = a.get('activityType', {}).get('typeKey', 'Activity')
                duration = (a.get('duration', 0) or 0) / 60
                activities_summary += f"- {activity_type}: {duration:.0f} min\n"
        
        return f"""### WORKOUT PLAN GENERATION
Generate a personalized {plan_duration}ly workout plan.

**User Profile:**
- Name: {user_data.get('displayName', 'User')}
- Primary Goal: {fitness_goals.get('primary_goal', 'General Fitness')}
- Target Days/Week: {fitness_goals.get('days_per_week', 4)}
- Experience Level: {fitness_goals.get('experience', 'Intermediate')}

**Recent Activity Pattern:**
{activities_summary or 'No recent activities'}

**Health Metrics:**
- Avg Resting HR: {health_metrics.get('avg_resting_hr', 'N/A')} bpm
- Avg Sleep: {health_metrics.get('avg_sleep_hours', 'N/A')} hours
- Recovery Status: {health_metrics.get('recovery_status', 'Unknown')}

### OUTPUT FORMAT (JSON)
Respond with a valid JSON object:
{{
  "plan_name": "String",
  "description": "Brief description of the plan",
  "target_days_per_week": Number,
  "intensity_distribution": {{
    "low": Number (percentage),
    "moderate": Number (percentage),
    "high": Number (percentage)
  }},
  "workouts": [
    {{
      "day": "Monday/Tuesday/etc",
      "title": "Workout Title",
      "type": "running/strength/recovery/etc",
      "duration_minutes": Number,
      "intensity": "low/moderate/high",
      "description": "What to do",
      "key_focus": "Main benefit"
    }}
  ],
  "weekly_goals": ["Goal 1", "Goal 2"],
  "recovery_recommendations": "String"
}}

Generate the workout plan now."""

    @staticmethod
    def health_insights_prompt(
        health_data: Dict[str, Any],
        trends: Dict[str, Any],
        activities: List[Dict],
        period: str = "week"
    ) -> str:
        """Build a health insights generation prompt."""
        
        return f"""### HEALTH INSIGHTS ANALYSIS
Analyze the following health data for the past {period} and provide insights.

**Health Metrics:**
- Average Steps: {health_data.get('avg_steps', 'N/A'):,}
- Total Active Minutes: {health_data.get('total_active_minutes', 'N/A')}
- Average Resting HR: {health_data.get('avg_resting_hr', 'N/A')} bpm
- Average Sleep: {health_data.get('avg_sleep_hours', 'N/A')} hours
- Average Stress: {health_data.get('avg_stress', 'N/A')}/100

**Trends vs Previous Period:**
- Steps: {trends.get('steps_change', 0):+.1f}%
- Active Minutes: {trends.get('active_change', 0):+.1f}%
- Sleep: {trends.get('sleep_change', 0):+.1f}%

**Activity Count:** {len(activities)} workouts

### OUTPUT FORMAT (JSON)
{{
  "overall_score": Number (0-100),
  "overall_assessment": "Brief summary",
  "highlights": [
    {{
      "type": "positive/warning/info",
      "category": "sleep/activity/recovery/stress",
      "title": "String",
      "description": "String"
    }}
  ],
  "sleep_analysis": {{
    "quality_rating": "Excellent/Good/Fair/Poor",
    "insights": ["Insight 1"],
    "recommendations": ["Rec 1"]
  }},
  "activity_analysis": {{
    "consistency_rating": "Excellent/Good/Fair/Poor",
    "insights": ["Insight 1"],
    "recommendations": ["Rec 1"]
  }},
  "recovery_analysis": {{
    "status": "Excellent/Good/Fair/Needs Attention",
    "insights": ["Insight 1"],
    "recommendations": ["Rec 1"]
  }},
  "weekly_focus": "One key priority",
  "motivational_message": "Encouraging note"
}}

Generate the insights now."""

    @staticmethod
    def goal_recommendation_prompt(
        current_metrics: Dict[str, Any],
        activity_history: List[Dict]
    ) -> str:
        """Build a goal recommendation prompt."""
        
        # Calculate activity stats
        total_activities = len(activity_history)
        running_count = sum(1 for a in activity_history 
                          if a.get('activityType', {}).get('typeKey', '') == 'running')
        
        return f"""### GOAL RECOMMENDATION
Based on the user's current fitness level, recommend personalized goals.

**Current Metrics:**
- Avg Daily Steps: {current_metrics.get('avg_steps', 0):,}
- Avg Active Minutes: {current_metrics.get('total_active_minutes', 0) / 7:.0f}/day
- Avg Resting HR: {current_metrics.get('avg_resting_hr', 'N/A')} bpm
- Primary Activity: {current_metrics.get('primary_activity', 'Mixed')}

**Activity History (30 days):**
- Total Workouts: {total_activities}
- Running Workouts: {running_count}

### OUTPUT FORMAT (JSON)
{{
  "recommended_goals": [
    {{
      "name": "Goal Name",
      "description": "Description",
      "category": "steps/activity/sleep/performance",
      "target_value": Number,
      "unit": "steps/minutes/hours/etc",
      "timeframe": "weekly/monthly",
      "difficulty": "easy/moderate/challenging",
      "why": "Explanation"
    }}
  ],
  "focus_areas": ["Area 1", "Area 2"],
  "suggested_milestones": [
    {{
      "week": Number,
      "target": "Description"
    }}
  ]
}}

Generate goal recommendations now."""
