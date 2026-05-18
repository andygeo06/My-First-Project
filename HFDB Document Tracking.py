import streamlit as st
from database import sheets_handler

# Page config set to wide, but custom CSS below will tame the width
st.set_page_config(page_title="HFDB Document Tracking", layout="wide", page_icon="🗂️")

# -----------------------------------------------------------------------------
# CUSTOM CSS: REDUCE MARGINS & TIGHTEN LOOK
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
        /* Tighten margins and set a beautiful, readable maximum screen width */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 3rem !important;
            padding-right: 3rem !important;
            max-width: 1250px !important;
            margin: 0 auto !important;
        }
        /* Tighten spacing between elements slightly */
        [data-testid="stVerticalBlock"] {
            gap: 1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

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
    st.rerun()

def get_access_level(user_info):
    """Returns the explicit user role from the Category column (Col G)."""
    category = user_info.get("category")
    return str(category).strip() if category else "Staff"

# -----------------------------------------------------------------------------
# AUTHENTICATION UI (Login & Sign Up)
# -----------------------------------------------------------------------------
def render_auth_page():
    st.title("🗂️ HFDB Document Tracking System")
    st.divider()
    
    # CRITICAL SCREEN FREEZE FOR NEW REGISTRATION CODE
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
    
    # 1. SIDEBAR NAVIGATION
    st.sidebar.title(f"👤 {user['nickname']}")
    st.sidebar.caption(f"Role: **{role}**\n\nDiv: **{user['division']}**")
    st.sidebar.divider()
    
    # Dynamically assign workspace menus based on exact roles
    if role == "Super Admin":
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'STAFF', 'HOLIDAYS', 'REPORTS', 'DD']
    elif role == "Admin":
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'REPORTS']
    elif role == "DC":
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'REPORTS']
    else: 
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM']
        
    selected_view = st.sidebar.radio("Navigation Menu", tabs)
    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True, type="secondary"):
        logout()

    # 2. GLOBAL SEARCHBAR (Top of screen)
    st.text_input("🔍 Global Document Search", placeholder="Search across files by DTRAK NO., Subject, or Office Control No...")
    st.divider()
    
    # 3. PAGE CONTENT PLACEHOLDER
    st.header(f"🗂️ {selected_view} Workspace")
    
    # Access rights indicator for our roadmap reference
    if selected_view in ['INCOMING', 'OUTGOING']:
        if role in ["Super Admin", "Admin"]:
            st.info("⚡ Mode: Full Read & Write Access (All Entries)")
        elif role == "DC":
            st.info(f"📁 Mode: Division Read & Write Access (Filtered by: {user['division']})")
        else:
            st.info(f"🔒 Mode: Staff Read & Write Access (Filtered by Assigned Rows: {user['name']})")
    elif selected_view == 'CONFERENCE ROOM':
        if role in ["Super Admin", "Admin"]:
            st.info("⚡ Mode: Read & Write Access")
        else:
            st.info("👁️ Mode: Read-Only Access")
    else:
        st.info("⚡ Mode: View Active")

# -----------------------------------------------------------------------------
# APP RUNNER
# -----------------------------------------------------------------------------
if st.session_state.logged_in:
    render_dashboard()
else:
    render_auth_page()
