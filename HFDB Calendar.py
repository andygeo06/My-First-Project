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

# --- TARGETED DATA CACHING ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_staff_data():
    staff_sheet = sh.worksheet("STAFF")
    
    # --- AUTOMATED ANNUAL WELLNESS RESET ENGINE ---
    try:
        current_year = datetime.now().year
        stored_year_val = staff_sheet.cell(1, 8).value  # Column H (8) tracks the active year configuration
        
        if not stored_year_val or str(stored_year_val).strip() != str(current_year):
            # Fetch names list length to find all active spreadsheet rows securely
            names_list = staff_sheet.col_values(2)
            total_rows = len(names_list)
            
            if total_rows > 1:
                # Select entire column range from G2 down to the last row entry
                cell_list = staff_sheet.range(f"G2:G{total_rows}")
                for cell in cell_list:
                    cell.value = 0
                staff_sheet.update_cells(cell_list)
                
            # Set metadata cell update indicator flags
            staff_sheet.update_cell(1, 8, current_year)
    except Exception:
        pass  # Failsafe protection layer prevents cloud data errors from blocking workflow logins
        
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

# --- INITIALIZATION & RAM DATABASE LOADER ---
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
if 'all_calendar_data' not in st.session_state:
    st.session_state.all_calendar_data = {}
if 'last_fetch_time' not in st.session_state:
    st.session_state.last_fetch_time = None

