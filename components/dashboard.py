"""Main dashboard component with activity and health visualizations."""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

from services import GarminService, DataProcessor
from utils.charts import ChartBuilder
from database import DatabaseManager


def render_dashboard():
    """Render the main activity dashboard."""
    
    st.markdown("# 📊 Activity Dashboard")
    st.markdown("Your comprehensive health and fitness overview")
    
    # Get data
    garmin: GarminService = st.session_state.garmin_client
    days = st.session_state.date_range
    
    # Fetch and cache data
    with st.spinner("Loading your fitness data..."):
        data = _get_dashboard_data(garmin, days)
    
    if not data:
        st.warning("No data available. Make sure your Garmin device is synced.")
        return
    
    # Today's snapshot
    _render_todays_snapshot(data)
    
    st.divider()
    
    # Main metrics tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Activity", "❤️ Heart Rate", "😴 Sleep", "🧘 Recovery"])
    
    with tab1:
        _render_activity_tab(data)
    
    with tab2:
        _render_heart_rate_tab(data)
    
    with tab3:
        _render_sleep_tab(data)
    
    with tab4:
        _render_recovery_tab(data)
    
    # Recent activities section
    st.divider()
    _render_recent_activities(data.get("activities", []))


def _get_dashboard_data(garmin: GarminService, days: int) -> Dict[str, Any]:
    """Fetch and process dashboard data."""
    
    cache_key = f"dashboard_data_{days}"
    
    # Check cache
    if cache_key in st.session_state.cached_data:
        cache_time = st.session_state.cached_data.get(f"{cache_key}_time", datetime.min)
        if datetime.now() - cache_time < timedelta(minutes=5):
            return st.session_state.cached_data[cache_key]
    
    try:
        # Fetch comprehensive data
        raw_data = garmin.get_comprehensive_data(days=days)
        
        # Process into DataFrames
        activities_df = DataProcessor.activities_to_dataframe(raw_data.get("activities", []))
        stats_df = DataProcessor.health_stats_to_dataframe(raw_data.get("daily_stats", []))
        sleep_df = DataProcessor.sleep_to_dataframe(raw_data.get("sleep_data", []))
        
        # Get summaries
        activity_summary = DataProcessor.get_activity_summary(activities_df)
        
        data = {
            "activities": raw_data.get("activities", []),
            "activities_df": activities_df,
            "stats_df": stats_df,
            "sleep_df": sleep_df,
            "activity_summary": activity_summary,
            "health_summary": raw_data.get("health_summary", {}),
            "user_profile": raw_data.get("user_profile", {}),
        }
        
        # Add today's data
        today = date.today()
        try:
            data["today_stats"] = garmin.get_stats(today)
        except Exception:
            data["today_stats"] = {}
        
        try:
            data["today_sleep"] = garmin.get_sleep_data(today)
        except Exception:
            data["today_sleep"] = {}
        
        # Cache
        st.session_state.cached_data[cache_key] = data
        st.session_state.cached_data[f"{cache_key}_time"] = datetime.now()
        
        return data
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return {}


def _render_todays_snapshot(data: Dict[str, Any]):
    """Render today's quick stats."""
    
    today_stats = data.get("today_stats", {})
    today_sleep = data.get("today_sleep", {})
    
    st.markdown("### Today's Snapshot")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Steps
    steps = today_stats.get("totalSteps", 0) or 0
    steps_goal = today_stats.get("dailyStepGoal", 10000) or 10000
    steps_pct = int((steps / steps_goal) * 100)
    
    with col1:
        st.metric(
            label="Steps",
            value=f"{steps:,}",
            delta=f"{steps_pct}% of goal",
            delta_color="normal" if steps_pct >= 100 else "off"
        )
    
    # Calories
    calories = today_stats.get("totalKilocalories", 0) or 0
    with col2:
        st.metric(
            label="Calories",
            value=f"{calories:,}",
            delta="burned today"
        )
    
    # Active Minutes
    active_mins = (
        (today_stats.get("highlyActiveSeconds", 0) or 0) +
        (today_stats.get("activeSeconds", 0) or 0)
    ) // 60
    with col3:
        st.metric(
            label="Active Minutes",
            value=f"{active_mins}",
            delta="today"
        )
    
    # Resting HR
    resting_hr = today_stats.get("restingHeartRate", "--")
    with col4:
        st.metric(
            label="Resting HR",
            value=f"{resting_hr}" if resting_hr != "--" else "--",
            delta="bpm" if resting_hr != "--" else None
        )
    
    # Sleep
    sleep_data = today_sleep.get("dailySleepDTO", {})
    sleep_hours = (sleep_data.get("sleepTimeSeconds", 0) or 0) / 3600
    with col5:
        st.metric(
            label="Last Night's Sleep",
            value=f"{sleep_hours:.1f}h" if sleep_hours > 0 else "--",
            delta="hours"
        )
    
    # Progress bar for steps
    st.progress(min(steps_pct / 100, 1.0), text=f"Step Goal Progress: {steps:,} / {steps_goal:,}")


