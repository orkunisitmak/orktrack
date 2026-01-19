"""Health Insights component for AI-generated reports."""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

from services import GarminService, AIService, DataProcessor
from database import DatabaseManager
from utils.charts import ChartBuilder


def render_insights():
    """Render the health insights page."""
    
    st.markdown("# 💡 Health Insights")
    st.markdown("AI-powered analysis of your health and fitness data")
    
    # AI Service check
    ai_service = AIService()
    if not ai_service.is_configured():
        st.warning("""
        ⚠️ **AI Service Not Configured**
        
        To use health insights, please add your Gemini API key.
        """)
        _render_basic_insights()
        return
    
    garmin: GarminService = st.session_state.garmin_client
    
    # Period selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        period = st.selectbox(
            "Analysis Period",
            options=["week", "month"],
            format_func=lambda x: "Last 7 Days" if x == "week" else "Last 30 Days"
        )
    
    with col2:
        if st.button("🔄 Generate New Insights", type="primary"):
            _generate_insights(ai_service, garmin, period)
    
    st.divider()
    
    # Check for cached insights or generate
    cache_key = f"insights_{period}"
    
    if cache_key in st.session_state:
        insights = st.session_state[cache_key]
        _display_insights(insights, period)
    else:
        # Check database for recent insights
        latest_insight = DatabaseManager.get_latest_insight(period)
        
        if latest_insight and (date.today() - latest_insight.insight_date).days < 1:
            insights = latest_insight.insights_data
            st.session_state[cache_key] = insights
            _display_insights(insights, period)
        else:
            st.info("Click 'Generate New Insights' to get your personalized health report.")
            _render_basic_insights()


def _generate_insights(ai_service: AIService, garmin: GarminService, period: str):
    """Generate AI health insights."""
    
    days = 7 if period == "week" else 30
    
    with st.spinner("🤖 Analyzing your health data..."):
        try:
            # Get comprehensive data
            raw_data = garmin.get_comprehensive_data(days=days)
            
            # Process data
            stats_df = DataProcessor.health_stats_to_dataframe(raw_data.get("daily_stats", []))
            sleep_df = DataProcessor.sleep_to_dataframe(raw_data.get("sleep_data", []))
            activities_df = DataProcessor.activities_to_dataframe(raw_data.get("activities", []))
            
            # Calculate health summary
            health_data = {
                "total_steps": int(stats_df["steps"].sum()) if not stats_df.empty else 0,
                "avg_steps": int(stats_df["steps"].mean()) if not stats_df.empty else 0,
                "avg_resting_hr": int(stats_df["resting_hr"].mean()) if not stats_df.empty and stats_df["resting_hr"].notna().any() else 0,
                "avg_sleep_hours": round(sleep_df["total_hours"].mean(), 1) if not sleep_df.empty else 0,
                "avg_sleep_score": int(sleep_df["sleep_score"].mean()) if not sleep_df.empty and sleep_df["sleep_score"].notna().any() else 0,
                "avg_stress": int(stats_df["avg_stress"].mean()) if not stats_df.empty and stats_df["avg_stress"].notna().any() else 0,
                "total_active_minutes": int(stats_df["active_minutes"].sum()) if not stats_df.empty else 0,
                "total_calories": int(stats_df["calories"].sum()) if not stats_df.empty else 0,
                "primary_activity": activities_df["activity_type"].mode().iloc[0] if not activities_df.empty else "N/A",
                "longest_workout_minutes": int(activities_df["duration_minutes"].max()) if not activities_df.empty else 0,
            }
            
            # Calculate trends (compare to previous period)
            trends = {
                "steps_change": 0,
                "resting_hr_change": 0,
                "sleep_change": 0,
                "active_minutes_change": 0,
                "stress_change": 0,
            }
            
            # Get AI insights
            insights = ai_service.generate_health_insights(
                health_data=health_data,
                trends=trends,
                activities=raw_data.get("activities", []),
                period=period
            )
            
            if "error" in insights:
                st.error(f"Failed to generate insights: {insights['error']}")
                if "raw_response" in insights:
                    with st.expander("Debug: Raw Response"):
                        st.text(insights["raw_response"])
            else:
                st.session_state[f"insights_{period}"] = insights
                st.success("✅ Insights generated!")
                st.rerun()
                
        except Exception as e:
            st.error(f"Error generating insights: {str(e)}")


