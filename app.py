"""
OrkTrack - AI-Powered Garmin Activity Dashboard
Main Streamlit application entry point.
"""

import streamlit as st
from pathlib import Path

# Page configuration must be first Streamlit command
st.set_page_config(
    page_title="OrkTrack - AI Fitness Dashboard",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/cyberjunky/python-garminconnect",
        "Report a bug": None,
        "About": "# OrkTrack\nAI-powered Garmin fitness dashboard"
    }
)

# Load custom CSS
def load_css():
    """Load custom CSS styles."""
    css_file = Path(__file__).parent / "assets" / "style.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Import components after page config
from config import settings
from database import init_db
from components import render_auth, render_dashboard, render_chat, render_planner, render_insights


def init_session_state():
    """Initialize Streamlit session state variables."""
    defaults = {
        "authenticated": False,
        "garmin_client": None,
        "user_data": None,
        "chat_history": [],
        "current_page": "dashboard",
        "date_range": 30,
        "fitness_goals": {},
        "cached_data": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """Render the navigation sidebar."""
    with st.sidebar:
        # Logo and title
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="font-size: 2rem; margin: 0;">🏃 OrkTrack</h1>
            <p style="color: #94a3b8; margin-top: 0.5rem;">AI Fitness Dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        if st.session_state.authenticated:
            # Navigation
            st.markdown("### Navigation")
            
            pages = {
                "dashboard": ("📊", "Dashboard"),
                "chat": ("💬", "AI Assistant"),
                "planner": ("📅", "Workout Planner"),
                "insights": ("💡", "Health Insights"),
            }
            
            for page_id, (icon, label) in pages.items():
                if st.button(
                    f"{icon} {label}",
                    key=f"nav_{page_id}",
                    use_container_width=True,
                    type="primary" if st.session_state.current_page == page_id else "secondary"
                ):
                    st.session_state.current_page = page_id
                    st.rerun()
            
            st.divider()
            
            # Date range selector
            st.markdown("### Data Range")
            days = st.selectbox(
                "Show data for",
                options=[7, 14, 30, 60, 90, 180, 365],
                index=2,
                format_func=lambda x: f"Last {x} days",
                key="date_range_selector"
            )
            if days != st.session_state.date_range:
                st.session_state.date_range = days
                st.session_state.cached_data = {}  # Clear cache on range change
            
            st.divider()
            
            # User info and logout
            if st.session_state.user_data:
                st.markdown("### Account")
                user = st.session_state.user_data
                if isinstance(user, dict):
                    st.markdown(f"**{user.get('displayName', 'User')}**")
                    st.caption(f"📧 {user.get('email', '')}")
                else:
                    st.markdown(f"**{user}**")
            
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.garmin_client = None
                st.session_state.user_data = None
                st.session_state.cached_data = {}
                st.rerun()
        else:
            st.info("Please log in to access your Garmin data.")
            
            # Quick setup guide
            with st.expander("📖 Quick Setup Guide"):
                st.markdown("""
                1. Create a `.env` file with your credentials
                2. Add your Garmin email and password
                3. Add your Gemini API key
                4. Click Login to connect
                
                ```
                GARMIN_EMAIL=your@email.com
                GARMIN_PASSWORD=your_password
                GEMINI_API_KEY=your_api_key
                ```
                """)


def main():
    """Main application entry point."""
    try:
        # Initialize database
        init_db()
        
        # Initialize session state
        init_session_state()
        
        # Render sidebar navigation
        render_sidebar()
        
        # Debug: Show authentication state
        st.sidebar.write(f"🔑 Auth: {st.session_state.authenticated}")
        
        # Main content area
        if not st.session_state.authenticated:
            render_auth()
        else:
            # Render current page
            page = st.session_state.current_page
            
            try:
                if page == "dashboard":
                    render_dashboard()
                elif page == "chat":
                    render_chat()
                elif page == "planner":
                    render_planner()
                elif page == "insights":
                    render_insights()
                else:
                    render_dashboard()
            except Exception as e:
                st.error(f"Error rendering {page}: {str(e)}")
                st.exception(e)
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
