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

# --- TARGETED CACHING FUNCTIONS ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_staff_data():
    staff_sheet = sh.worksheet("STAFF")
    df = pd.DataFrame(safe_get_all_records(staff_sheet))
    df.columns = df.columns.astype(str).str.strip().str.upper()
    return df

@st.cache_data(ttl=300, show_spinner=False)
def fetch_division_data(div_name):
    return safe_get_all_records(sh.worksheet(div_name))

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

# UPGRADE: Fetch Holidays Function
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_holidays():
    try:
        holiday_sheet = sh.worksheet("HOLIDAYS")
        df = pd.DataFrame(safe_get_all_records(holiday_sheet))
        df.columns = df.columns.astype(str).str.strip().str.upper()
        return df
    except Exception:
        return pd.DataFrame() # Fails safely if the sheet doesn't exist yet

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
if 'expiration_time' not in st.session_state:
    st.session_state.expiration_time = None

check_session_expiration()

if not st.session_state.logged_in:
    st.markdown('<div class="compact-alert-info">👈 <b>Mobile Users:</b> Tap the <b>></b> arrow in the top left to open the Staff Login!</div>', unsafe_allow_html=True)

# --- UI: SIDEBAR LOGIN ---
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
                    st.session_state.expiration_time = get_next_expiration()
                    st.rerun()
                else:
                    st.error("Invalid Code.")
    else:
        st.success(f"Logged in as: **{st.session_state.current_user}**")
        st.info(f"Division: {st.session_state.user_division}")
        st.caption(f"Session expires: {st.session_state.expiration_time.strftime('%b %d, %H:%M')}")
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.user_division = None
            st.rerun()

# --- UI: MAIN DASHBOARD ---
st.markdown('<h1 class="sticky-header">📅 HFDB Whereabouts Tracker</h1>', unsafe_allow_html=True)

