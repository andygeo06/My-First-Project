import streamlit as st
from database import sheets_handler
from datetime import datetime, timedelta, time

# Page configuration
st.set_page_config(page_title="HFDB Document Tracking", layout="wide", page_icon="🗂️")

# Custom CSS for clean margins and compact layout
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 3rem !important;
            padding-right: 3rem !important;
            max-width: 1250px !important;
            margin: 0 auto !important;
        }
        [data-testid="stVerticalBlock"] {
            gap: 1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TIME EXPIRATION LOGIC (Monday 6:00 AM Cutoff)
# -----------------------------------------------------------------------------
def calculate_monday_expiry():
    """Calculates the datetime of the upcoming Monday at 6:00 AM."""
    now = datetime.now()
    # Find the current week's Monday date
    current_week_monday = now - timedelta(days=now.weekday())
    target_expiry = datetime.combine(current_week_monday.date(), time(6, 0, 0))
    
    # If we are already past this week's Monday 6 AM, the expiry is next week's Monday 6 AM
    if now >= target_expiry:
        target_expiry += timedelta(days=7)
    return target_expiry

def check_session_expiration():
    """Logs the user out automatically if the current time has passed Monday 6 AM."""
    if st.session_state.get("logged_in") and "session_expiry" in st.session_state:
        if datetime.now() > st.session_state.session_expiry:
            st.toast("🚨 Your weekly access session has expired. Please log in again.", icon="🔒")
            logout()

# -----------------------------------------------------------------------------
# SESSION STATE MANAGEMENT
# -----------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "new_code" not in st.session_state:
    st.session_state.new_code = None

def logout():
    st.session_state.logged_in = False
    st.session_state.user_info = None
    if "session_expiry" in st.session_state:
        del st.session_state.session_expiry
    st.rerun()

def get_access_level(user_info):
    """Returns the explicit user role from the Category column."""
    category = user_info.get("category")
    return str(category).strip() if category else "Staff"

# -----------------------------------------------------------------------------
# AUTHENTICATION UI (Login & Sign Up)
# -----------------------------------------------------------------------------
def render_auth_page():
    st.title("🗂️ HFDB Document Tracking System")
    st.divider()
    
    if st.session_state.new_code:
        st.error("⚠️ CRITICAL: Copy and save this code immediately. It will not be shown again.")
        st.markdown(
            f"<h1 style='text-align: center; font-size: 65px; color: #4CAF50; background-color: #f0f2f6; padding: 20px; border-radius: 10px; font-family: monospace;'>{st.session_state.new_code}</h1>", 
            unsafe_allow_html=True
        )
        if st.button("I have securely copied my code. Proceed to Login.", use_container_width=True, type="primary"):
            st.session_state.new_code = None
            st.rerun()
        return

    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.subheader("Login")
        with st.form("login_form"):
            login_code = st.text_input("Enter your HFDB Code", type="password")
            submitted = st.form_submit_button("Access Dashboard", use_container_width=True)
            if submitted:
                user = sheets_handler.authenticate_user(login_code)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    # Inject the secure weekly expiration timestamp
                    st.session_state.session_expiry = calculate_monday_expiry()
                    st.rerun()
                else:
                    st.error("Invalid Code. Please verify your credentials.")
            
    with col2:
        st.subheader("First Time Registration")
        unregistered = sheets_handler.get_unregistered_staff()
        
        if unregistered:
            selected_name = st.selectbox("Select your name from the staff registry", unregistered)
            if st.button("Generate My Login Code", use_container_width=True):
                with st.spinner("Generating secure code..."):
                    code = sheets_handler.register_new_user(selected_name)
                    if code:
                        st.session_state.new_code = code
                        st.rerun()
        else:
            st.success("All current staff members have been registered.")

# -----------------------------------------------------------------------------
# MAIN DASHBOARD ROUTER (Logged In View)
# -----------------------------------------------------------------------------
def render_dashboard():
    user = st.session_state.user_info
    role = get_access_level(user)
    
    # Sidebar Profile Details
    st.sidebar.title(f"👤 {user['nickname']}")
    st.sidebar.caption(f"Role: **{role}**\n\nDiv: **{user['division']}**")
    
    # Display session expiry info in sidebar for user peace of mind
    if "session_expiry" in st.session_state:
        expiry_str = st.session_state.session_expiry.strftime("%b %d, %Y (%I:%M %p)")
        st.sidebar.caption(f"Session Expires On:\n`{expiry_str}`")
        
    st.sidebar.divider()
    
    # Menu Routing Logic
    if role == "Super Admin":
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'STAFF', 'HOLIDAYS', 'REPORTS', 'DD']
    elif role in ["Admin", "DC"]:
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'REPORTS']
    else: 
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM']
        
    selected_view = st.sidebar.radio("Navigation Menu", tabs)
    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True, type="secondary"):
        logout()

    # Global Top Search Bar
    st.text_input("🔍 Global Document Search", placeholder="Search across entries by DTRAK NO., Subject, or Office Control No...")
    st.divider()
    
    # Main Content Area
    st.header(f"🗂️ {selected_view} Workspace")
    
    # Strict Access Rights Display (Roadmap reference for upcoming features)
    if role == "Super Admin":
        st.success("👑 Master Control Mode: Full Unrestricted View & Full Edit Privileges Enabled.")
    elif selected_view in ['INCOMING', 'OUTGOING']:
        if role == "Admin":
            st.info("⚡ Mode: Full Read & Write Access (All Divisions)")
        elif role == "DC":
            st.info(f"📁 Mode: Division Read & Write Access (Filtered by: {user['division']})")
        else:
            st.info(f"🔒 Mode: Staff Read & Write Access (Filtered by Assigned Rows: {user['name']})")
    elif selected_view == 'CONFERENCE ROOM':
        if role == "Admin":
            st.info("⚡ Mode: Read & Write Access")
        else:
            st.info("👁️ Mode: Read-Only Access")
    else:
        st.info("⚡ Mode: View Active")

# -----------------------------------------------------------------------------
# APP RUNNER
# -----------------------------------------------------------------------------
if st.session_state.logged_in:
    check_session_expiration()  # Keep a constant eye on the clock
    render_dashboard()
else:
    render_auth_page()
