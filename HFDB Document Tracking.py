import streamlit as st
import pandas as pd  
from database import sheets_handler
from datetime import datetime, timedelta, time

st.set_page_config(page_title="HFDB Document Tracking", layout="wide", page_icon="🗂️")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; padding-left: 3rem !important; padding-right: 3rem !important; max-width: 1250px !important; margin: 0 auto !important; }
        [data-testid="stVerticalBlock"] { gap: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_info" not in st.session_state: st.session_state.user_info = None
if "new_code" not in st.session_state: st.session_state.new_code = None

def logout():
    st.session_state.logged_in = False
    st.session_state.user_info = None
    if "session_expiry" in st.session_state: del st.session_state.session_expiry
    st.rerun()

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

def get_access_level(user_info):
    category = user_info.get("category")
    return str(category).strip() if category else "Staff"

def render_auth_page():
    st.title("🗂️ HFDB Document Tracking System")
    st.divider()
    
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
    
    st.sidebar.title(f"👤 {user['nickname']}")
    st.sidebar.caption(f"Role: **{role}**\n\nDiv: **{user['division']}**")
    
    if "session_expiry" in st.session_state:
        st.sidebar.caption(f"Session Expires On:\n`{st.session_state.session_expiry.strftime('%b %d, %Y (%I:%M %p)')}`")
        
    st.sidebar.divider()
    
    if role == "Super Admin": tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'STAFF', 'HOLIDAYS', 'REPORTS', 'DD']
    elif role in ["Admin", "DC"]: tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM', 'REPORTS']
    else: tabs = ['INCOMING', 'OUTGOING', 'CONFERENCE ROOM']
        
    selected_view = st.sidebar.radio("Navigation Menu", tabs)
    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True, type="secondary"): logout()

    st.text_input("🔍 Global Document Search", placeholder="Search across entries by DTRAK NO., Subject, or Office Control No...")
    st.divider()
    
    st.header(f"🗂️ {selected_view} Workspace")
    
    if role == "Super Admin":
        st.success("👑 Master Control Mode: Full Unrestricted View & Full Edit Privileges Enabled.")
    st.divider()

    # -------------------------------------------------------------------------
    # WORKSPACE ROUTING
    # -------------------------------------------------------------------------
    if selected_view == 'CONFERENCE ROOM':
        st.subheader("📅 Live Room Availability Matrix (Rolling 30 Days)")
        
        raw_schedule = sheets_handler.get_conference_data()
        today = datetime.now().date()
        
        date_range = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
        matrix_df = pd.DataFrame(index=date_range, columns=["Large Room (AM)", "Large Room (PM)", "Small Room (AM)", "Small Room (PM)"])
        matrix_df.fillna("Free", inplace=True)
        matrix_df.index.name = "Date"
        
        if not raw_schedule.empty:
            for idx, row in raw_schedule.iterrows():
                try:
                    r_date_str = pd.to_datetime(row["Date"]).strftime('%Y-%m-%d')
                    if r_date_str in matrix_df.index:
                        room = str(row["Room"]).strip()
                        slot = str(row["Time Slot"]).strip()
                        status_icon = "✅" if str(row["Status"]).strip() == "Confirmed" else "⏳"
                        cell_text = f"{status_icon} {row['Activity Name']} ({row['Requested By']})"
                        
                        if "Large" in room:
                            if "AM" in slot or "Whole Day" in slot: matrix_df.at[r_date_str, "Large Room (AM)"] = cell_text
                            if "PM" in slot or "Whole Day" in slot: matrix_df.at[r_date_str, "Large Room (PM)"] = cell_text
                        elif "Small" in room:
                            if "AM" in slot or "Whole Day" in slot: matrix_df.at[r_date_str, "Small Room (AM)"] = cell_text
                            if "PM" in slot or "Whole Day" in slot: matrix_df.at[r_date_str, "Small Room (PM)"] = cell_text
                except Exception:
                    pass
        
        display_df = matrix_df.reset_index()
        display_df["Date"] = pd.to_datetime(display_df["Date"]).dt.strftime('%b %d (%a)')
        
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
        st.divider()

        form_col, apprv_col = st.columns([1, 1], gap="large")
        
        with form_col:
            st.markdown("### 📝 Submit Reservation")
            with st.form("booking_form", clear_on_submit=True):
                chosen_date = st.date_input("Target Date", min_value=today)
                room_choice = st.selectbox("Target Facility", ["Large Conference Room", "Small Conference Room"])
                slot = st.selectbox("Preferred Window", ["AM (8:00 - 12:00)", "PM (1:00 - 5:00)", "Whole Day"])
                activity = st.text_input("Activity/Meeting Title")
                
                if st.form_submit_button("Book Temporary Slot", use_container_width=True):
                    if activity.strip() == "":
                        st.warning("Action halted: Activity Title cannot be empty.")
                    else:
                        with st.spinner("Locking coordinates..."):
                            success = sheets_handler.add_conference_booking(chosen_date, room_choice, activity, slot, user['nickname'], user['division'])
                            if success: st.rerun()

        with apprv_col:
            st.markdown("### 🔑 Admin Approval Queue")
            if role in ["Super Admin", "Admin"]:
                pending_df = raw_schedule[raw_schedule["Status"] == "Pending"]
                if pending_df.empty:
                    st.success("No pending requests in the queue. All clear!")
                else:
                    for idx, row in pending_df.iterrows():
                        st.info(f"**{row['Activity Name']}**\n\n📅 {row['Date']} | 🚪 {row['Room']} ({row['Time Slot']}) | 👤 {row['Requested By']}")
                        if st.button(f"Approve Booking", key=f"apprv_{idx}", type="primary"):
                            with st.spinner("Authorizing..."):
                                sheets_handler.confirm_conference_booking(row['Activity Name'], row['Date'])
                                st.rerun()
            else:
                st.info("Your view is restricted. Only Admins can approve pending (⏳) reservations.")

    # -------------------------------------------------------------------------
    # GENERIC DATA MANAGERS (STAFF, HOLIDAYS, DD)
    # -------------------------------------------------------------------------
    elif selected_view in ['STAFF', 'HOLIDAYS', 'DD']:
        st.subheader(f"🛠️ {selected_view} Database Manager")
        
        # Pull live sheet data using our new generic engine
        raw_data = sheets_handler.get_generic_sheet(selected_view)
        
        if role == "Super Admin":
            st.info("💡 You have direct edit access to this table. Modify cells or add rows at the bottom, then click **Save Changes**.")
            
            # Interactive Grid Engine
            edited_df = st.data_editor(raw_data, num_rows="dynamic", use_container_width=True, height=500)
            
            if st.button(f"💾 Save {selected_view} Changes", type="primary"):
                with st.spinner("Syncing to Google Workspace..."):
                    if sheets_handler.update_generic_sheet(selected_view, edited_df):
                        st.success(f"{selected_view} database synchronized successfully!")
                        st.rerun()
        else:
            # Fallback for future proofing in case you ever grant Admin read access
            st.info("👁️ Mode: Read-Only Access")
            st.dataframe(raw_data, use_container_width=True, height=500)

    # -------------------------------------------------------------------------
    # CORE TRACKING LOGIC (INCOMING / OUTGOING)
    # -------------------------------------------------------------------------
    elif selected_view in ['INCOMING', 'OUTGOING']:
        if role == "Admin": st.info("⚡ Mode: Full Read & Write Access (All Divisions)")
        elif role == "DC": st.info(f"📁 Mode: Division Read & Write Access (Filtered by: {user['division']})")
        elif role == "Staff": st.info(f"🔒 Mode: Staff Read & Write Access (Filtered by Assigned Rows: {user['name']})")
            
    else:
        st.info("⚡ Mode: View Active")

if st.session_state.logged_in:
    check_session_expiration()
    render_dashboard()
else:
    render_auth_page()