# 1. Schedule Management
if st.session_state.logged_in:
    tab1, tab2 = st.tabs(["📝 Add Schedule", "🗑️ Manage My Entries"])
    
    with tab1:
        with st.form("schedule_form", clear_on_submit=True):
            today = datetime.now().date()
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
                        div_sheet = sh.worksheet(st.session_state.user_division)
                        row_data = [str(start_date), str(end_date), st.session_state.current_user, final_whereabouts]
                        safe_append_row(div_sheet, row_data)
                        
                        fetch_division_data.clear(st.session_state.user_division) 
                        st.markdown('<div class="compact-alert-success">✅ Schedule successfully added to the tracker!</div>', unsafe_allow_html=True)
                        time.sleep(1) 
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error saving. Does your division tab exist?")
                else:
                    st.error("Please ensure your dates and Activity Details are filled out.")

    with tab2:
        st.caption("Select an entry below to remove it from the calendar.")
        try:
            div_data = fetch_division_data(st.session_state.user_division)
            user_entries = []
            for i, row in enumerate(div_data):
                if str(row.get('Name', '')) == st.session_state.current_user:
                    user_entries.append({
                        "display": f"{row['Start Date']} to {row['End Date']} | {row['Whereabouts']}",
                        "row_index": i + 2 
                    })
            
            if user_entries:
                selected_entry_display = st.selectbox("Select Entry to Delete", [e["display"] for e in user_entries])
                
                if st.button("🗑️ Delete Selected Entry", type="primary"):
                    target_row = next(e["row_index"] for e in user_entries if e["display"] == selected_entry_display)
                    with st.spinner("Deleting..."):
                        active_sheet = sh.worksheet(st.session_state.user_division)
                        active_sheet.delete_rows(target_row)
                        fetch_division_data.clear(st.session_state.user_division)
                        st.markdown('<div class="compact-alert-success">✅ Entry removed successfully!</div>', unsafe_allow_html=True)
                        time.sleep(1)
                        st.rerun()
            else:
                st.markdown('<div class="compact-alert-info">You currently have no scheduled entries to manage.</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error("Unable to load entries for management.")

st.divider()

details_placeholder = st.empty()

# 2. Calendar View
divisions = ["ALL", "DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]
selected_div = st.radio("Filter by Division", divisions, horizontal=True)

division_colors = {
    "DIRECTOR": "hsl(350, 70%, 40%)",    
    "HSDMSD": "hsl(210, 70%, 40%)",      
    "PPPDD": "hsl(120, 60%, 35%)",       
    "FPMD": "hsl(35, 90%, 40%)",         
    "ADMIN": "hsl(280, 60%, 45%)"        
}

if selected_div == "ALL":
    st.markdown("**Color Legend:**")
    cols = st.columns(len(division_colors) + 1)
    
    # Render Division Legend
    for i, (div_name, color) in enumerate(division_colors.items()):
        cols[i].markdown(f"<div style='background-color:{color}; color:white; padding:5px; border-radius:5px; text-align:center; font-size:14px; font-weight:bold; box-shadow: 0px 2px 4px rgba(0,0,0,0.2); margin-bottom: 10px;'>{div_name}</div>", unsafe_allow_html=True)
    
    # UPGRADE: Inject the Holiday Legend marker
    cols[-1].markdown("<div style='background-color:#FF3B3B; color:white; padding:5px; border-radius:5px; text-align:center; font-size:14px; font-weight:bold; box-shadow: 0px 2px 4px rgba(0,0,0,0.2); margin-bottom: 10px;'>🎌 HOLIDAY</div>", unsafe_allow_html=True)

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

calendar_events = []
sheets_to_fetch = divisions[1:] if selected_div == "ALL" else [selected_div]

with st.spinner("Loading calendar data..."):
    # --- UPGRADE: Plot the Holidays First (With Bulletproof Date Formatting) ---
    holiday_df = fetch_holidays()
    if not holiday_df.empty and 'DATE' in holiday_df.columns:
        for _, h_row in holiday_df.iterrows():
            raw_date = str(h_row.get('DATE', '')).strip()
            h_remarks = str(h_row.get('REMARKS', '')).strip()
            
            if raw_date:
                try:
                    # Force ANY date format into the strict YYYY-MM-DD format FullCalendar demands!
                    h_date = pd.to_datetime(raw_date).strftime("%Y-%m-%d")
                except Exception:
                    h_date = raw_date # Fallback just in case
                
                # 1. The Background Tint (colors the whole square cell)
                calendar_events.append({
                    "start": h_date,
                    "display": "background",
                    "backgroundColor": "rgba(255, 59, 59, 0.15)" 
                })
                # 2. The Solid Text Block (readable banner at the top of the day)
                calendar_events.append({
                    "title": f"🎌 HOLIDAY: {h_remarks}",
                    "start": h_date,
                    "backgroundColor": "#FF3B3B", 
                    "borderColor": "#FF3B3B",
                    "textColor": "#FFFFFF",
                    "display": "block"
                })

    # --- Plot the Staff Whereabouts ---
    for div in sheets_to_fetch:
        try:
            div_data = fetch_division_data(div) 
            for row in div_data:
                try:
                    end_date_obj = datetime.strptime(str(row['End Date']), "%Y-%m-%d") + timedelta(days=1)
                    end_str = end_date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    end_str = str(row['End Date']) 
                
                raw_name = str(row['Name']).strip()
                display_name = nickname_map.get(raw_name, raw_name)
                
                if selected_div == "ALL":
                    bg_color = division_colors.get(div, "#808080")
                else:
                    bg_color = get_color_for_name(raw_name) 
                
                calendar_events.append({
                    "title": f"{display_name} - {row['Whereabouts']}",
                    "start": str(row['Start Date']),
                    "end": end_str,
                    "backgroundColor": bg_color,
                    "borderColor": bg_color,
                    "textColor": "#FFFFFF",
                    "display": "block" 
                })
        except Exception:
             pass 

calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,dayGridWeek"
    },
    "displayEventTime": False, 
    "eventDisplay": "block",   
    "height": 650
}

details_placeholder.markdown('<div class="compact-alert-info">💡 <b>Tip:</b> Click on any colored bar in the calendar to see the full details here!</div>', unsafe_allow_html=True)

if not calendar_events:
    details_placeholder.markdown(f'<div class="compact-alert-info">No whereabouts plotted yet for {selected_div}. The calendar is currently empty.</div>', unsafe_allow_html=True)

cal_result = calendar(events=calendar_events, options=calendar_options)

if cal_result and cal_result.get("callback") == "eventClick":
    clicked_event = cal_result["eventClick"]["event"]
    event_details = clicked_event.get("title", "No details provided")
    start_date_click = clicked_event.get("start", "Unknown Date")[:10] 
    
    details_placeholder.markdown(f'<div class="compact-alert-success">🔍 <b>Full Details for {start_date_click}:</b> {event_details}</div>', unsafe_allow_html=True)
