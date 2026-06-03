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

# --- INITIALIZATION & RAM DATABASE STORAGE ---
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

# RAM Data Cache Stores
if 'calendar_data' not in st.session_state:
    st.session_state.calendar_data = None
if 'staff_df' not in st.session_state:
    st.session_state.staff_df = None
if 'presets' not in st.session_state:
    st.session_state.presets = None
if 'holidays_df' not in st.session_state:
    st.session_state.holidays_df = None

def ensure_data_loaded(force=False):
    need_load = (
        st.session_state.calendar_data is None or 
        st.session_state.staff_df is None or 
        st.session_state.presets is None or 
        st.session_state.holidays_df is None or 
        force
    )
    if need_load:
        with st.spinner("Downloading updates to local RAM engine..."):
            if st.session_state.calendar_data is None or force:
                st.session_state.calendar_data = {}
                for div in ["DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]:
                    try:
                        st.session_state.calendar_data[div] = safe_get_all_records(sh.worksheet(div))
                    except Exception:
                        st.session_state.calendar_data[div] = []
            
            if st.session_state.staff_df is None or force:
                try:
                    df = pd.DataFrame(safe_get_all_records(sh.worksheet("STAFF")))
                    df.columns = df.columns.astype(str).str.strip().str.upper()
                    st.session_state.staff_df = df
                except Exception:
                    st.session_state.staff_df = pd.DataFrame()
                    
            if st.session_state.presets is None or force:
                try:
                    preset_sheet = sh.worksheet("PRESET")
                    presets = preset_sheet.col_values(1)
                    if presets and presets[0].strip().upper() in ["PRESET", "PRESETS", "WHEREABOUTS", "ACTIVITY"]:
                        presets = presets[1:]
                    st.session_state.presets = [p for p in presets if p.strip()]
                except Exception:
                    st.session_state.presets = []
                    
            if st.session_state.holidays_df is None or force:
                try:
                    df = pd.DataFrame(safe_get_all_records(sh.worksheet("HOLIDAYS")))
                    df.columns = df.columns.astype(str).str.strip().str.upper()
                    st.session_state.holidays_df = df
                except Exception:
                    st.session_state.holidays_df = pd.DataFrame()

# Populate RAM cache layer instantly on startup
ensure_data_loaded()
check_session_expiration()

if not st.session_state.logged_in:
    st.markdown('<div class="compact-alert-info">👈 <b>Mobile Users:</b> Tap the <b>></b> arrow in the top left to open the Staff Login!</div>', unsafe_allow_html=True)

# --- UI: SIDEBAR LOGIN & SYNC CONTROL ---
with st.sidebar:
    st.header("🔑 Staff Login")
    
    if st.session_state.staff_df is not None and not st.session_state.staff_df.empty:
        staff_df = st.session_state.staff_df
    else:
        st.error("The 'STAFF' repository data model is empty or missing.")
        st.stop()
        
    if not st.session_state.logged_in:
        with st.expander("Generate New Code"):
            selected_name = st.selectbox("Select Name to Generate Code", staff_df['NAME'].tolist())
            
            if st.button("Send Login Code"):
                with st.spinner("Generating and securing code..."):
                    try:
                        # Isolated single execution handling prevents 429 loops
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
                            ensure_data_loaded(force=True) # Synchronize local cache state
                            st.success(f"Code secured and sent to {user_email}!")
                        except Exception as e:
                            st.error("Code saved, but email failed to send.")
                    except Exception as e:
                        st.error("An unexpected error occurred.")
        
        st.divider()
        entered_code = st.text_input("Enter Code", type="password")
        
        if st.button("Login"):
            with st.spinner("Verifying..."):
                try:
                    staff_sheet = sh.worksheet("STAFF")
                    fresh_records = safe_get_all_records(staff_sheet)
                    fresh_staff_df = pd.DataFrame(fresh_records)
                    fresh_staff_df.columns = fresh_staff_df.columns.astype(str).str.strip().str.upper()
                    st.session_state.staff_df = fresh_staff_df
                except Exception:
                    fresh_staff_df = st.session_state.staff_df
                
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
            ensure_data_loaded(force=True)
            st.success("RAM Engine Refreshed!")
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

# 1. Schedule Management
if st.session_state.logged_in:
    tab1, tab2 = st.tabs(["📝 Add Schedule", "✏️ Manage Entries"])
    
    with tab1:
        with st.form("schedule_form", clear_on_submit=True):
            today = datetime.now().date()
            
            if st.session_state.is_super_user:
                st.markdown("**👑 Super User:** Plotting schedule for division staff")
                staff_df = st.session_state.staff_df
                div_staff = staff_df[staff_df['DIVISION'].astype(str).str.strip().str.upper() == str(st.session_state.user_division).upper().strip()]['NAME'].dropna().unique().tolist()
                if not div_staff:
                    div_staff = [st.session_state.current_user]
                
                default_idx = div_staff.index(st.session_state.current_user) if st.session_state.current_user in div_staff else 0
                target_user = st.selectbox("Select Staff Member", div_staff, index=default_idx)
            else:
                target_user = st.session_state.current_user
                st.text_input("Staff Member", value=target_user, disabled=True)
                
            selected_dates = st.date_input("Select Date Range", value=(today, today))
            
            preset_options = list(st.session_state.presets) if st.session_state.presets else []
            preset_options.insert(0, "Custom Input...")
            selected_preset = st.selectbox("Whereabouts / Activity", preset_options)
            
            if selected_preset == "Custom Input...":
                final_whereabouts = st.text_input("Enter Custom Details", placeholder="e.g., Regional Monitoring")
            else:
                custom_addon = st.text_input(f"Add extra details to '{selected_preset}' (Optional)", placeholder="e.g., Specific location or reason")
                if custom_addon.strip():
                    final_whereabouts = f"{selected_preset} - {custom_addon.strip()}"
                else:
                    final_whereabouts = selected_preset
            
            submitted = st.form_submit_button("Save Schedule")
            if submitted:
                if len(selected_dates) == 2:
                    start_date, end_date = selected_dates[0], selected_dates[1]
                elif len(selected_dates) == 1:
                    start_date, end_date = selected_dates[0], selected_dates[0]
                else:
                    start_date, end_date = None, None
                
                if start_date and end_date and final_whereabouts:
                    try:
                        # 1. Instantly write directly through to cloud spreadsheet
                        div_sheet = sh.worksheet(st.session_state.user_division)
                        row_data = [str(start_date), str(end_date), target_user, final_whereabouts]
                        safe_append_row(div_sheet, row_data)
                        
                        # 2. Mutate state structure locally without re-downloading sheets
                        new_entry = {
                            "Start Date": str(start_date),
                            "End Date": str(end_date),
                            "Name": target_user,
                            "Whereabouts": final_whereabouts
                        }
                        if st.session_state.user_division not in st.session_state.calendar_data:
                            st.session_state.calendar_data[st.session_state.user_division] = []
                        st.session_state.calendar_data[st.session_state.user_division].append(new_entry)
                        
                        st.markdown(f'<div class="compact-alert-success">✅ Schedule added instantly to local engine & cloud for {target_user}!</div>', unsafe_allow_html=True)
                        time.sleep(1) 
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error saving data models.")
                else:
                    st.error("Please ensure your dates and Activity Details are filled out.")

    with tab2:
        st.caption("Select an entry below to Edit or Delete its details.")
        try:
            # Pulled completely from zero-cost local session memory storage
            div_data = st.session_state.calendar_data.get(st.session_state.user_division, [])
            user_entries = []
            for i, row in enumerate(div_data):
                entry_owner = str(row.get('Name', ''))
                if st.session_state.is_super_user or entry_owner == st.session_state.current_user:
                    user_entries.append({
                        "display": f"[{entry_owner}] {row.get('Start Date','')} to {row.get('End Date','')} | {row.get('Whereabouts','')}",
                        "row_index": i + 2,
                        "ram_index": i,
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

                    active_sheet = sh.worksheet(st.session_state.user_division)
                    target_row = selected_data['row_index']
                    ram_index = selected_data['ram_index']

                    if update_btn:
                        if len(edit_dates) == 2:
                            new_start, new_end = edit_dates[0], edit_dates[1]
                        elif len(edit_dates) == 1:
                            new_start, new_end = edit_dates[0], edit_dates[0]
                        else:
                            new_start, new_end = None, None
                        
                        if new_start and new_end and edit_whereabouts:
                            with st.spinner("Processing local RAM & Cloud update transactions..."):
                                # 1. Synchronize RAM Database entry instantly
                                st.session_state.calendar_data[st.session_state.user_division][ram_index] = {
                                    "Start Date": str(new_start),
                                    "End Date": str(new_end),
                                    "Name": selected_data['name'],
                                    "Whereabouts": edit_whereabouts
                                }
                                # 2. Target cloud cell range adjustment explicitly
                                active_sheet.update(
                                    f"A{target_row}:D{target_row}",
                                    [[str(new_start), str(new_end), selected_data['name'], edit_whereabouts]]
                                )
                                st.markdown('<div class="compact-alert-success">✅ Entry modified successfully in cache & sheet storage!</div>', unsafe_allow_html=True)
                                time.sleep(1)
                                st.rerun()
                                
                    if delete_btn:
                        with st.spinner("Executing deletion sequences..."):
                            # 1. Pop from local RAM map
                            st.session_state.calendar_data[st.session_state.user_division].pop(ram_index)
                            # 2. Extract out row allocation on remote sheet
                            active_sheet.delete_rows(target_row)
                            st.markdown('<div class="compact-alert-success">✅ Entry cleanly dropped from cache & sheet storage!</div>', unsafe_allow_html=True)
                            time.sleep(1)
                            st.rerun()
            else:
                st.markdown('<div class="compact-alert-info">You currently have no entries to manage.</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Unable to safely access entries data models.")

st.divider()

details_placeholder = st.empty()

# 2. Filter Tabs (Calendar View & Trackers)
divisions = ["DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN", "WELLNESS"]
selected_div = st.radio("Filter Dashboard View", divisions, horizontal=True)

# --- WELLNESS LEAVE TRACKER LOGIC (UPDATED FOR ALL STAFF) ---
if selected_div == "WELLNESS":
    st.markdown("### 🌿 Staff Wellness Leave Tracker")
    try:
        # Load instantly from state RAM memory instead of querying Google Sheets
        staff_df = st.session_state.staff_df
        
        if staff_df is not None and not staff_df.empty and 'USED WELLNESS LEAVE' in staff_df.columns:
            
            # Use all staff without filtering by "JOB ORDER" status
            wellness_df = staff_df.copy()
            
            # Convert the 'USED WELLNESS LEAVE' column to numbers, setting empty cells to 0
            wellness_df['USED WELLNESS LEAVE'] = pd.to_numeric(wellness_df['USED WELLNESS LEAVE'], errors='coerce').fillna(0)
            
            # Calculate Remaining Credits (Default 5)
            wellness_df['REMAINING LEAVE'] = 5 - wellness_df['USED WELLNESS LEAVE']
            
            # Format strictly for display
            display_df = wellness_df[['NAME', 'DIVISION', 'USED WELLNESS LEAVE', 'REMAINING LEAVE']]
            
            st.dataframe(
                display_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "NAME": "Staff Name",
                    "DIVISION": "Division",
                    "USED WELLNESS LEAVE": st.column_config.NumberColumn("Used Credits", format="%d"),
                    "REMAINING LEAVE": st.column_config.ProgressColumn("Remaining Credits", format="%d", min_value=0, max_value=5)
                }
            )
        else:
            st.error("Required column 'USED WELLNESS LEAVE' not found in the STAFF sheet. Please check column G.")
    except Exception as e:
        st.error(f"Could not load Wellness Leave data: {e}")

# --- CALENDAR TRACKER LOGIC (Pulled completely from internal RAM memory storage) ---
else:
    division_colors = {
        "DIRECTOR": "hsl(350, 70%, 40%)",    
        "HSDMSD": "hsl(210, 70%, 40%)",      
        "PPPDD": "hsl(120, 60%, 35%)",       
        "FPMD": "hsl(35, 90%, 40%)",         
        "ADMIN": "hsl(280, 60%, 45%)"        
    }

    nickname_map = {}
    try:
        current_staff_data = st.session_state.staff_df
        if current_staff_data is not None and 'NICKNAME' in current_staff_data.columns:
            for _, s_row in current_staff_data.iterrows():
                f_name = str(s_row['NAME']).strip()
                n_name = str(s_row['NICKNAME']).strip()
                if n_name and n_name != "nan": 
                    nickname_map[f_name] = n_name
    except Exception:
        pass 

    if selected_div in ["HSDMSD", "PPPDD", "FPMD", "ADMIN"]:
        st.markdown(f"**{selected_div} Color Legend:**")
        try:
            temp_staff_data = st.session_state.staff_df
            if temp_staff_data is not None and 'DIVISION' in temp_staff_data.columns:
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

    # Render Background Structural Holidays from Local RAM Dataframe 
    holiday_df = st.session_state.holidays_df
    if holiday_df is not None and not holiday_df.empty and 'DATE' in holiday_df.columns:
        for _, h_row in holiday_df.iterrows():
            raw_date = str(h_row.get('DATE', '')).strip()
            h_remarks = str(h_row.get('REMARKS', '')).strip()
            if raw_date and raw_date != "nan":
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

    # Render Entry Values directly from state memory maps
    for div in sheets_to_fetch:
        div_data = st.session_state.calendar_data.get(div, [])
        for row in div_data:
            try:
                end_date_obj = datetime.strptime(str(row.get('End Date', '')), "%Y-%m-%d") + timedelta(days=1)
                end_str = end_date_obj.strftime("%Y-%m-%d")
            except Exception:
                end_str = str(row.get('End Date', '')) 
            
            raw_name = str(row.get('Name', '')).strip()
            display_name = nickname_map.get(raw_name, raw_name)
            
                bg_color = get_color_for_name(raw_name) 
            
            calendar_events.append({
                "title": f"{display_name} - {row.get('Whereabouts', '')}",
                "start": str(row.get('Start Date', '')),
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
