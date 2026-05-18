import streamlit as st
from database import sheets_handler

st.set_page_config(page_title="HFDB Document Tracking", layout="wide", page_icon="🗂️")

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
    """Determines user role based on the 'Division' column string."""
    div = str(user_info.get("division", "")).upper()
    if "SUPER" in div: return "Super Admin"
    if "ADMIN" in div: return "Admin"
    if "DC" in div: return "DC"
    return "Staff"

# -----------------------------------------------------------------------------
# AUTHENTICATION UI (Login & Sign Up)
# -----------------------------------------------------------------------------
def render_auth_page():
    st.title("HFDB Document Tracking System")
    st.divider()
    
    # FREEZE SCREEN FOR NEW CODE CONFIRMATION
    if st.session_state.new_code:
        st.error("⚠️ CRITICAL: Copy and save this code immediately. It will not be shown again.")
        st.markdown(
            f"<h1 style='text-align: center; font-size: 80px; color: #4CAF50;'>{st.session_state.new_code}</h1>", 
            unsafe_allow_html=True
        )
        if st.button("I have securely copied my code. Proceed to Login.", use_container_width=True, type="primary"):
            st.session_state.new_code = None
            st.rerun()
        return # Stop rendering the rest of the page

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Login")
        with st.form("login_form"):
            login_code = st.text_input("Enter your HFDB Code", type="password")
            submitted = st.form_submit_button("Access Dashboard")
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
            if st.button("Generate My Login Code"):
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
    st.sidebar.title(f"Welcome, {user['nickname']}")
    st.sidebar.caption(f"Access Level: {role} | Division: {user['division']}")
    st.sidebar.divider()
    
    # Determine allowed tabs based on role
    if role == "Super Admin":
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'STAFF', 'HOLIDAYS', 'REPORTS', 'DD']
    elif role == "Admin":
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'REPORTS']
    elif role == "DC":
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'REPORTS']
    else: # Staff
        tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM']
        
    selected_view = st.sidebar.radio("Navigation Menu", tabs)
    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        logout()

    # 2. GLOBAL SEARCH (Always visible at the top)
    st.text_input("🔍 Global Search", placeholder="Search by DTRAK NO., Subject, or Office Control No...")
    st.divider()
    
    # 3. PAGE RENDERING PLACEHOLDER
    st.header(f"🗂️ {selected_view} Workspace")
    
    # Display access parameters for our future coding reference
    if selected_view in ['INCOMING', 'OUTGOING']:
        if role in ["Super Admin", "Admin"]:
            st.info("Permission: Read & Write (All Divisions)")
        elif role == "DC":
            st.info(f"Permission: Read & Write (Filtered by Division: {user['division']})")
        else:
            st.info(f"Permission: Read & Write (Filtered by Assigned Staff: {user['name']})")
    elif selected_view == 'CONFERENCE ROOM':
        if role in ["Super Admin", "Admin"]:
            st.info("Permission: Read & Write")
        else:
            st.info("Permission: Read Only")
    else:
        st.info("Permission: Active")

# -----------------------------------------------------------------------------
# APP EXECUTION
# -----------------------------------------------------------------------------
if st.session_state.logged_in:
    render_dashboard()
else:
    render_auth_page()