def load_calendar_data_to_ram(force=False):
    now = datetime.now()
    is_expired = st.session_state.last_fetch_time is None or (now - st.session_state.last_fetch_time).total_seconds() > 600
    if force or not st.session_state.all_calendar_data or is_expired:
        with st.spinner("Downloading updates to local RAM database..."):
            st.session_state.all_calendar_data = {}
            for div in ["DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]:
                try:
                    st.session_state.all_calendar_data[div] = safe_get_all_records(sh.worksheet(div))
                except Exception:
                    st.session_state.all_calendar_data[div] = []
            st.session_state.last_fetch_time = now

check_session_expiration()

if not st.session_state.logged_in:
    st.markdown('<div class="compact-alert-info">👈 <b>Mobile Users:</b> Tap the <b>></b> arrow in the top left to open the Staff Login!</div>', unsafe_allow_html=True)

# Pre-load local RAM data to make the UI snappy
load_calendar_data_to_ram()

# --- UI: SIDEBAR LOGIN & SYNC CONSOLE ---
with st.sidebar:
    st.header("🔑 Staff Login")
    
    try:
        staff_df = fetch_staff_data()
        staff_sheet = sh.worksheet("STAFF") 
    except Exception as e:
        st.error(f"Could not connect to the 'STAFF' tab. Error: {e}")
        st.stop()
        
    if not st.session_state.logged_in:
        with st.expander("Generate New Code"):
            selected_name = st.selectbox("Select Name to Generate Code", staff_df['NAME'].tolist())
            
            if st.button("Send Login Code"):
                with st.spinner("Generating and securing code..."):
                    try:
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
            load_calendar_data_to_ram(force=True)
            st.success("RAM Engine Synced!")
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

# 1. Schedule Management (Writes directly to RAM + writes through to Sheets background)
if st.session_state.logged_in:
    tab1, tab2 = st.tabs(["📝 Add Schedule", "✏️ Manage Entries"])
    
    with tab1:
        with st.form("schedule_form", clear_on_submit=True):
            today = datetime.now().date()
            
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
                        # 1. Update RAM database collection instantly
                        new_row_dict = {
                            "Start Date": str(start_date),
                            "End Date": str(end_date),
                            "Name": target_user,
                            "Whereabouts": final_whereabouts
                        }
                        if st.session_state.user_division not in st.session_state.all_calendar_data:
                            st.session_state.all_calendar_data[st.session_state.user_division] = []
                        st.session_state.all_calendar_data[st.session_state.user_division].append(new_row_dict)
                        
                        # 2. Write straight through to remote spreadsheet
                        div_sheet = sh.worksheet(st.session_state.user_division)
                        row_data = [str(start_date), str(end_date), target_user, final_whereabouts]
                        safe_append_row(div_sheet, row_data)
                        
                        # --- INTERCEPT WELLNESS LEAVE TRANSACTION ---
                        if "WELLNESS LEAVE" in final_whereabouts.upper():
                            try:
                                staff_sheet_internal = sh.worksheet("STAFF")
                                name_cell = staff_sheet_internal.find(target_user, in_column=2)
                                if name_cell:
                                    exact_row = name_cell.row
                                    current_used = staff_sheet_internal.cell(exact_row, 7).value
                                    try:
                                        current_used_num = int(current_used) if current_used else 0
                                    except ValueError:
                                        current_used_num = 0
                                        
                                    # Calculate working weekdays in date range range boundaries
                                    days_plotted = 0
                                    curr = start_date
                                    while curr <= end_date:
                                        if curr.weekday() < 5:  # Monday to Friday
                                            days_plotted += 1
                                        curr += timedelta(days=1)
                                        
                                    staff_sheet_internal.update_cell(exact_row, 7, current_used_num + days_plotted)
                                    fetch_staff_data.clear()
                            except Exception as e:
                                st.error(f"Schedule added, but wellness leave tracking counters failed to sync: {e}")
                        
                        st.markdown(f'<div class="compact-alert-success">✅ Schedule added instantly to local engine & cloud for {target_user}!</div>', unsafe_allow_html=True)
                        time.sleep(1) 
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error saving to Cloud sheet collection.")
                else:
                    st.error("Please ensure your dates and Activity Details are filled out.")

    with tab2:
        st.caption("Select an entry below to Edit or Delete its details.")
        try:
            div_data = st.session_state.all_calendar_data.get(st.session_state.user_division, [])
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

                    active_sheet = sh.worksheet(st.session_state.user_division)
                    target_row = selected_data['row_index']
                    ram_index = target_row - 2

                    if update_btn:
                        if len(edit_dates) == 2:
                            new_start, new_end = edit_dates[0], edit_dates[1]
                        elif len(edit_dates) == 1:
                            new_start, new_end = edit_dates[0], edit_dates[0]
                        else:
                            new_start, new_end = None, None
                        
                        if new_start and new_end and edit_whereabouts:
                            with st.spinner("Processing local RAM & Cloud update transactions..."):
                                
                                # --- UPDATE TRANSACTION CREDIT COMPENSATOR ---
                                was_wellness = "WELLNESS LEAVE" in selected_data['whereabouts'].upper()
                                is_wellness = "WELLNESS LEAVE" in edit_whereabouts.upper()
                                
                                if was_wellness or is_wellness:
                                    try:
                                        staff_sheet_internal = sh.worksheet("STAFF")
                                        name_cell = staff_sheet_internal.find(selected_data['name'], in_column=2)
                                        if name_cell:
                                            exact_row = name_cell.row
                                            current_used = staff_sheet_internal.cell(exact_row, 7).value
                                            try:
                                                current_used_num = int(current_used) if current_used else 0
                                            except ValueError:
                                                current_used_num = 0
                                            
                                            # Deduct old timeframe credits if it was a Wellness Leave
                                            if was_wellness:
                                                curr = def_start
                                                while curr <= def_end:
                                                    if curr.weekday() < 5:
                                                        current_used_num -= 1
                                                    curr += timedelta(days=1)
                                            
                                            # Add newly mapped timeframe working weights
                                            if is_wellness:
                                                curr = new_start
                                                while curr <= new_end:
                                                    if curr.weekday() < 5:
                                                        current_used_num += 1
                                                    curr += timedelta(days=1)
                                                    
                                            staff_sheet_internal.update_cell(exact_row, 7, max(0, current_used_num))
                                            fetch_staff_data.clear()
                                    except Exception:
                                        pass

                                # Update RAM Database entry instantly
                                st.session_state.all_calendar_data[st.session_state.user_division][ram_index] = {
                                    "Start Date": str(new_start),
                                    "End Date": str(new_end),
                                    "Name": selected_data['name'],
                                    "Whereabouts": edit_whereabouts
                                }
                                # Target cloud cell range adjustment explicitly
                                active_sheet.update(
                                    f"A{target_row}:D{target_row}",
                                    [[str(new_start), str(new_end), selected_data['name'], edit_whereabouts]]
                                )
                                st.markdown('<div class="compact-alert-success">✅ Entry modified successfully in cache & sheet storage!</div>', unsafe_allow_html=True)
                                time.sleep(1)
                                st.rerun()
                                
                    if delete_btn:
                        with st.spinner("Executing deletion sequences..."):
                            
                            # --- REVERT AND REFUND CREDIT UPON ENTRIES DELETION ---
                            if "WELLNESS LEAVE" in selected_data['whereabouts'].upper():
                                try:
                                    staff_sheet_internal = sh.worksheet("STAFF")
                                    name_cell = staff_sheet_internal.find(selected_data['name'], in_column=2)
                                    if name_cell:
                                        exact_row = name_cell.row
                                        current_used = staff_sheet_internal.cell(exact_row, 7).value
                                        try:
                                            current_used_num = int(current_used) if current_used else 0
                                        except ValueError:
                                            current_used_num = 0
                                            
                                        days_plotted = 0
                                        curr = def_start
                                        while curr <= def_end:
                                            if curr.weekday() < 5:
                                                days_plotted += 1
                                            curr += timedelta(days=1)
                                            
                                        staff_sheet_internal.update_cell(exact_row, 7, max(0, current_used_num - days_plotted))
                                        fetch_staff_data.clear()
                                except Exception:
                                    pass

                            # Pop from local RAM map
                            st.session_state.all_calendar_data[st.session_state.user_division].pop(ram_index)
                            # Extract out row allocation on remote sheet
                            active_sheet.delete_rows(target_row)
                            st.markdown('<div class="compact-alert-success">✅ Entry cleanly dropped from cache & sheet storage!</div>', unsafe_allow_html=True)
                            time.sleep(1)
                            st.rerun()
            else:
                st.markdown('<div class="compact-alert-info">You currently have no entries to manage.</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Unable to safely access entries data models. Error: {e}")

st.divider()

details_placeholder = st.empty()

# 2. Filter Tabs (Calendar View & Trackers)
divisions = ["DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN", "WELLNESS"]
selected_div = st.radio("Filter Dashboard View", divisions, horizontal=True)

# --- WELLNESS LEAVE TRACKER LOGIC ---
if selected_div == "WELLNESS":
    st.markdown("### 🌿 Job Order Wellness Leave Tracker")
    try:
        staff_df = fetch_staff_data()
        
        if 'STATUS' in staff_df.columns and 'USED WELLNESS LEAVE' in staff_df.columns:
            jo_df = staff_df[staff_df['STATUS'].astype(str).str.upper().str.strip() == "JOB ORDER"].copy()
            
            if not jo_df.empty:
                jo_df['USED WELLNESS LEAVE'] = pd.to_numeric(jo_df['USED WELLNESS LEAVE'], errors='coerce').fillna(0)
                jo_df['REMAINING LEAVE'] = 5 - jo_df['USED WELLNESS LEAVE']
                
                display_df = jo_df[['NAME', 'DIVISION', 'USED WELLNESS LEAVE', 'REMAINING LEAVE']]
                
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
                st.info("No Job Order staff records found in the directory.")
        else:
            st.error("Required columns ('STATUS' or 'USED WELLNESS LEAVE') not found in the STAFF sheet. Please check columns F and G.")
    except Exception as e:
        st.error(f"Could not load Wellness Leave data: {e}")

# --- CALENDAR TRACKER LOGIC ---
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
        current_staff_data = fetch_staff_data()
        if 'NICKNAME' in current_staff_data.columns:
            for _, s_row in current_staff_data.iterrows():
                f_name = str(s_row['NAME']).strip()
                n_name = str(s_row['NICKNAME']).strip()
                if n_name: 
                    nickname_map[f_name] = n_name
    except Exception:
        pass 

    if selected_div in ["HSDMSD", "PPPDD", "FPMD", "ADMIN"]:
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

    # Render structural values from RAM arrays instead of calling API sheets repeatedly
    for div in sheets_to_fetch:
        div_data = st.session_state.all_calendar_data.get(div, [])
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