def _display_insights(insights: Dict[str, Any], period: str):
    """Display generated health insights."""
    
    # Overall score
    overall_score = insights.get("overall_score", 0)
    overall_assessment = insights.get("overall_assessment", "")
    
    # Score gauge and summary
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Overall Health Score")
        
        score_color = "#22c55e" if overall_score >= 70 else "#f59e0b" if overall_score >= 50 else "#ef4444"
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {score_color}20, {score_color}10);
            border: 2px solid {score_color};
            border-radius: 50%;
            width: 150px;
            height: 150px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 1rem auto;
        ">
            <span style="font-size: 3rem; font-weight: 700; color: {score_color};">{overall_score}</span>
            <span style="color: #94a3b8;">/ 100</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Summary")
        st.markdown(overall_assessment)
        
        # Weekly focus
        if insights.get("weekly_focus"):
            st.info(f"🎯 **Focus Area:** {insights['weekly_focus']}")
    
    st.divider()
    
    # Highlights
    st.markdown("### 📊 Key Highlights")
    
    highlights = insights.get("highlights", [])
    
    cols = st.columns(min(len(highlights), 3))
    
    for idx, highlight in enumerate(highlights[:3]):
        with cols[idx % 3]:
            h_type = highlight.get("type", "info")
            icon = "✅" if h_type == "positive" else "⚠️" if h_type == "warning" else "ℹ️"
            color = "#22c55e" if h_type == "positive" else "#f59e0b" if h_type == "warning" else "#3b82f6"
            
            st.markdown(f"""
            <div style="
                background: {color}10;
                border-left: 4px solid {color};
                padding: 1rem;
                border-radius: 8px;
                height: 100%;
            ">
                <div style="font-size: 1.5rem;">{icon}</div>
                <h4 style="margin: 0.5rem 0;">{highlight.get('title', 'Insight')}</h4>
                <p style="color: #94a3b8; margin: 0; font-size: 0.875rem;">
                    {highlight.get('description', '')}
                </p>
                {f'<p style="color: {color}; font-weight: 600; margin-top: 0.5rem;">{highlight.get("metric", "")}: {highlight.get("value", "")}</p>' if highlight.get('metric') else ''}
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Detailed analysis sections
    col1, col2 = st.columns(2)
    
    with col1:
        # Sleep Analysis
        sleep_analysis = insights.get("sleep_analysis", {})
        if sleep_analysis:
            st.markdown("### 😴 Sleep Analysis")
            
            quality = sleep_analysis.get("quality_rating", "Unknown")
            quality_color = _get_rating_color(quality)
            
            st.markdown(f"""
            <div style="
                background: {quality_color}10;
                border: 1px solid {quality_color}40;
                padding: 1rem;
                border-radius: 12px;
            ">
                <strong style="color: {quality_color};">Quality: {quality}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Insights:**")
            for insight in sleep_analysis.get("insights", []):
                st.markdown(f"- {insight}")
            
            st.markdown("**Recommendations:**")
            for rec in sleep_analysis.get("recommendations", []):
                st.markdown(f"- {rec}")
        
        # Heart Health
        heart_health = insights.get("heart_health", {})
        if heart_health:
            st.markdown("### ❤️ Heart Health")
            
            status = heart_health.get("status", "Unknown")
            status_color = _get_rating_color(status)
            
            st.markdown(f"""
            <div style="
                background: {status_color}10;
                border: 1px solid {status_color}40;
                padding: 1rem;
                border-radius: 12px;
            ">
                <strong style="color: {status_color};">Status: {status}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Insights:**")
            for insight in heart_health.get("insights", []):
                st.markdown(f"- {insight}")
    
    with col2:
        # Activity Analysis
        activity_analysis = insights.get("activity_analysis", {})
        if activity_analysis:
            st.markdown("### 🏃 Activity Analysis")
            
            consistency = activity_analysis.get("consistency_rating", "Unknown")
            consistency_color = _get_rating_color(consistency)
            
            st.markdown(f"""
            <div style="
                background: {consistency_color}10;
                border: 1px solid {consistency_color}40;
                padding: 1rem;
                border-radius: 12px;
            ">
                <strong style="color: {consistency_color};">Consistency: {consistency}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Insights:**")
            for insight in activity_analysis.get("insights", []):
                st.markdown(f"- {insight}")
            
            st.markdown("**Recommendations:**")
            for rec in activity_analysis.get("recommendations", []):
                st.markdown(f"- {rec}")
        
        # Stress & Recovery
        stress_recovery = insights.get("stress_recovery", {})
        if stress_recovery:
            st.markdown("### 🧘 Stress & Recovery")
            
            balance = stress_recovery.get("balance_rating", "Unknown")
            balance_color = _get_rating_color(balance)
            
            st.markdown(f"""
            <div style="
                background: {balance_color}10;
                border: 1px solid {balance_color}40;
                padding: 1rem;
                border-radius: 12px;
            ">
                <strong style="color: {balance_color};">Balance: {balance}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Insights:**")
            for insight in stress_recovery.get("insights", []):
                st.markdown(f"- {insight}")
    
    # Motivational message
    st.divider()
    
    if insights.get("motivational_message"):
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            padding: 1.5rem;
            border-radius: 16px;
            text-align: center;
        ">
            <p style="font-size: 1.25rem; color: white; margin: 0;">
                💪 {insights['motivational_message']}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Generation info
    st.caption(f"Generated: {insights.get('generated_at', 'Unknown')} | Model: {insights.get('ai_model', 'Gemini')}")


def _get_rating_color(rating: str) -> str:
    """Get color based on rating."""
    rating_lower = rating.lower()
    if "excellent" in rating_lower or "good" in rating_lower:
        return "#22c55e"
    elif "fair" in rating_lower or "moderate" in rating_lower:
        return "#f59e0b"
    elif "poor" in rating_lower or "needs" in rating_lower:
        return "#ef4444"
    return "#3b82f6"


def _render_basic_insights():
    """Render basic insights without AI."""
    
    st.markdown("### 📊 Basic Stats Overview")
    
    garmin: GarminService = st.session_state.garmin_client
    
    try:
        # Get summary data
        health_summary = DatabaseManager.get_health_summary(days=7)
        sleep_summary = DatabaseManager.get_sleep_summary(days=7)
        activity_stats = DatabaseManager.get_activity_stats(days=7)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Activity")
            st.metric("Avg Daily Steps", f"{health_summary.get('avg_steps', 0):,}")
            st.metric("Total Active Minutes", f"{health_summary.get('total_active_minutes', 0)}")
            st.metric("Total Workouts", str(activity_stats.get("total_activities", 0)))
        
        with col2:
            st.markdown("#### Sleep")
            st.metric("Avg Sleep", f"{sleep_summary.get('avg_sleep_hours', 0):.1f} hrs")
            st.metric("Avg Sleep Score", f"{sleep_summary.get('avg_sleep_score', 0)}/100")
            st.metric("Avg Deep Sleep", f"{sleep_summary.get('avg_deep_hours', 0):.1f} hrs")
        
        with col3:
            st.markdown("#### Health")
            st.metric("Avg Resting HR", f"{health_summary.get('avg_resting_hr', 0)} bpm")
            st.metric("Avg Stress", f"{health_summary.get('avg_stress', 0)}/100")
            st.metric("Avg HRV", f"{sleep_summary.get('avg_hrv', 0):.0f} ms")
        
        # Simple recommendations
        st.divider()
        st.markdown("### 💡 Quick Tips")
        
        recommendations = DataProcessor.get_recommendations(
            health_summary,
            sleep_summary,
            activity_stats
        )
        
        for rec in recommendations:
            st.markdown(f"{rec.get('icon', '💡')} **{rec.get('category', '').title()}:** {rec.get('message', '')}")
            
    except Exception as e:
        st.error(f"Error loading basic stats: {str(e)}")
