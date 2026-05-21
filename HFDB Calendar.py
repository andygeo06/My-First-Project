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

st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .sticky-header {
            position: sticky;
            top: 2.8rem; 
            background-color: var(--background-color); 
            z-index: 999;
            padding: 10px 0px 10px 0px;
            margin-top: -10px;
            margin-bottom: 15px;
            border-bottom: 2px solid var(--secondary-background-color);
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
    # UPGRADE: 3D Color Hashing!
    hash_object = hashlib.md5(str(name).strip().encode())
    hash_int = int(hash_object.hexdigest(), 16)
    
    # 1. Hue: 0 to 360 degrees (The base color)
    hue = hash_int % 360
    
    # 2. Saturation: 50% to 95% (Keeps it vibrant, never gray)
    saturation = 50 + ((hash_int // 360) % 45)
    
    # 3. Lightness: 35% to 65% (Keeps text readable, never too dark or too pale)
    lightness = 35 + ((hash_int // 36000) % 30)
    
    return f"hsl({hue}, {saturation}%, {lightness}%)"

def safe_append_row(sheet, row_data, max_retries=5):
    for attempt in range(max_retries):
        try:
            sheet.append_row(row_data)
            return True
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
            else:
                raise e 

# --- CACHING FUNCTIONS ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_staff_data():
    staff_sheet = sh.worksheet("STAFF")
    df = pd.DataFrame(staff_sheet.get_all_records())
    df.columns = df.columns.astype(str).str.strip().str.upper()
    return df

@st.cache_data(ttl=60, show_spinner=False)
def fetch_division_data(div_name):
    return sh.worksheet(div_name).get_all_records()

@st.cache_data(ttl=60, show_spinner=False)
def fetch_presets():
    try:
        preset_sheet = sh.worksheet("PRESET")
        presets = preset_sheet.col_values(1)
        # Skip header if it exists
        if presets and presets[0].strip().upper() in ["PRESET", "PRESETS", "WHEREABOUTS", "ACTIVITY"]:
            presets = presets[1:]
        return [p for p in presets if p.strip()]
    except Exception:
        return []

# --- INITIALIZATION ---
try:
    sh = init_google_sheets()
except Exception as e:
    st.error(f"Failed to connect to Google Sheets. Please double-check your st.secrets configuration. Error details: {e}")
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

# --- UI: SIDEBAR LOGIN ---
with st.sidebar:
    st.header("🔑 Staff Login")
    
    try:
        staff_df = fetch_staff_data()
        staff_sheet = sh.worksheet("STAFF") 
    except Exception as e:
        st.error(f"Could not connect to the 'STAFF' tab. Error: {e}")
        st.stop()
        
    if 'NAME' not in staff_df.columns:
        st.error(f"Column 'NAME' is missing! Found: {list(staff_df.columns)}")
        st.stop()
    elif staff_df.empty:
        st.warning("The STAFF tab was found, but it looks like there are no data rows underneath the headers.")
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
                        last_error = ""
                        
                        for attempt in range(3):
                            try:
                                staff_sheet.update_cell(exact_row, 1, new_code)
                                time.sleep(2) 
                                verify_val = staff_sheet.cell(exact_row, 1).value
                                if str(verify_val).strip() == new_code:
                                    write_success = True
                                    break 
                                else:
                                    last_error = f"Verification mismatch"
                            except Exception as e:
                                last_error = str(e)
                                time.sleep(2) 
                                
                        if not write_success:
                            st.error(f"Google API blocked the save. Reason: {last_error}")
                            st.stop()
                        
                        try:
                            send_email(user_email, selected_name, new_code)
                            st.cache_data.clear() 
                            st.success(f"Code secured and sent to {user_email}!")
                        except Exception as e:
                            st.error("Code saved, but email failed to send.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")
        
        st.divider()
        entered_code = st.text_input("Enter Code", type="password")
        
        if st.button("Login"):
            with st.spinner("Verifying..."):
                fresh_staff_df = pd.DataFrame(staff_sheet.get_all_records())
                fresh_staff_df.columns = fresh_staff_df.columns.astype(str).str.strip().str.upper()
                entered_clean = entered_code.strip()
                
                # BUG SQUASHED: We now search the entire sheet for the code!
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

# 1. Schedule Entry Form
if st.session_state.logged_in:
    with st.expander("📝 Plot Your Schedule", expanded=True):
        with st.form("schedule_form", clear_on_submit=True):
            today = datetime.now().date()
            selected_dates = st.date_input("Select Date Range", value=(today, today))
            
            # UPGRADE: PRESET LOGIC
            preset_options = fetch_presets()
            preset_options.insert(0, "Custom Input...")
            selected_preset = st.selectbox("Whereabouts / Activity", preset_options)
            
            if selected_preset == "Custom Input...":
                whereabouts = st.text_input("Enter Custom Details", placeholder="e.g., Regional Monitoring")
            else:
                whereabouts = selected_preset
            
            submitted = st.form_submit_button("Save Schedule")
            if submitted:
                if len(selected_dates) == 2:
                    start_date, end_date = selected_dates[0], selected_dates[1]
                elif len(selected_dates) == 1:
                    start_date, end_date = selected_dates[0], selected_dates[0]
                else:
                    start_date, end_date = None, None
                
                if start_date and end_date and whereabouts:
                    try:
                        div_sheet = sh.worksheet(st.session_state.user_division)
                        row_data = [str(start_date), str(end_date), st.session_state.current_user, whereabouts]
                        safe_append_row(div_sheet, row_data)
                        
                        st.cache_data.clear() 
                        st.success("Schedule successfully added to the tracker!")
                        
                        time.sleep(1) 
                        st.rerun() 
                        
                    except Exception as e:
                        st.error(f"Error saving to the {st.session_state.user_division} tab. Does it exist?")
                else:
                    st.error("Please ensure your dates and Activity Details are filled out.")

# 2. Calendar View
divisions = ["ALL", "DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]
selected_div = st.radio("Filter by Division", divisions, horizontal=True)

calendar_events = []
sheets_to_fetch = divisions[1:] if selected_div == "ALL" else [selected_div]

with st.spinner("Loading calendar data..."):
    for div in sheets_to_fetch:
        try:
            div_data = fetch_division_data(div) 
            for row in div_data:
                try:
                    end_date_obj = datetime.strptime(str(row['End Date']), "%Y-%m-%d") + timedelta(days=1)
                    end_str = end_date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    end_str = str(row['End Date']) 
                
                calendar_events.append({
                    "title": f"{row['Name']} - {row['Whereabouts']}",
                    "start": str(row['Start Date']),
                    "end": end_str,
                    "backgroundColor": get_color_for_name(row['Name']),
                    "borderColor": get_color_for_name(row['Name'])
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

if not calendar_events:
    st.info(f"No whereabouts plotted yet for {selected_div}. The calendar is currently empty.")

# Render Calendar
calendar(events=calendar_events, options=calendar_options)
