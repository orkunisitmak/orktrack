"""AI Workout Planner component with calendar view."""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
import json

from services import GarminService, AIService
from database import DatabaseManager


def render_planner():
    """Render the AI workout planner."""
    
    st.markdown("# 📅 AI Workout Planner")
    st.markdown("Get personalized workout plans based on your fitness data and goals")
    
    # AI Service check
    ai_service = AIService()
    if not ai_service.is_configured():
        st.warning("""
        ⚠️ **AI Service Not Configured**
        
        To use the workout planner, please add your Gemini API key.
        """)
        return
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📝 Create Plan", "📆 Current Plan", "🎯 Goals"])
    
    with tab1:
        _render_plan_creator(ai_service)
    
    with tab2:
        _render_current_plan()
    
    with tab3:
        _render_goals(ai_service)


def _render_plan_creator(ai_service: AIService):
    """Render the workout plan creation interface."""
    
    st.markdown("### Create Your Personalized Plan")
    
    garmin: GarminService = st.session_state.garmin_client
    
    # Goal selection
    col1, col2 = st.columns(2)
    
    with col1:
        primary_goal = st.selectbox(
            "Primary Goal",
            options=[
                "General Fitness",
                "Weight Loss",
                "Build Endurance",
                "Build Strength",
                "Improve Speed",
                "Train for Race",
                "Active Recovery",
            ],
            key="plan_primary_goal"
        )
    
    with col2:
        plan_duration = st.selectbox(
            "Plan Duration",
            options=["week", "month"],
            format_func=lambda x: "1 Week" if x == "week" else "4 Weeks",
            key="plan_duration"
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        workout_days = st.slider(
            "Workouts per Week",
            min_value=2,
            max_value=7,
            value=4,
            key="workout_days"
        )
    
    with col2:
        session_duration = st.slider(
            "Minutes per Session",
            min_value=15,
            max_value=120,
            value=45,
            step=15,
            key="session_duration"
        )
    
    # Focus areas
    st.markdown("#### Focus Areas")
    col1, col2, col3, col4 = st.columns(4)
    
    focus_areas = []
    with col1:
        if st.checkbox("Cardio", value=True):
            focus_areas.append("Cardio")
    with col2:
        if st.checkbox("Strength"):
            focus_areas.append("Strength")
    with col3:
        if st.checkbox("Flexibility"):
            focus_areas.append("Flexibility")
    with col4:
        if st.checkbox("Recovery"):
            focus_areas.append("Recovery")
    
    # Additional preferences
    with st.expander("Additional Preferences"):
        equipment = st.multiselect(
            "Available Equipment",
            options=["None (Bodyweight)", "Dumbbells", "Barbell", "Resistance Bands", 
                     "Pull-up Bar", "Treadmill", "Bike", "Full Gym"],
            default=["None (Bodyweight)"]
        )
        
        constraints = st.text_area(
            "Any constraints or injuries?",
            placeholder="E.g., knee injury, limited time in mornings...",
            max_chars=500
        )
    
    # Generate button
    st.divider()
    
    if st.button("🚀 Generate Workout Plan", type="primary", use_container_width=True):
        _generate_plan(
            ai_service=ai_service,
            garmin=garmin,
            primary_goal=primary_goal,
            plan_duration=plan_duration,
            workout_days=workout_days,
            session_duration=session_duration,
            focus_areas=focus_areas,
            equipment=equipment if 'equipment' in dir() else [],
            constraints=constraints if 'constraints' in dir() else ""
        )


def _generate_plan(
    ai_service: AIService,
    garmin: GarminService,
    primary_goal: str,
    plan_duration: str,
    workout_days: int,
    session_duration: int,
    focus_areas: List[str],
    equipment: List[str],
    constraints: str
):
    """Generate a workout plan using AI."""
    
    with st.spinner("🤖 Creating your personalized workout plan..."):
        try:
            # Get user data and activity history
            user_data = st.session_state.user_data or {}
            
            # Get recent activities
            try:
                recent_activities = garmin.get_activities(limit=30)
            except Exception:
                recent_activities = []
            
            # Get health metrics
            health_metrics = garmin.get_health_metrics_for_ai(days=14)
            
            # Build fitness goals
            fitness_goals = {
                "primary_goal": primary_goal,
                "workout_days": workout_days,
                "session_duration": session_duration,
                "focus_areas": focus_areas,
                "equipment": equipment,
                "constraints": constraints,
            }
            
            # Generate plan
            plan = ai_service.generate_workout_plan(
                user_data=user_data,
                fitness_goals=fitness_goals,
                recent_activities=recent_activities,
                health_metrics=health_metrics,
                plan_duration=plan_duration
            )
            
            if "error" in plan:
                st.error(f"Failed to generate plan: {plan['error']}")
                if "raw_response" in plan:
                    with st.expander("Debug: Raw Response"):
                        st.text(plan["raw_response"])
            else:
                st.success("✅ Workout plan generated successfully!")
                st.session_state.generated_plan = plan
                st.rerun()
                
        except Exception as e:
            st.error(f"Error generating plan: {str(e)}")


def _render_current_plan():
    """Render the current active workout plan."""
    
    # Check for recently generated plan
    if "generated_plan" in st.session_state:
        plan = st.session_state.generated_plan
        _display_plan(plan, is_new=True)
        return
    
    # Check database for active plan
    active_plan = DatabaseManager.get_active_plan()
    
    if not active_plan:
        st.info("""
        📝 **No Active Workout Plan**
        
        Go to the "Create Plan" tab to generate a personalized workout plan based on your Garmin data.
        """)
        return
    
    plan_data = active_plan.plan_data
    _display_plan(plan_data, is_new=False, plan_id=active_plan.id)


def _display_plan(plan: Dict[str, Any], is_new: bool = False, plan_id: Optional[int] = None):
    """Display a workout plan."""
    
    # Plan header
    st.markdown(f"### {plan.get('plan_name', 'Your Workout Plan')}")
    
    if plan.get("plan_summary"):
        st.markdown(f"*{plan['plan_summary']}*")
    
    # Plan stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Sessions", plan.get("total_sessions", len(plan.get("days", []))))
    with col2:
        total_mins = sum(d.get("duration_minutes", 0) for d in plan.get("days", []))
        st.metric("Total Minutes", f"{total_mins}")
    with col3:
        total_cals = sum(d.get("estimated_calories", 0) for d in plan.get("days", []))
        st.metric("Est. Calories", f"{total_cals:,}")
    with col4:
        workout_types = set(d.get("workout_type", "") for d in plan.get("days", []))
        st.metric("Variety", f"{len(workout_types)} types")
    
    st.divider()
    
    # Calendar view
    st.markdown("#### 📆 Weekly Schedule")
    
    days = plan.get("days", [])
    
    if days:
        # Group by day of week
        cols = st.columns(7)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for idx, day_name in enumerate(day_names):
            with cols[idx]:
                st.markdown(f"**{day_name[:3]}**")
                
                day_workouts = [d for d in days if d.get("day", "").lower() == day_name.lower()]
                
                if day_workouts:
                    for workout in day_workouts:
                        workout_type = workout.get("workout_type", "Workout")
                        
                        # Color based on type
                        type_colors = {
                            "rest": "#22c55e",
                            "running": "#ef4444",
                            "strength": "#6366f1",
                            "cardio": "#f59e0b",
                            "yoga": "#8b5cf6",
                            "cycling": "#3b82f6",
                        }
                        color = type_colors.get(workout_type.lower(), "#6366f1")
                        
                        st.markdown(f"""
                        <div style="
                            background: {color}20;
                            border-left: 3px solid {color};
                            padding: 0.5rem;
                            border-radius: 8px;
                            margin-bottom: 0.5rem;
                            font-size: 0.875rem;
                        ">
                            <strong>{workout.get('title', workout_type)}</strong><br>
                            <span style="color: #94a3b8;">
                                {workout.get('duration_minutes', 0)} min
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="
                        background: rgba(26, 26, 46, 0.5);
                        padding: 0.5rem;
                        border-radius: 8px;
                        text-align: center;
                        color: #64748b;
                    ">
                        Rest
                    </div>
                    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Detailed workouts
    st.markdown("#### 📋 Workout Details")
    
    for day in days:
        if day.get("workout_type", "").lower() == "rest":
            continue
        
        with st.expander(f"**{day.get('day', 'Day')}** - {day.get('title', 'Workout')}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**Duration:** {day.get('duration_minutes', 0)} minutes")
            with col2:
                st.markdown(f"**Intensity:** {day.get('intensity', 'Medium')}")
            with col3:
                st.markdown(f"**Est. Calories:** {day.get('estimated_calories', 0)}")
            
            if day.get("description"):
                st.markdown(f"\n{day['description']}")
            
            # Exercises
            exercises = day.get("exercises", [])
            if exercises:
                st.markdown("**Exercises:**")
                for ex in exercises:
                    sets = ex.get("sets", "")
                    reps = ex.get("reps", "")
                    set_rep = f" - {sets}x{reps}" if sets and reps else f" - {reps}" if reps else ""
                    st.markdown(f"- {ex.get('name', 'Exercise')}{set_rep}")
                    if ex.get("notes"):
                        st.caption(f"  _{ex['notes']}_")
    
    # Tips
    if plan.get("weekly_tips"):
        st.markdown("#### 💡 Tips for This Week")
        for tip in plan["weekly_tips"]:
            st.markdown(f"- {tip}")
    
    if plan.get("recovery_recommendations"):
        st.info(f"🧘 **Recovery:** {plan['recovery_recommendations']}")
    
    # Action buttons
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if is_new:
            if st.button("✅ Save Plan", use_container_width=True, type="primary"):
                # Plan is already saved during generation
                if "generated_plan" in st.session_state:
                    del st.session_state.generated_plan
                st.success("Plan saved!")
                st.rerun()
    
    with col2:
        if st.button("📤 Export Plan", use_container_width=True):
            _export_plan(plan)
    
    with col3:
        if st.button("🔄 Generate New", use_container_width=True):
            if "generated_plan" in st.session_state:
                del st.session_state.generated_plan
            st.rerun()


def _export_plan(plan: Dict[str, Any]):
    """Export plan as JSON."""
    plan_json = json.dumps(plan, indent=2, default=str)
    st.download_button(
        label="📥 Download Plan (JSON)",
        data=plan_json,
        file_name=f"workout_plan_{date.today().isoformat()}.json",
        mime="application/json"
    )


def _render_goals(ai_service: AIService):
    """Render goals management section."""
    
    st.markdown("### 🎯 Fitness Goals")
    
    # Get active goals
    active_goals = DatabaseManager.get_active_goals()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if active_goals:
            st.markdown("#### Your Active Goals")
            
            for goal in active_goals:
                progress = goal.progress_percentage
                
                st.markdown(f"""
                <div style="
                    background: rgba(26, 26, 46, 0.8);
                    border: 1px solid rgba(51, 65, 85, 0.5);
                    border-radius: 12px;
                    padding: 1rem;
                    margin-bottom: 1rem;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>{goal.name}</strong>
                        <span style="color: {'#22c55e' if progress >= 100 else '#f59e0b'};">
                            {progress:.0f}%
                        </span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.875rem; margin: 0.5rem 0;">
                        {goal.description or f'Target: {goal.target_value} {goal.unit}'}
                    </p>
                    <div style="
                        background: rgba(51, 65, 85, 0.5);
                        border-radius: 4px;
                        height: 8px;
                        overflow: hidden;
                    ">
                        <div style="
                            background: {'#22c55e' if progress >= 100 else '#6366f1'};
                            width: {min(progress, 100)}%;
                            height: 100%;
                            transition: width 0.3s ease;
                        "></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No active goals. Add a goal or get AI recommendations!")
    
    with col2:
        st.markdown("#### Quick Actions")
        
        if st.button("🤖 Get AI Recommendations", use_container_width=True):
            _get_goal_recommendations(ai_service)
        
        if st.button("➕ Add Custom Goal", use_container_width=True):
            st.session_state.show_add_goal = True
    
    # Add goal form
    if st.session_state.get("show_add_goal"):
        st.divider()
        st.markdown("#### Add New Goal")
        
        with st.form("add_goal_form"):
            goal_name = st.text_input("Goal Name", placeholder="E.g., Daily Steps")
            goal_target = st.number_input("Target Value", min_value=1, value=10000)
            goal_unit = st.text_input("Unit", placeholder="steps, minutes, km...")
            goal_timeframe = st.selectbox("Timeframe", ["daily", "weekly", "monthly"])
            goal_category = st.selectbox("Category", ["activity", "sleep", "cardio", "strength"])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Save Goal", type="primary"):
                    DatabaseManager.save_goal({
                        "name": goal_name,
                        "target_value": goal_target,
                        "unit": goal_unit,
                        "timeframe": goal_timeframe,
                        "category": goal_category,
                    })
                    st.session_state.show_add_goal = False
                    st.success("Goal saved!")
                    st.rerun()
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.show_add_goal = False
                    st.rerun()


def _get_goal_recommendations(ai_service: AIService):
    """Get AI-recommended goals."""
    
    garmin: GarminService = st.session_state.garmin_client
    
    with st.spinner("Analyzing your data for personalized goals..."):
        try:
            # Get metrics
            health_metrics = garmin.get_health_metrics_for_ai(days=30)
            
            try:
                activities = garmin.get_activities(limit=30)
            except Exception:
                activities = []
            
            # Get recommendations
            recommendations = ai_service.recommend_goals(
                current_metrics=health_metrics,
                activity_history=activities
            )
            
            if "error" in recommendations:
                st.error(f"Failed to get recommendations: {recommendations['error']}")
            else:
                st.session_state.goal_recommendations = recommendations
                st.rerun()
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Display recommendations if available
    if "goal_recommendations" in st.session_state:
        recs = st.session_state.goal_recommendations
        
        st.markdown("#### 🎯 Recommended Goals")
        st.markdown(f"*{recs.get('reasoning', '')}*")
        
        for goal in recs.get("goals", []):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                **{goal.get('name', 'Goal')}**  
                {goal.get('description', '')}  
                Target: {goal.get('target_value', 0)} {goal.get('unit', '')} ({goal.get('timeframe', 'weekly')})
                """)
            
            with col2:
                if st.button("Add", key=f"add_goal_{goal.get('name', '')}"):
                    DatabaseManager.save_goal({
                        "name": goal.get("name"),
                        "description": goal.get("description"),
                        "target_value": goal.get("target_value"),
                        "unit": goal.get("unit"),
                        "timeframe": goal.get("timeframe"),
                        "category": goal.get("category"),
                        "difficulty": goal.get("difficulty"),
                        "ai_recommended": True,
                    })
                    st.success(f"Added goal: {goal.get('name')}")
