import streamlit as st
import gspread
import pandas as pd
import random
import string
import smtplib
import time
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_calendar import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="HFDB Whereabouts", page_icon="📅", layout="wide")

# --- CUSTOM CSS FOR PADDING AND STICKY HEADER ---
st.markdown("""
    <style>
        /* 1. Reduce overall page padding to maximize screen space */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* 2. Create the sticky header class */
        .sticky-header {
            position: sticky;
            top: 2.8rem; /* Sits just below the default Streamlit top bar */
            background-color: var(--background-color); /* Adapts to light/dark mode */
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
    colors = ["#FF5733", "#33FF57", "#3357FF", "#FF33A8", "#A833FF", "#33FFF5", "#FF8F33", "#E3FF33", "#FF4500", "#2E8B57"]
    return colors[hash(name) % len(colors)]

# --- ANTI-COLLISION FUNCTION ---
def safe_append_row(sheet, row_data, max_retries=5):
    """Appends data with Exponential Backoff to prevent Google 429 Rate Limits."""
    for attempt in range(max_retries):
        try:
            sheet.append_row(row_data)
            return True
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt < max_retries - 1:
                # Sleep for an exponentially increasing time + random jitter
                time.sleep((2 ** attempt) + random.uniform(0, 1))
            else:
                raise e # If it's not a rate limit, or we ran out of retries, crash gracefully.


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
        staff_sheet = sh.worksheet("STAFF")
        staff_df = pd.DataFrame(staff_sheet.get_all_records())
        staff_df.columns = staff_df.columns.astype(str).str.strip().str.upper()
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
        selected_name = st.selectbox("Select Name", staff_df['NAME'].tolist())
        
        if st.button("Send Login Code"):
            user_row = staff_df[staff_df['NAME'] == selected_name].index[0]
            
            if 'EMAIL' not in staff_df.columns:
                st.error(f"Column 'EMAIL' is missing! Found: {list(staff_df.columns)}")
                st.stop()
                
            user_email = staff_df.at[user_row, 'EMAIL']
            new_code = generate_ucode()
            
            # Using safe retry for the code update as well
            for attempt in range(3):
                try:
                    staff_sheet.update_cell(int(user_row) + 2, 1, new_code)
                    break
                except gspread.exceptions.APIError:
                    time.sleep(1)
            
            try:
                with st.spinner("Sending code via email..."):
                    send_email(user_email, selected_name, new_code)
                st.success(f"Code sent to {user_email}!")
            except Exception as e:
                st.error("Failed to send email. Check your email credentials in st.secrets.")
            
        entered_code = st.text_input("Enter Code", type="password")
        if st.button("Login"):
            fresh_staff_df = pd.DataFrame(staff_sheet.get_all_records())
            fresh_staff_df.columns = fresh_staff_df.columns.astype(str).str.strip().str.upper()
            
            user_data = fresh_staff_df[fresh_staff_df['NAME'] == selected_name].iloc[0]
            stored_code = str(user_data.get('UCODE', ''))
            
            if entered_code == stored_code and entered_code != "":
                st.session_state.logged_in = True
                st.session_state.current_user = selected_name
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
# The sticky header replacing standard st.title()
st.markdown('<h1 class="sticky-header">📅 HFDB Whereabouts Tracker</h1>', unsafe_allow_html=True)

# 1. Schedule Entry Form
if st.session_state.logged_in:
    with st.expander("📝 Plot Your Schedule", expanded=True):
        with st.form("schedule_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Start Date")
            end_date = col2.date_input("End Date")
            whereabouts = st.text_input("Whereabouts / Activity Details", placeholder="e.g., Regional Monitoring, Leave, WFH")
            
            submitted = st.form_submit_button("Save Schedule")
            if submitted:
                if start_date <= end_date and whereabouts:
                    try:
                        div_sheet = sh.worksheet(st.session_state.user_division)
                        row_data = [str(start_date), str(end_date), st.session_state.current_user, whereabouts]
                        
                        # Implementing the anti-collision function here
                        safe_append_row(div_sheet, row_data)
                        
                        st.success("Schedule successfully added to the tracker!")
                    except Exception as e:
                        st.error(f"Error saving to the {st.session_state.user_division} tab. Does it exist?")
                else:
                    st.error("Please ensure the End Date is after the Start Date and the Details are filled out.")


# 2. Calendar View
divisions = ["ALL", "DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]
selected_div = st.radio("Filter by Division", divisions, horizontal=True)

# Fetch Data for Calendar
calendar_events = []
sheets_to_fetch = divisions[1:] if selected_div == "ALL" else [selected_div]

with st.spinner("Loading calendar data..."):
    for div in sheets_to_fetch:
        try:
            div_data = sh.worksheet(div).get_all_records()
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

# Configure Calendar Appearance
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

# Render Calendar
if not calendar_events:
    st.info(f"No whereabouts plotted yet for {selected_div}. The calendar is currently empty.")

calendar(events=calendar_events, options=calendar_options)
