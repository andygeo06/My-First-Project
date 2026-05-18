import streamlit as st
from database import sheets_handler
from datetime import datetime, timedelta, time

st.set_page_config(page_title="HFDB Document Tracking", layout="wide", page_icon="🗂️")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; padding-left: 3rem !important; padding-right: 3rem !important; max-width: 1250px !important; margin: 0 auto !important; }
        [data-testid="stVerticalBlock"] { gap: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# LIFECYCLE MANAGEMENT
# -----------------------------------------------------------------------------
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_info" not in st.session_state: st.session_state.user_info = None
if "new_code" not in st.session_state: st.session_state.new_code = None

def logout():
    st.session_state.logged_in = False
    st.session_state.user_info = None
    if "session_expiry" in st.session_state: del st.session_state.session_expiry
    st.rerun()

# -----------------------------------------------------------------------------
# SECURITY GATE CONTROL
# -----------------------------------------------------------------------------
def calculate_monday_expiry():
    now = datetime.now()
    current_week_monday = now - timedelta(days=now.weekday())
    target_expiry = datetime.combine(current_week_monday.date(), time(6, 0, 0))
    if now >= target_expiry: target_expiry += timedelta(days=7)
    return target_expiry

def check_session_expiration():
    if st.session_state.get("logged_in") and "session_expiry" in st.session_state:
        if datetime.now() > st.session_state.session_expiry:
            st.toast("🚨 Your weekly access session has expired. Please log in again.", icon="🔒")
            logout()

# -----------------------------------------------------------------------------
# INTERFACE FRONTEND
# -----------------------------------------------------------------------------
def render_auth_page():
    st.title("🗂️ HFDB Document Tracking System")
    st.divider()
    
    # SCREEN FREEZE FOR NEW REGISTRATION
    if st.session_state.new_code:
        st.success("🎉 Account Code Created Successfully!")
        st.info("📨 A copy of this access credential has been dispatched to your registered Staff Email address.")
        st.markdown(
            f"<h1 style='text-align: center; font-size: 65px; color: #4CAF50; background-color: #f0f2f6; padding: 20px; border-radius: 10px; font-family: monospace;'>{st.session_state.new_code}</h1>", 
            unsafe_allow_html=True
        )
        if st.button("I understand. Proceed to Login Dashboard.", use_container_width=True, type="primary"):
            st.session_state.new_code = None
            st.rerun()
        return

    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.subheader("Login Portal")
        with st.form("login_form"):
            login_code = st.text_input("Enter your HFDB Code", type="password")
            submitted = st.form_submit_button("Access Dashboard", use_container_width=True)
            if submitted:
                user = sheets_handler.authenticate_user(login_code)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.session_expiry = calculate_monday_expiry()
                    st.rerun()
                else:
                    st.error("Invalid Code. Please verify your credentials.")
            
    with col2:
        st.subheader("Registration & Code Recovery")
        all_staff = sheets_handler.get_all_staff_names()
        
        if all_staff:
            selected_name = st.selectbox("Select your name from the staff registry", all_staff)
            if st.button("Process My Account Access", use_container_width=True):
                with st.spinner("Analyzing profile security parameters..."):
                    status, payload = sheets_handler.process_registration_or_recovery(selected_name)
                    
                    if status == "CREATED":
                        st.session_state.new_code = payload
                        st.rerun()
                    elif status == "RECOVERED":
                        st.success(f"🔐 Security match confirmed! Your existing code has been emailed to: `{payload}`")
                    elif status == "NO_EMAIL":
                        st.error(payload)
                    else:
                        st.error(f"Execution Error: {payload}")
        else:
            st.warning("Staff registry index returned completely empty.")

def render_dashboard():
    user = st.session_state.user_info
    role = get_access_level(user)
    
    # 1. SIDEBAR PROFILE DETAILS
    st.sidebar.title(f"👤 {user['nickname']}")
    st.sidebar.caption(f"Role: **{role}**\n\nDiv: **{user['division']}**")
    
    if "session_expiry" in st.session_state:
        st.sidebar.caption(f"Session Expires On:\n`{st.session_state.session_expiry.strftime('%b %d, %Y (%I:%M %p)')}`")
        
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

    # 2. GLOBAL TOP SEARCH BAR
    st.text_input("🔍 Global Document Search", placeholder="Search across entries by DTRAK NO., Subject, or Office Control No...")
    st.divider()
    
    # 3. MAIN WORKSPACE HEADER
    st.header(f"🗂️ {selected_view} Workspace")
    
    # Role Banner (Now independent so it won't swallow the rest of the code!)
    if role == "Super Admin":
        st.success("👑 Master Control Mode: Full Unrestricted View & Full Edit Privileges Enabled.")
    
    st.divider()

    # 4. WORKSPACE CONTENT ROUTER
    if selected_view == 'CONFERENCE ROOM':
        current_year = datetime.now().year
        st.subheader(f"📅 Schedule Calendar Matrix — Fiscal Year {current_year}")
        
        view_col, form_col = st.columns([2, 1], gap="large")
        
        with form_col:
            st.markdown("### 📝 Reservation Request")
            with st.form("booking_form", clear_on_submit=True):
                chosen_date = st.date_input(
                    "Target Date", 
                    min_value=datetime(current_year, 1, 1), 
                    max_value=datetime(current_year, 12, 31)
                )
                slot = st.selectbox("Preferred Window", ["Whole Day", "Morning (8AM - 12PM)", "Afternoon (1PM - 5PM)"])
                activity = st.text_input("Activity/Meeting Title", placeholder="e.g., Division General Assembly")
                
                submit_booking = st.form_submit_button("Submit Temporary Booking", use_container_width=True)
                if submit_booking:
                    if activity.strip() == "":
                        st.warning("Action halted: Activity Title cannot be empty.")
                    else:
                        with st.spinner("Logging reservation query..."):
                            success = sheets_handler.add_conference_booking(
                                chosen_date, activity, slot, user['nickname'], user['division']
                            )
                            if success:
                                st.success("🎉 Request logged! Awaiting Admin authorization.")
                                st.rerun()

        with view_col:
            st.markdown("### 📑 Master Booking Timeline")
            raw_schedule = sheets_handler.get_conference_data()
            
            if raw_schedule.empty:
                st.info("No bookings recorded for this period.")
            else:
                raw_schedule["Date"] = pd.to_datetime(raw_schedule["Date"]).dt.date
                raw_schedule = raw_schedule.sort_values(by="Date", ascending=True)
                
                for idx, row in raw_schedule.iterrows():
                    is_confirmed = str(row["Status"]).strip() == "Confirmed"
                    border_color = "#4CAF50" if is_confirmed else "#FFC107"
                    bg_color = "#e8f5e9" if is_confirmed else "#fffde7"
                    badge_label = "✅ Confirmed" if is_confirmed else "⏳ Temporary / Pending Approval"
                    
                    st.markdown(f"""
                        <div style="border-left: 6px solid {border_color}; background-color: {bg_color}; padding: 12px 16px; border-radius: 4px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <strong>📅 {row['Date'].strftime('%A, %b %d, %Y')}</strong>
                                <span style="color: {border_color}; font-weight: bold; font-size: 0.85em;">{badge_label}</span>
                            </div>
                            <div style="font-size: 1.15em; font-weight: 600; margin: 4px 0;">🏷️ {row['Activity Name']}</div>
                            <div style="font-size: 0.9em; color: #555;">⏱️ Timeframe: {row['Time Slot']} | 👤 Care of: {row['Requested By']} ({row['Division']})</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Escalated confirmation panel for Admin & Super Admin
                    if role in ["Super Admin", "Admin"] and not is_confirmed:
                        if st.button(f"Approve & Hardcode Reservation: '{row['Activity Name']}'", key=f"apprv_{idx}"):
                            with st.spinner("Locking structural cell block..."):
                                if sheets_handler.confirm_conference_booking(idx):
                                    st.success("Schedule locked into master database grid!")
                                    st.rerun()

    elif selected_view in ['INCOMING', 'OUTGOING']:
        if role == "Admin": 
            st.info("⚡ Mode: Full Read & Write Access (All Divisions)")
        elif role == "DC": 
            st.info(f"📁 Mode: Division Read & Write Access (Filtered by: {user['division']})")
        elif role == "Staff":
            st.info(f"🔒 Mode: Staff Read & Write Access (Filtered by Assigned Rows: {user['name']})")
            
    else:
        st.info("⚡ Mode: View Active")

# -----------------------------------------------------------------------------
# MAIN APP ENTRY
# -----------------------------------------------------------------------------
if st.session_state.logged_in:
    check_session_expiration()
    render_dashboard()
else:
    render_auth_page()
