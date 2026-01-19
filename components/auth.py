"""Authentication component for Garmin Connect login."""

import streamlit as st
from pathlib import Path

from config import settings
from services.garmin_service import GarminService, AuthenticationError


def render_auth():
    """Render the authentication/login page."""
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">🏃 OrkTrack</h1>
        <p style="font-size: 1.25rem; color: #94a3b8;">
            AI-Powered Garmin Fitness Dashboard
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature highlights
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 2.5rem;">📊</div>
            <h4>Dashboard</h4>
            <p style="color: #94a3b8; font-size: 0.875rem;">
                Visualize all your health metrics
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 2.5rem;">💬</div>
            <h4>AI Chat</h4>
            <p style="color: #94a3b8; font-size: 0.875rem;">
                Ask questions about your data
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 2.5rem;">📅</div>
            <h4>Planner</h4>
            <p style="color: #94a3b8; font-size: 0.875rem;">
                AI-generated workout plans
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 2.5rem;">💡</div>
            <h4>Insights</h4>
            <p style="color: #94a3b8; font-size: 0.875rem;">
                Personalized health insights
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Login form
    st.markdown("### 🔐 Connect to Garmin")
    
    # Check for saved tokens
    token_path = Path(settings.garmin_token_path)
    has_saved_tokens = token_path.exists() and any(token_path.iterdir()) if token_path.exists() else False
    
    # Login method selection
    login_method = st.radio(
        "Login Method",
        options=["saved_tokens", "credentials"] if has_saved_tokens else ["credentials"],
        format_func=lambda x: "Use Saved Session" if x == "saved_tokens" else "Enter Credentials",
        horizontal=True,
        key="login_method"
    )
    
    if login_method == "saved_tokens":
        st.info("🔑 Found saved authentication tokens. Click below to reconnect.")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("🔗 Reconnect", use_container_width=True, type="primary"):
                _attempt_login(use_saved=True)
        with col2:
            if st.button("🗑️ Clear Saved Session", use_container_width=True):
                _clear_tokens()
    
    else:
        # Credentials form
        with st.form("login_form"):
            st.markdown("Enter your Garmin Connect credentials:")
            
            # Check for env vars
            has_env_email = bool(settings.garmin_email)
            has_env_password = bool(settings.garmin_password)
            
            if has_env_email and has_env_password:
                st.success("✅ Credentials found in environment variables")
                email = settings.garmin_email
                password = settings.garmin_password
                st.text_input("Email", value=email[:3] + "***" + email[-10:], disabled=True)
                st.text_input("Password", value="••••••••", type="password", disabled=True)
            else:
                email = st.text_input(
                    "Garmin Email",
                    placeholder="your.email@example.com",
                    help="Your Garmin Connect account email"
                )
                password = st.text_input(
                    "Garmin Password",
                    type="password",
                    placeholder="Enter your password",
                    help="Your Garmin Connect account password"
                )
            
            remember = st.checkbox("Remember me (save session)", value=True)
            
            submitted = st.form_submit_button("🚀 Connect to Garmin", use_container_width=True, type="primary")
            
            if submitted:
                if has_env_email and has_env_password:
                    _attempt_login(
                        email=settings.garmin_email,
                        password=settings.garmin_password,
                        save_tokens=remember
                    )
                elif email and password:
                    _attempt_login(email=email, password=password, save_tokens=remember)
                else:
                    st.error("Please enter both email and password")
    
    # Gemini API key section
    st.divider()
    st.markdown("### 🤖 AI Configuration")
    
    has_gemini_key = bool(settings.gemini_api_key)
    
    if has_gemini_key:
        st.success("✅ Gemini API key configured")
    else:
        st.warning("⚠️ Gemini API key not found. AI features will be limited.")
        
        with st.expander("How to get a Gemini API key"):
            st.markdown("""
            1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
            2. Sign in with your Google account
            3. Click "Create API Key"
            4. Copy the key and add it to your `.env` file:
            
            ```
            GEMINI_API_KEY=your_api_key_here
            ```
            
            5. Restart the application
            """)
    
    # Help section
    st.divider()
    with st.expander("❓ Need help?"):
        st.markdown("""
        **Troubleshooting Login Issues:**
        
        1. **Invalid Credentials**: Make sure you're using your Garmin Connect credentials (not Garmin Express)
        
        2. **Two-Factor Authentication**: If you have 2FA enabled, you may need to use an app-specific password
        
        3. **Rate Limiting**: If you see rate limit errors, wait a few minutes before trying again
        
        4. **Token Issues**: Try clearing saved tokens and logging in fresh
        
        **Setting up Environment Variables:**
        
        Create a `.env` file in the project root:
        
        ```
        GARMIN_EMAIL=your_email@example.com
        GARMIN_PASSWORD=your_password
        GEMINI_API_KEY=your_gemini_api_key
        ```
        
        **Privacy Note:**
        
        Your credentials are only used to authenticate with Garmin Connect. 
        They are never stored in plain text or transmitted to any third party.
        OAuth tokens are saved locally for session persistence.
        """)


def _attempt_login(
    email: str = None,
    password: str = None,
    use_saved: bool = False,
    save_tokens: bool = True
):
    """Attempt to login to Garmin Connect."""
    
    login_success = False
    garmin_service = None
    error_msg = None
    
    with st.spinner("Connecting to Garmin Connect..."):
        try:
            garmin_service = GarminService()
            
            if use_saved:
                login_success = garmin_service.login(
                    email=settings.garmin_email or "placeholder",
                    password=settings.garmin_password or "placeholder",
                    use_saved_tokens=True
                )
            else:
                login_success = garmin_service.login(
                    email=email,
                    password=password,
                    use_saved_tokens=False
                )
                
        except AuthenticationError as e:
            error_msg = f"❌ Authentication failed: {str(e)}"
        except Exception as e:
            error_msg = f"❌ Connection error: {str(e)}"
            st.exception(e)
    
    # Handle result outside of spinner context
    if login_success and garmin_service:
        st.session_state.authenticated = True
        st.session_state.garmin_client = garmin_service
        st.session_state.user_data = garmin_service.user_profile
        
        st.success("✅ Successfully connected to Garmin Connect!")
        st.balloons()
        # Use switch_page pattern for better state management
        import time
        time.sleep(0.5)  # Brief delay for visual feedback
        st.rerun()
    elif error_msg:
        st.error(error_msg)
    else:
        st.error("❌ Failed to connect. Please check your credentials.")


def _clear_tokens():
    """Clear saved authentication tokens."""
    token_path = Path(settings.garmin_token_path)
    
    try:
        if token_path.exists():
            for file in token_path.iterdir():
                file.unlink()
            st.success("✅ Saved session cleared")
            st.rerun()
    except Exception as e:
        st.error(f"Failed to clear tokens: {str(e)}")
