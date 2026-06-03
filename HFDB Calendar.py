import streamlit as st
import gspread
import pandas as pd
import random
import string
import smtplib
import time
import hashlib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_calendar import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="HFDB Whereabouts", page_icon="📅", layout="wide")

# Space-Maximizing CSS & Ultra-Compact Banners
st.markdown("""
    <style>
        .block-container {
            padding-top: 3.5rem !important; 
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .sticky-header {
            position: sticky;
            top: 2.875rem; 
            background-color: var(--background-color); 
            z-index: 999;
            padding: 5px 0px 5px 0px !important;
            margin-top: 0px !important; 
            margin-bottom: 5px !important;
            border-bottom: 2px solid var(--secondary-background-color);
        }
        .compact-alert-info {
            background-color: rgba(28, 131, 225, 0.1);
            color: var(--text-color);
            border-left: 4px solid #1c83e1;
            padding: 4px 10px;
            font-size: 0.85rem;
            border-radius: 4px;
            margin-bottom: 5px;
        }
        .compact-alert-success {
            background-color: rgba(43, 163, 102, 0.1);
            color: var(--text-color);
            border-left: 4px solid #2ba366;
            padding: 4px 10px;
            font-size: 0.85rem;
            border-radius: 4px;
            margin-bottom: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_next_expiration():
    now = datetime.now()
    if now.weekday() == 0 and now.hour < 6:
        return now.replace(hour=6, minute=0, second=0, microsecond=0)
    
    days_ahead = 0 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (now + timedelta(days_ahead)).replace(hour=6, minute=0, second=0, microsecond=0)

def check_session_expiration():
    if st.session_state.get('logged_in'):
        if datetime.now() > st.session_state.expiration_time:
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.user_division = None
            st.session_state.is_super_user = False
            st.warning("Session expired. Please log in again for the new week.")

def generate_ucode():
    prefix = "HFDB-"
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return prefix + suffix

def send_email(to_email, name, code):
    sender_email = st.secrets["email"]["address"]
    sender_password = st.secrets["email"]["app_password"]
    
    msg = MIMEText(f"Hello {name},\n\nYour HFDB Whereabouts login code is: {code}\n\nThis code is valid for your current session.")
    msg['Subject'] = '🔑 HFDB Whereabouts Login Code'
    msg['From'] = sender_email
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)

@st.cache_resource
def init_google_sheets():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(st.secrets["sheets"]["whereabouts_url"])

def get_color_for_name(name):
    hash_object = hashlib.md5(str(name).strip().encode())
    hash_int = int(hash_object.hexdigest(), 16)
    hue = hash_int % 360
    saturation = 60 + ((hash_int // 360) % 30)
    lightness = 30 + ((hash_int // 36000) % 15) 
    return f"hsl({hue}, {saturation}%, {lightness}%)"

def safe_get_all_records(sheet, max_retries=5):
    for attempt in range(max_retries):
        try:
            return sheet.get_all_records()
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))
            else:
                raise e

def safe_append_row(sheet, row_data, max_retries=5):
    for attempt in range(max_retries):
        try:
            sheet.append_row(row_data)
            return True
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))
            else:
                raise e 

# --- TARGETED DATA CACHING CORE ENGINE ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_divisions_data():
    all_data = {}
    try:
        all_sheets = sh.worksheets()
        sheet_map = {sheet.title: sheet for sheet in all_sheets}
        
        for div in ["DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]:
            if div in sheet_map:
                all_data[div] = safe_get_all_records(sheet_map[div])
            else:
                all_data[div] = []
    except Exception:
        for div in ["DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]:
            try:
                all_data[div] = safe_get_all_records(sh.worksheet(div))
            except Exception:
                all_data[div] = []
    return all_data

@st.cache_data(ttl=600, show_spinner=False)
def fetch_staff_data():
    staff_sheet = sh.worksheet("STAFF")
    try:
        current_year = datetime.now().year
        stored_year_val = staff_sheet.cell(1, 8).value  
        
        if not stored_year_val or str(stored_year_val).strip() != str(current_year):
            names_list = staff_sheet.col_values(2)
            total_rows = len(names_list)
            
            if total_rows > 1:
                cell_list = staff_sheet.range(f"G2:G{total_rows}")
                for cell in cell_list:
                    cell.value = 0
                staff_sheet.update_cells(cell_list)
                
            staff_sheet.update_cell(1, 8, current_year)
    except Exception:
        pass  
        
    df = pd.DataFrame(safe_get_all_records(staff_sheet))
    df.columns = df.columns.astype(str).str.strip().str.upper()
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_presets():
    try:
        preset_sheet = sh.worksheet("PRESET")
        presets = preset_sheet.col_values(1)
        if presets and presets[0].strip().upper() in ["PRESET", "PRESETS", "WHEREABOUTS", "ACTIVITY"]:
            presets = presets[1:]
        return [p for p in presets if p.strip()]
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_holidays():
    try:
        holiday_sheet = sh.worksheet("HOLIDAYS")
        df = pd.DataFrame(safe_get_all_records(holiday_sheet))
        df.columns = df.columns.astype(str).str.strip().str.upper()
        return df
    except Exception:
        return pd.DataFrame() 

# --- ULTRALIGHT AUTOMATED CREDIT OVERWRITE SYNC ENGINE ---
def sync_staff_wellness_credits(target_user, division_name):
    """
    Scans the specific division sheet, counts all mapped weekdays for Wellness Leave,
    and accurately overwrites column G on the STAFF directory to eliminate counter drifting bugs.
    """
    try:
        div_sheet = sh.worksheet(division_name)
        records = div_sheet.get_all_records()
        total_days = 0
        
        for row in records:
            row_name = str(row.get('Name', '')).strip()
            whereabouts = str(row.get('Whereabouts', '')).upper()
            if row_name == target_user and "WELLNESS LEAVE" in whereabouts:
                try:
                    start_dt = datetime.strptime(str(row.get('Start Date', '')), "%Y-%m-%d").date()
                    end_dt = datetime.strptime(str(row.get('End Date', '')), "%Y-%m-%d").date()
                    curr = start_dt
                    while curr <= end_dt:
                        if curr.weekday() < 5:  # Count Mon-Fri working days
                            total_days += 1
                        curr += timedelta(days=1)
                except Exception:
                    pass
                    
        staff_sheet_internal = sh.worksheet("STAFF")
        name_cell = staff_sheet_internal.find(target_user, in_column=2)
        if name_cell:
            staff_sheet_internal.update_cell(name_cell.row, 7, total_days)
        fetch_staff_data.clear()
    except Exception:
        pass

# --- INITIALIZATION ---
try:
    sh = init_google_sheets()
except Exception as e:
    st.error(f"Failed to connect to Google Sheets. Error details: {e}")
    st.stop()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'user_division' not in st.session_state:
    st.session_state.user_division = None
if 'is_super_user' not in st.session_state:
    st.session_state.is_super_user = False
if 'expiration_time' not in st.session_state:
    st.session_state.expiration_time = None

check_session_expiration()

if not st.session_state.logged_in:
    st.markdown('<div class="compact-alert-info">👈 <b>Mobile Users:</b> Tap the <b>></b> arrow in the top left to open the Staff Login!</div>', unsafe_allow_html=True)

# --- UI: SIDEBAR LOGIN & SYNC CONSOLE ---
with st.sidebar:
    st.header("🔑 Staff Login")
    try:
        staff_df = fetch_staff_data()
    except Exception as e:
        st.error(f"Could not connect to the 'STAFF' tab directory cache. Error: {e}")
        st.stop()
        
    if not st.session_state.logged_in:
        with st.expander("Generate New Code"):
            selected_name = st.selectbox("Select Name to Generate Code", staff_df['NAME'].tolist())
            if st.button("Send Login Code"):
                with st.spinner("Generating and securing code..."):
                    try:
                        staff_sheet = sh.worksheet("STAFF")
                        name_cell = staff_sheet.find(selected_name, in_column=2)
                        if name_cell is None:
                            st.error(f"Could not locate {selected_name} in the sheet.")
                            st.stop()
                            
                        exact_row = name_cell.row
                        user_email = staff_sheet.cell(exact_row, 3).value
                        new_code = generate_ucode()
                        
                        write_success = False
                        for attempt in range(3):
                            try:
                                staff_sheet.update_cell(exact_row, 1, new_code)
                                time.sleep(2) 
                                if str(staff_sheet.cell(exact_row, 1).value).strip() == new_code:
                                    write_success = True
                                    break 
                            except Exception:
                                time.sleep(2) 
                                
                        if not write_success:
                            st.error("Google API blocked the save. Please try again.")
                            st.stop()
                        
                        try:
                            send_email(user_email, selected_name, new_code)
                            fetch_staff_data.clear() 
                            st.success(f"Code secured and sent to {user_email}!")
                        except Exception as e:
                            st.error("Code saved, but email failed to send.")
                    except Exception as e:
                        st.error("An unexpected error occurred.")
        
        st.divider()
        entered_code = st.text_input("Enter Code", type="password")
        if st.button("Login"):
            with st.spinner("Verifying..."):
                fresh_staff_df = fetch_staff_data()
                entered_clean = entered_code.strip()
                match_df = fresh_staff_df[fresh_staff_df['UCODE'].astype(str).str.strip() == entered_clean]
                
                if not match_df.empty and entered_clean != "":
                    user_data = match_df.iloc[0]
                    st.session_state.logged_in = True
                    st.session_state.current_user = user_data['NAME']
                    st.session_state.user_division = user_data.get('DIVISION', 'Unknown')
                    st.session_state.is_super_user = entered_clean.startswith("SU-")
                    st.session_state.expiration_time = get_next_expiration()
                    st.rerun()
                else:
                    st.error("Invalid Code.")
    else:
        st.success(f"Logged in as: **{st.session_state.current_user}**")
        if st.session_state.is_super_user:
            st.warning("👑 Super User Access Enabled")
        st.info(f"Division: {st.session_state.user_division}")
        st.caption(f"Session expires: {st.session_state.expiration_time.strftime('%b %d, %H:%M')}")
        
        st.divider()
        st.markdown("### ⚡ RAM Status Console")
        if st.button("🔄 Pull Live Cloud Updates", use_container_width=True):
            fetch_all_divisions_data.clear()
            fetch_staff_data.clear()
            st.success("Global RAM Engine Refreshed!")
            time.sleep(0.5)
            st.rerun()
            
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.user_division = None
            st.session_state.is_super_user = False
            st.rerun()

# --- UI: MAIN DASHBOARD ---
st.markdown('<h1 class="sticky-header">📅 HFDB Whereabouts Tracker</h1>', unsafe_allow_html=True)

# 1. Schedule & Tracker Management View
if st.session_state.logged_in:
    # REVISED: Added '🌿 Wellness Leave Tracker' directly as a prominent top tab utility
    tab1, tab2, tab3 = st.tabs(["📝 Add Schedule", "✏️ Manage Entries", "🌿 Wellness Leave Tracker"])
    
    with tab1:
        today = datetime.now().date()
        
        # 1. MOVE SELECTORS OUTSIDE THE FORM (Triggers immediate real-time layout updates)
        if st.session_state.is_super_user:
            st.markdown("**👑 Super User:** Plotting schedule for division staff")
            staff_df = fetch_staff_data()
            div_staff = staff_df[staff_df['DIVISION'].astype(str).str.strip().str.upper() == str(st.session_state.user_division).upper().strip()]['NAME'].dropna().unique().tolist()
            if not div_staff:
                div_staff = [st.session_state.current_user]
            
            default_idx = div_staff.index(st.session_state.current_user) if st.session_state.current_user in div_staff else 0
            target_user = st.selectbox("Select Staff Member", div_staff, index=default_idx)
        else:
            target_user = st.session_state.current_user
            st.text_input("Staff Member", value=target_user, disabled=True)
            
        selected_dates = st.date_input("Select Date Range", value=(today, today))
        preset_options = fetch_presets()
        preset_options.insert(0, "Custom Input...")
        selected_preset = st.selectbox("Whereabouts / Activity", preset_options)
        
        # 2. KEEP ONLY TEXT INPUTS & BUTTON INSIDE THE FORM (Prevents keystroke lags)
        with st.form("schedule_form", clear_on_submit=True):
            if selected_preset == "Custom Input...":
                custom_in = st.text_input("Enter Custom Details", placeholder="e.g., Regional Monitoring")
                final_whereabouts = custom_in
            else:
                custom_addon = st.text_input(f"Add extra details to '{selected_preset}' (Optional)", placeholder="e.g., Specific location or reason")
            
            submitted = st.form_submit_button("Save Schedule")
            if submitted:
                # Compile the final text fields reliably upon submission trigger
                if selected_preset != "Custom Input...":
                    if custom_addon.strip():
                        final_whereabouts = f"{selected_preset} - {custom_addon.strip()}"
                    else:
                        final_whereabouts = selected_preset
                
                if len(selected_dates) == 2:
                    start_date, end_date = selected_dates[0], selected_dates[1]
                elif len(selected_dates) == 1:
                    start_date, end_date = selected_dates[0], selected_dates[0]
                else:
                    start_date, end_date = None, None
                
                if start_date and end_date and final_whereabouts.strip():
                    try:
                        div_sheet = sh.worksheet(st.session_state.user_division)
                        row_data = [str(start_date), str(end_date), target_user, final_whereabouts]
                        safe_append_row(div_sheet, row_data)
                        
                        # Run automated true recalculation overwrite sync on transaction completion
                        sync_staff_wellness_credits(target_user, st.session_state.user_division)
                        fetch_all_divisions_data.clear()
                        
                        st.markdown(f'<div class="compact-alert-success">✅ Schedule added instantly to cloud for {target_user}!</div>', unsafe_allow_html=True)
                        time.sleep(1) 
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error saving to Cloud sheet collection.")
                else:
                    st.error("Please ensure your dates and Activity Details are filled out.")

    with tab2:
        st.caption("Select an entry below to Edit or Delete its details.")
        try:
            cached_db = fetch_all_divisions_data()
            div_data = cached_db.get(st.session_state.user_division, [])
            user_entries = []
            for i, row in enumerate(div_data):
                entry_owner = str(row.get('Name', ''))
                if st.session_state.is_super_user or entry_owner == st.session_state.current_user:
                    user_entries.append({
                        "display": f"[{entry_owner}] {row.get('Start Date','')} to {row.get('End Date','')} | {row.get('Whereabouts','')}",
                        "row_index": i + 2,
                        "name": entry_owner,
                        "start": row.get('Start Date',''),
                        "end": row.get('End Date',''),
                        "whereabouts": row.get('Whereabouts','')
                    })
            
            if user_entries:
                selected_entry_display = st.selectbox("Select Entry to Manage", [e["display"] for e in user_entries])
                selected_data = next(e for e in user_entries if e["display"] == selected_entry_display)
                
                with st.form("edit_delete_form"):
                    try:
                        def_start = datetime.strptime(selected_data['start'], "%Y-%m-%d").date()
                        def_end = datetime.strptime(selected_data['end'], "%Y-%m-%d").date()
                    except:
                        today_date = datetime.now().date()
                        def_start, def_end = today_date, today_date

                    edit_dates = st.date_input("Update Date Range", value=(def_start, def_end))
                    edit_whereabouts = st.text_input("Update Whereabouts", value=selected_data['whereabouts'])
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        update_btn = st.form_submit_button("💾 Save Changes", type="primary")
                    with col2:
                        delete_btn = st.form_submit_button("🗑️ Delete Entry")

                    target_row = selected_data['row_index']

                    if update_btn:
                        if len(edit_dates) == 2:
                            new_start, new_end = edit_dates[0], edit_dates[1]
                        elif len(edit_dates) == 1:
                            new_start, new_end = edit_dates[0], edit_dates[0]
                        else:
                            new_start, new_end = None, None
                        
                        if new_start and new_end and edit_whereabouts:
                            with st.spinner("Processing Cloud update transitions..."):
                                active_sheet = sh.worksheet(st.session_state.user_division)
                                active_sheet.update(
                                    f"A{target_row}:D{target_row}",
                                    [[str(new_start), str(new_end), selected_data['name'], edit_whereabouts]]
                                )
                                
                                # REVISED: Execute clean, true recalculation sweep for the employee
                                sync_staff_wellness_credits(selected_data['name'], st.session_state.user_division)
                                fetch_all_divisions_data.clear()
                                
                                st.markdown('<div class="compact-alert-success">✅ Entry modified successfully in sheet storage!</div>', unsafe_allow_html=True)
                                time.sleep(1)
                                st.rerun()
                                
                    if delete_btn:
                        with st.spinner("Executing deletion sequences..."):
                            active_sheet = sh.worksheet(st.session_state.user_division)
                            active_sheet.delete_rows(target_row)
                            
                            # REVISED: Execute clean, true recalculation sweep for the employee
                            sync_staff_wellness_credits(selected_data['name'], st.session_state.user_division)
                            fetch_all_divisions_data.clear()
                            
                            st.markdown('<div class="compact-alert-success">✅ Entry cleanly dropped from sheet storage!</div>', unsafe_allow_html=True)
                            time.sleep(1)
                            st.rerun()
            else:
                st.markdown('<div class="compact-alert-info">You currently have no entries to manage.</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Unable to safely access entries data models. Error: {e}")

    # REVISED: Wellness Leave Tracker Logic integrated seamlessly inside the dedicated Tab 3 layout
    with tab3:
        st.markdown("### 🌿 HFDB Staff Wellness Leave Tracker")
        try:
            cached_db_internal = fetch_all_divisions_data()
            raw_staff_df = fetch_staff_data().copy()
            
            if 'NAME' in raw_staff_df.columns:
                # DYNAMIC ENGINE: Computes live weekday metrics from division logs to guarantee instant sync display
                live_calculated_counts = {}
                for div_name, rows_list in cached_db_internal.items():
                    for entry_row in rows_list:
                        e_name = str(entry_row.get('Name', '')).strip()
                        e_activity = str(entry_row.get('Whereabouts', '')).upper()
                        if "WELLNESS LEAVE" in e_activity:
                            try:
                                s_d = datetime.strptime(str(entry_row.get('Start Date', '')), "%Y-%m-%d").date()
                                e_d = datetime.strptime(str(entry_row.get('End Date', '')), "%Y-%m-%d").date()
                                active_curr = s_d
                                days_counter = 0
                                while active_curr <= e_d:
                                    if active_curr.weekday() < 5:
                                        days_counter += 1
                                    active_curr += timedelta(days=1)
                                live_calculated_counts[e_name] = live_calculated_counts.get(e_name, 0) + days_counter
                            except Exception:
                                pass

                # REVISED: Removed Job Order filtering to cleanly render ALL recorded Bureau staff rows
                raw_staff_df['USED WELLNESS LEAVE'] = raw_staff_df['NAME'].apply(lambda name_val: live_calculated_counts.get(str(name_val).strip(), 0))
                raw_staff_df['REMAINING LEAVE'] = 5 - raw_staff_df['USED WELLNESS LEAVE']
                raw_staff_df['REMAINING LEAVE'] = raw_staff_df['REMAINING LEAVE'].clip(lower=0)
                
                display_df = raw_staff_df[['NAME', 'DIVISION', 'USED WELLNESS LEAVE', 'REMAINING LEAVE']]
                st.dataframe(
                    display_df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "NAME": "Staff Name",
                        "DIVISION": "Division",
                        "USED WELLNESS LEAVE": st.column_config.NumberColumn("Used Credits (Days Plotted)", format="%d"),
                        "REMAINING LEAVE": st.column_config.ProgressColumn("Remaining Credits (Out of 5)", format="%d", min_value=0, max_value=5)
                    }
                )
            else:
                st.error("Staff directory structural mismatch encountered.")
        except Exception as e:
            st.error(f"Could not load Wellness Leave data models: {e}")

st.divider()

details_placeholder = st.empty()

# 2. Filter Tabs (REVISED: Focuses purely on individual divisions; 'WELLNESS' option cleanly removed)
divisions = ["DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]
selected_div = st.radio("Filter Dashboard View", divisions, horizontal=True)

# --- CALENDAR TRACKER LOGIC ---
nickname_map = {}
try:
    current_staff_data = fetch_staff_data()
    if 'NICKNAME' in current_staff_data.columns:
        for _, s_row in current_staff_data.iterrows():
            f_name = str(s_row['NAME']).strip()
            n_name = str(s_row['NICKNAME']).strip()
            if n_name: 
                nickname_map[f_name] = n_name
except Exception:
    pass 

if selected_div in ["DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]:
    st.markdown(f"**{selected_div} Color Legend:**")
    try:
        temp_staff_data = fetch_staff_data()
        if 'DIVISION' in temp_staff_data.columns:
            div_staff_df = temp_staff_data[temp_staff_data['DIVISION'].astype(str).str.upper().str.strip() == selected_div]
            if not div_staff_df.empty:
                staff_list = div_staff_df['NAME'].dropna().unique()
                cols = st.columns(len(staff_list) + 1)
                
                for i, raw_name in enumerate(staff_list):
                    raw_name_str = str(raw_name).strip()
                    display_name = nickname_map.get(raw_name_str, raw_name_str)
                    color = get_color_for_name(raw_name_str)
                    cols[i].markdown(f"<div style='background-color:{color}; color:white; padding:5px; border-radius:5px; text-align:center; font-size:14px; font-weight:bold; box-shadow: 0px 2px 4px rgba(0,0,0,0.2); margin-bottom: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{display_name}'>{display_name}</div>", unsafe_allow_html=True)
                
                cols[-1].markdown("<div style='background-color:#FF3B3B; color:white; padding:5px; border-radius:5px; text-align:center; font-size:14px; font-weight:bold; box-shadow: 0px 2px 4px rgba(0,0,0,0.2); margin-bottom: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='🎌 HOLIDAY'>🎌 HOLIDAY</div>", unsafe_allow_html=True)
    except Exception:
        pass

calendar_events = []
sheets_to_fetch = [selected_div]

# Render background structural configuration for holidays
holiday_df = fetch_holidays()
if not holiday_df.empty and 'DATE' in holiday_df.columns:
    for _, h_row in holiday_df.iterrows():
        raw_date = str(h_row.get('DATE', '')).strip()
        h_remarks = str(h_row.get('REMARKS', '')).strip()
        if raw_date:
            try:
                h_date = pd.to_datetime(raw_date).strftime("%Y-%m-%d")
            except Exception:
                h_date = raw_date 
            
            calendar_events.append({
                "start": h_date,
                "display": "background",
                "backgroundColor": "rgba(255, 59, 59, 0.15)" 
            })
            calendar_events.append({
                "title": f"🎌 HOLIDAY: {h_remarks}",
                "start": h_date,
                "backgroundColor": "#FF3B3B", 
                "borderColor": "#FF3B3B",
                "textColor": "#FFFFFF",
                "display": "block"
            })

# Render data parameters using optimized global data cache map
cached_db = fetch_all_divisions_data()
for div in sheets_to_fetch:
    div_data = cached_db.get(div, [])
    for row in div_data:
        try:
            end_date_obj = datetime.strptime(str(row.get('End Date','')), "%Y-%m-%d") + timedelta(days=1)
            end_str = end_date_obj.strftime("%Y-%m-%d")
        except Exception:
            end_str = str(row.get('End Date','')) 
        
        raw_name = str(row.get('Name','')).strip()
        display_name = nickname_map.get(raw_name, raw_name)
        bg_color = get_color_for_name(raw_name) 
        
        calendar_events.append({
            "title": f"{display_name} - {row.get('Whereabouts','')}",
            "start": str(row.get('Start Date','')),
            "end": end_str,
            "backgroundColor": bg_color,
            "borderColor": bg_color,
            "textColor": "#FFFFFF",
            "display": "block" 
        })

calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,dayGridWeek"
    },
    "displayEventTime": False, 
    "eventDisplay": "block",   
    "weekends": False,
    "height": 650
}

custom_calendar_css = """
    .fc-event-title {
        font-size: 10px !important; 
        font-weight: normal !important; 
        line-height: 1.2 !important;
    }
    .fc-event-main {
        padding: 1px 2px !important; 
    }
"""

details_placeholder.markdown('<div class="compact-alert-info">💡 <b>Tip:</b> Click on any colored bar in the calendar to see the full details here!</div>', unsafe_allow_html=True)

if not calendar_events:
    details_placeholder.markdown(f'<div class="compact-alert-info">No whereabouts plotted yet for {selected_div}. The calendar is currently empty.</div>', unsafe_allow_html=True)

cal_result = calendar(
    events=calendar_events, 
    options=calendar_options,
    custom_css=custom_calendar_css
)

if cal_result and cal_result.get("callback") == "eventClick":
    clicked_event = cal_result["eventClick"]["event"]
    event_details = clicked_event.get("title", "No details provided")
    start_date_click = clicked_event.get("start", "Unknown Date")[:10] 
    details_placeholder.markdown(f'<div class="compact-alert-success">🔍 <b>Full Details for {start_date_click}:</b> {event_details}</div>', unsafe_allow_html=True)