def _render_activity_tab(data: Dict[str, Any]):
    """Render activity metrics tab."""
    
    stats_df = data.get("stats_df", pd.DataFrame())
    activities_df = data.get("activities_df", pd.DataFrame())
    activity_summary = data.get("activity_summary", {})
    
    if stats_df.empty:
        st.info("No activity data available for this period.")
        return
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_steps = int(stats_df["steps"].sum())
        st.metric("Total Steps", f"{total_steps:,}")
    
    with col2:
        avg_steps = int(stats_df["steps"].mean())
        st.metric("Daily Average", f"{avg_steps:,}")
    
    with col3:
        total_distance = stats_df["distance_km"].sum()
        st.metric("Total Distance", f"{total_distance:.1f} km")
    
    with col4:
        total_workouts = activity_summary.get("total_activities", 0)
        st.metric("Workouts", str(total_workouts))
    
    # Steps chart
    st.markdown("#### Daily Steps")
    if "date" in stats_df.columns and "steps" in stats_df.columns:
        chart = ChartBuilder.activity_summary_chart(
            stats_df,
            metric="steps",
            title=""
        )
        st.plotly_chart(chart, use_container_width=True)
    
    # Activity breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Calories Burned")
        if "calories" in stats_df.columns:
            chart = ChartBuilder.activity_summary_chart(
                stats_df,
                metric="calories",
                title=""
            )
            st.plotly_chart(chart, use_container_width=True)
    
    with col2:
        st.markdown("#### Activity Types")
        activity_types = activity_summary.get("activity_types", {})
        if activity_types:
            chart = ChartBuilder.activity_breakdown_pie(activity_types, title="")
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("No workout activities recorded in this period.")


def _render_heart_rate_tab(data: Dict[str, Any]):
    """Render heart rate metrics tab."""
    
    stats_df = data.get("stats_df", pd.DataFrame())
    
    if stats_df.empty or "resting_hr" not in stats_df.columns:
        st.info("No heart rate data available for this period.")
        return
    
    # Filter out null values
    hr_df = stats_df[stats_df["resting_hr"].notna()].copy()
    
    if hr_df.empty:
        st.info("No heart rate data available for this period.")
        return
    
    # Summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_resting = int(hr_df["resting_hr"].mean())
        st.metric("Avg Resting HR", f"{avg_resting} bpm")
    
    with col2:
        min_resting = int(hr_df["resting_hr"].min())
        st.metric("Lowest Resting HR", f"{min_resting} bpm")
    
    with col3:
        max_hr = int(hr_df["max_hr"].max()) if "max_hr" in hr_df.columns and hr_df["max_hr"].notna().any() else 0
        st.metric("Peak HR", f"{max_hr} bpm" if max_hr else "--")
    
    with col4:
        # Calculate trend
        if len(hr_df) >= 7:
            recent_avg = hr_df["resting_hr"].tail(7).mean()
            older_avg = hr_df["resting_hr"].head(7).mean() if len(hr_df) >= 14 else recent_avg
            diff = recent_avg - older_avg
            st.metric("7-Day Trend", f"{diff:+.1f} bpm")
        else:
            st.metric("7-Day Trend", "--")
    
    # Heart rate chart
    st.markdown("#### Resting Heart Rate Trend")
    
    # Prepare data for chart
    chart_df = hr_df[["date", "resting_hr"]].copy()
    if "max_hr" in hr_df.columns:
        chart_df["max_hr"] = hr_df["max_hr"]
    if "min_hr" in hr_df.columns:
        chart_df["avg_hr"] = hr_df["min_hr"]  # Use min as "low" for visualization
    
    chart = ChartBuilder.heart_rate_chart(chart_df, title="")
    st.plotly_chart(chart, use_container_width=True)
    
    # HR insights
    with st.expander("💡 Heart Rate Insights"):
        st.markdown(f"""
        **Your Resting Heart Rate Analysis:**
        
        - Average resting HR: **{avg_resting} bpm**
        - A lower resting heart rate generally indicates better cardiovascular fitness
        - Normal resting HR for adults: 60-100 bpm
        - Athletes often have resting HR of 40-60 bpm
        
        {"✅ Your resting HR is in a healthy range!" if 40 <= avg_resting <= 80 else "⚠️ Consider consulting a doctor if this seems unusual for you."}
        """)


