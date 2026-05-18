import streamlit as st
import pandas as pd  
from database import sheets_handler
from datetime import datetime, timedelta, time

st.set_page_config(page_title="HFDB Document Tracking", layout="wide", page_icon="🗂️")

# Custom CSS for an ultra-wide, adaptive layout
st.markdown("""
    <style>
        /* Unleash the full screen width with minimal padding */
        .block-container { 
            padding-top: 1.5rem !important; 
            padding-bottom: 2rem !important; 
            padding-left: 1rem !important; 
            padding-right: 1rem !important; 
            max-width: 100% !important; 
        }
        /* Tighten vertical spacing between elements */
        [data-testid="stVerticalBlock"] { gap: 0.75rem !important; }
        
        /* Force the sidebar to be significantly narrower (~250px) */
        section[data-testid="stSidebar"] {
            min-width: 175px !important;
            max-width: 175px !important;
        }
        /* Transparent backgrounds ensure native Light/Dark theme compatibility */
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
    # CORE TRACKING LOGIC (INCOMING)
    # -------------------------------------------------------------------------
    elif selected_view == 'INCOMING':
        st.subheader("📥 INCOMING Document Tracker")
        
        # 1. Fetch live data and dropdown lists
        a1_note, master_df = sheets_handler.get_incoming_data()
        doc_types, doc_tags = sheets_handler.get_dropdown_lists()
        
        staff_df = sheets_handler.get_staff_data()
        divisions_list = staff_df["Division"].dropna().unique().tolist()
        staff_list = staff_df["Name of Staff"].dropna().unique().tolist()
        time_options = ["AM", "PM"]
        
        if master_df.empty:
            st.warning("INCOMING sheet is currently empty or unreachable.")
        else:
            # 2. Extract Columns based on the A-X layout structure
            edit_cols = master_df.columns[:17].tolist()
            form_cols = master_df.columns[17:].tolist()
            
            # Identify columns by their exact Google Sheet Letter Indices
            # A=0, C=2, D=3, E=4, F=5, G=6, M=12, O=14, P=15, Q=16
            visible_indices = [0, 2, 3, 4, 5, 6, 12, 14, 15, 16]
            allowed_edit_indices = [14, 15, 16] # O, P, Q
            
            # Map indices safely to actual column names
            visible_cols = [master_df.columns[i] for i in visible_indices if i < len(master_df.columns)]
            allowed_edit_names = [master_df.columns[i] for i in allowed_edit_indices if i < len(master_df.columns)]
            
            # 3. RBAC Filtering & Permission Setting
            if role in ["Super Admin", "Admin"]:
                st.info("⚡ Master Access: Full Read/Write (A-Q) & View (R-X)")
                st.caption(f"**Top Note (A1):** {a1_note}")
                view_df = master_df.copy() 
                disabled_cols = form_cols  
                
            elif role == "DC":
                st.info(f"📁 Division Access: Read/Write filtered for **{user['division']}**")
                div_col_name = master_df.columns[10]
                view_df = master_df[master_df[div_col_name].astype(str).str.strip() == user['division'].strip()].copy()
                
                # Slice view to ONLY the specifically requested columns
                view_df = view_df[visible_cols]
                disabled_cols = [c for c in visible_cols if c not in allowed_edit_names]
                
            else: # Staff
                st.info(f"🔒 Staff Access: Read/Write filtered for **{user['name']}**")
                staff_col_name = master_df.columns[11]
                view_df = master_df[master_df[staff_col_name].astype(str).str.strip() == user['name'].strip()].copy()
                
                # Slice view to ONLY the specifically requested columns
                view_df = view_df[visible_cols]
                disabled_cols = [c for c in visible_cols if c not in allowed_edit_names]

            # 4. Safely convert date strings to actual Datetime objects
            # Date columns: A(0), H(7), J(9), O(14)
            date_col_names = [master_df.columns[i] for i in [0, 7, 9, 14] if i < len(master_df.columns)]
            
            for col in date_col_names:
                if col in view_df.columns:
                    view_df[col] = pd.to_datetime(view_df[col], errors='coerce')

            # 5. Configure Column Types and Exact Widths (in pixels)
            # Tweak the 'width' numbers below to trial-and-error your perfect layout!
            col_config = {
                # --- DATES & TIMES (Keep these narrow) ---
                master_df.columns[0]: st.column_config.DateColumn("DATE RECEIVED", format="YYYY-MM-DD", width=90),
                master_df.columns[1]: st.column_config.SelectboxColumn("TIME RECEIVED", options=time_options, width=70),
                master_df.columns[7]: st.column_config.DateColumn("DATE RELEASED", format="YYYY-MM-DD", width=90),
                master_df.columns[8]: st.column_config.SelectboxColumn("TIME RELEASED", options=time_options, width=70),
                master_df.columns[9]: st.column_config.DateColumn("DATE SENT", format="YYYY-MM-DD", width=90),
                master_df.columns[14]: st.column_config.DateColumn("ACTION DATE", format="YYYY-MM-DD", width=90),
                master_df.columns[15]: st.column_config.SelectboxColumn("ACTION TIME", options=time_options, width=70),

                # --- TEXT COLUMNS (Give Subject more room, shrink others) ---
                master_df.columns[2]: st.column_config.TextColumn("DTRAK NO.", width=110),
                master_df.columns[3]: st.column_config.TextColumn("OFFICE CONTROL NO.", width=110),
                master_df.columns[4]: st.column_config.TextColumn("SUBJECT", width=400),
                master_df.columns[6]: st.column_config.TextColumn("ORIGINATING OFFICE", width=130),
                master_df.columns[13]: st.column_config.TextColumn("REMARKS", width=250),
                master_df.columns[16]: st.column_config.TextColumn("DOCUMENT STATUS", width=150),

                # --- DROPDOWNS ---
                master_df.columns[5]: st.column_config.SelectboxColumn("DOCUMENT TYPE", options=doc_types, width=130),
                master_df.columns[10]: st.column_config.SelectboxColumn("DIVISION", options=divisions_list, width=120),
                master_df.columns[11]: st.column_config.SelectboxColumn("STAFF ASSIGNED", options=staff_list, width=120),
                master_df.columns[12]: st.column_config.SelectboxColumn("DOCUMENT TAG", options=doc_tags, width=130),
            }

            # 6. Render Interactive Data Grid
            edited_view = st.data_editor(
                view_df,
                column_config=col_config,
                disabled=disabled_cols,
                hide_index=True,
                num_rows="dynamic" if role in ["Super Admin", "Admin"] else "fixed",
                use_container_width=True,
                height=600
            )
            
            # 7. Recombine and Save Logic
            if st.button("💾 Sync Updates to Master Sheet", type="primary"):
                with st.spinner("Stitching data and syncing to Google Workspace..."):
                    # Convert Datetimes back to clean strings ("YYYY-MM-DD" or "")
                    for col in date_col_names:
                        if col in edited_view.columns:
                            edited_view[col] = pd.to_datetime(edited_view[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna("")
                    
                    master_df.update(edited_view)
                    master_df = master_df.fillna("") 
                    
                    if sheets_handler.update_incoming_data(master_df):
                        st.success("INCOMING Tracker successfully updated!")
                        st.rerun()

    elif selected_view == 'OUTGOING':
        st.info("🚧 OUTGOING Module Pending Construction...")

if st.session_state.logged_in:
    check_session_expiration()
    render_dashboard()
else:
    render_auth_page()
