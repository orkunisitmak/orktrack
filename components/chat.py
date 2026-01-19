"""AI Chat interface component for natural language queries."""

import streamlit as st
import uuid
from datetime import datetime
from typing import List, Dict, Any

from services import GarminService, AIService
from database import DatabaseManager


def render_chat():
    """Render the AI chat interface."""
    
    st.markdown("# 💬 AI Fitness Assistant")
    st.markdown("Ask me anything about your fitness data, get workout advice, or analyze your progress")
    
    # Initialize session state for chat
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = str(uuid.uuid4())
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # AI Service check
    ai_service = AIService()
    if not ai_service.is_configured():
        st.warning("""
        ⚠️ **AI Service Not Configured**
        
        To use the AI assistant, please add your Gemini API key to the `.env` file:
        
        ```
        GEMINI_API_KEY=your_api_key_here
        ```
        
        Get your API key from [Google AI Studio](https://aistudio.google.com/apikey)
        """)
        return
    
    # Quick action buttons
    st.markdown("### Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    quick_prompts = {
        "📊 Weekly Summary": "Give me a summary of my fitness performance this week",
        "😴 Sleep Analysis": "How has my sleep been lately? Any patterns or issues?",
        "🏃 Running Tips": "Based on my recent runs, what should I focus on improving?",
        "💪 Recovery Status": "Am I well recovered? Should I train hard today or rest?",
    }
    
    with col1:
        if st.button("📊 Weekly Summary", use_container_width=True):
            _add_user_message(quick_prompts["📊 Weekly Summary"])
    
    with col2:
        if st.button("😴 Sleep Analysis", use_container_width=True):
            _add_user_message(quick_prompts["😴 Sleep Analysis"])
    
    with col3:
        if st.button("🏃 Running Tips", use_container_width=True):
            _add_user_message(quick_prompts["🏃 Running Tips"])
    
    with col4:
        if st.button("💪 Recovery Status", use_container_width=True):
            _add_user_message(quick_prompts["💪 Recovery Status"])
    
    st.divider()
    
    # Chat container
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        for message in st.session_state.messages:
            _render_message(message)
    
    # Process pending message
    if st.session_state.get("pending_message"):
        _process_message(ai_service)
    
    # Chat input
    st.divider()
    
    col1, col2 = st.columns([6, 1])
    
    with col1:
        user_input = st.chat_input(
            "Ask about your fitness data...",
            key="chat_input"
        )
    
    with col2:
        if st.button("🗑️ Clear", use_container_width=True, help="Clear chat history"):
            st.session_state.messages = []
            st.session_state.chat_session_id = str(uuid.uuid4())
            st.rerun()
    
    if user_input:
        _add_user_message(user_input)
    
    # Example prompts
    with st.expander("💡 Example questions you can ask"):
        st.markdown("""
        **Activity Analysis:**
        - "How many steps did I take last week?"
        - "Compare my running pace this month vs last month"
        - "What's my most active day of the week?"
        - "How many workouts did I complete this month?"
        
        **Health Insights:**
        - "Is my resting heart rate trending up or down?"
        - "How does my sleep affect my workout performance?"
        - "What's my average stress level?"
        - "Am I getting enough deep sleep?"
        
        **Training Advice:**
        - "Should I do an intense workout today?"
        - "What's the best time for me to exercise?"
        - "How can I improve my running endurance?"
        - "Am I overtraining?"
        
        **Goal Setting:**
        - "Help me set a realistic step goal"
        - "What should my target heart rate zones be?"
        - "How can I improve my sleep score?"
        """)


def _add_user_message(content: str):
    """Add a user message and trigger processing."""
    message = {
        "role": "user",
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    st.session_state.messages.append(message)
    st.session_state.pending_message = content
    st.rerun()


def _process_message(ai_service: AIService):
    """Process the pending message and get AI response."""
    
    pending = st.session_state.pop("pending_message", None)
    if not pending:
        return
    
    garmin: GarminService = st.session_state.garmin_client
    
    # Show thinking indicator
    with st.spinner("🤔 Analyzing your data..."):
        try:
            # Get context data
            user_data = st.session_state.user_data or {}
            
            # Get recent activities from database
            recent_activities = []
            try:
                activities = garmin.get_activities(limit=20)
                recent_activities = activities
            except Exception:
                pass
            
            # Get health summary
            health_summary = garmin.get_health_metrics_for_ai(days=7)
            
            # Prepare chat history
            chat_history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]  # Exclude current message
            ]
            
            # Get AI response
            response = ai_service.chat(
                user_query=pending,
                user_data=user_data,
                recent_activities=recent_activities,
                health_summary=health_summary,
                chat_history=chat_history,
                session_id=st.session_state.chat_session_id
            )
            
            # Add assistant response
            assistant_message = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.messages.append(assistant_message)
            
        except Exception as e:
            error_message = {
                "role": "assistant",
                "content": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "timestamp": datetime.now().isoformat(),
                "error": True
            }
            st.session_state.messages.append(error_message)
    
    st.rerun()


def _render_message(message: Dict[str, Any]):
    """Render a single chat message."""
    
    role = message.get("role", "user")
    content = message.get("content", "")
    is_error = message.get("error", False)
    
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user">
            <div class="chat-avatar user">👤</div>
            <div style="flex: 1;">
                <div style="color: #94a3b8; font-size: 0.75rem; margin-bottom: 0.25rem;">You</div>
                <div style="color: #f8fafc;">{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        avatar_style = "background: linear-gradient(135deg, #ef4444 0%, #f59e0b 100%);" if is_error else ""
        st.markdown(f"""
        <div class="chat-message assistant">
            <div class="chat-avatar assistant" style="{avatar_style}">🤖</div>
            <div style="flex: 1;">
                <div style="color: #94a3b8; font-size: 0.75rem; margin-bottom: 0.25rem;">OrkTrack AI</div>
                <div style="color: #f8fafc;">{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_chat_sidebar():
    """Render chat in sidebar mode (compact)."""
    
    st.markdown("### 💬 Quick Chat")
    
    ai_service = AIService()
    if not ai_service.is_configured():
        st.warning("AI not configured. Add GEMINI_API_KEY to .env")
        return
    
    # Compact chat history
    if "sidebar_messages" not in st.session_state:
        st.session_state.sidebar_messages = []
    
    # Show last 3 messages
    for msg in st.session_state.sidebar_messages[-3:]:
        role_icon = "👤" if msg["role"] == "user" else "🤖"
        st.markdown(f"**{role_icon}**: {msg['content'][:100]}...")
    
    # Quick input
    quick_input = st.text_input("Ask something...", key="sidebar_chat_input")
    
    if quick_input:
        st.session_state.sidebar_messages.append({
            "role": "user",
            "content": quick_input
        })
        
        # Get quick response
        response = ai_service.quick_answer(quick_input)
        st.session_state.sidebar_messages.append({
            "role": "assistant",
            "content": response
        })
        st.rerun()