def _render_sleep_tab(data: Dict[str, Any]):
    """Render sleep metrics tab."""
    
    sleep_df = data.get("sleep_df", pd.DataFrame())
    
    if sleep_df.empty:
        st.info("No sleep data available for this period.")
        return
    
    # Summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_sleep = sleep_df["total_hours"].mean()
        st.metric("Avg Sleep", f"{avg_sleep:.1f} hrs")
    
    with col2:
        avg_score = int(sleep_df["sleep_score"].mean()) if sleep_df["sleep_score"].notna().any() else 0
        st.metric("Avg Sleep Score", f"{avg_score}/100" if avg_score else "--")
    
    with col3:
        avg_deep = sleep_df["deep"].mean()
        st.metric("Avg Deep Sleep", f"{avg_deep:.1f} hrs")
    
    with col4:
        avg_rem = sleep_df["rem"].mean()
        st.metric("Avg REM Sleep", f"{avg_rem:.1f} hrs")
    
    # Sleep score gauge (if available)
    if sleep_df["sleep_score"].notna().any():
        latest_score = sleep_df["sleep_score"].iloc[0]
        if pd.notna(latest_score):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("#### Last Night's Score")
                gauge = ChartBuilder.sleep_score_gauge(latest_score, title="")
                st.plotly_chart(gauge, use_container_width=True)
            with col2:
                st.markdown("#### Sleep Stages Over Time")
                chart = ChartBuilder.sleep_chart(sleep_df, title="")
                st.plotly_chart(chart, use_container_width=True)
    else:
        st.markdown("#### Sleep Stages Over Time")
        chart = ChartBuilder.sleep_chart(sleep_df, title="")
        st.plotly_chart(chart, use_container_width=True)
    
    # Sleep tips
    with st.expander("💡 Sleep Tips"):
        if avg_sleep < 7:
            st.warning("""
            **You're averaging less than 7 hours of sleep.**
            
            Tips to improve:
            - Set a consistent bedtime
            - Avoid screens 1 hour before bed
            - Keep your bedroom cool and dark
            - Limit caffeine after 2 PM
            """)
        else:
            st.success("""
            **Great job on your sleep duration!**
            
            To optimize sleep quality:
            - Maintain a consistent sleep schedule
            - Get regular exercise (but not too close to bedtime)
            - Consider tracking factors that affect your sleep score
            """)


def _render_recovery_tab(data: Dict[str, Any]):
    """Render recovery/stress metrics tab."""
    
    stats_df = data.get("stats_df", pd.DataFrame())
    
    if stats_df.empty or "avg_stress" not in stats_df.columns:
        st.info("No stress/recovery data available for this period.")
        return
    
    # Filter for stress data
    stress_df = stats_df[stats_df["avg_stress"].notna()].copy()
    
    if stress_df.empty:
        st.info("No stress data available for this period.")
        return
    
    # Summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_stress = int(stress_df["avg_stress"].mean())
        st.metric("Avg Stress Level", f"{avg_stress}/100")
    
    with col2:
        low_stress_days = len(stress_df[stress_df["avg_stress"] < 40])
        st.metric("Low Stress Days", str(low_stress_days))
    
    with col3:
        high_stress_days = len(stress_df[stress_df["avg_stress"] > 60])
        st.metric("High Stress Days", str(high_stress_days))
    
    # Stress chart
    st.markdown("#### Stress Level Trend")
    
    chart_df = stress_df[["date", "avg_stress"]].copy()
    chart_df.columns = ["date", "stress"]
    
    chart = ChartBuilder.stress_chart(chart_df, title="")
    st.plotly_chart(chart, use_container_width=True)
    
    # Recovery status
    st.markdown("#### Recovery Status")
    
    if avg_stress < 30:
        status = "Excellent"
        color = "green"
        message = "Your stress levels are low. Great time for intense training!"
    elif avg_stress < 50:
        status = "Good"
        color = "blue"
        message = "Your recovery is on track. Maintain your current routine."
    elif avg_stress < 70:
        status = "Moderate"
        color = "orange"
        message = "Consider adding more rest or relaxation activities."
    else:
        status = "Needs Attention"
        color = "red"
        message = "High stress detected. Prioritize recovery and sleep."
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.8), rgba(26, 26, 46, 0.6));
        border-left: 4px solid {color};
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    ">
        <h4 style="margin: 0 0 0.5rem 0; color: {color};">Recovery Status: {status}</h4>
        <p style="margin: 0; color: #94a3b8;">{message}</p>
    </div>
    """, unsafe_allow_html=True)


def _render_recent_activities(activities: List[Dict[str, Any]]):
    """Render recent activities list."""
    
    st.markdown("### 🏋️ Recent Activities")
    
    if not activities:
        st.info("No recent activities found.")
        return
    
    # Show last 10 activities
    for activity in activities[:10]:
        activity_type = activity.get("activityType", {}).get("typeKey", "other")
        name = activity.get("activityName", activity_type.replace("_", " ").title())
        start_time = activity.get("startTimeLocal", "")[:16].replace("T", " ")
        duration = (activity.get("duration", 0) or 0) / 60
        distance = (activity.get("distance", 0) or 0) / 1000
        calories = activity.get("calories", 0) or 0
        avg_hr = activity.get("averageHR", "--")
        
        # Activity type emoji
        emoji_map = {
            "running": "🏃",
            "cycling": "🚴",
            "swimming": "🏊",
            "walking": "🚶",
            "hiking": "🥾",
            "strength_training": "💪",
            "yoga": "🧘",
            "indoor_cycling": "🚴",
            "treadmill_running": "🏃",
        }
        emoji = emoji_map.get(activity_type, "🏋️")
        
        with st.expander(f"{emoji} {name} - {start_time}"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Duration", f"{duration:.0f} min")
            with col2:
                st.metric("Distance", f"{distance:.2f} km" if distance > 0 else "--")
            with col3:
                st.metric("Calories", f"{calories:,}")
            with col4:
                st.metric("Avg HR", f"{avg_hr} bpm" if avg_hr != "--" else "--")
