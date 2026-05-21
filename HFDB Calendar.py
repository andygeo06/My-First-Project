import streamlit as st
import gspread
import pandas as pd
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_calendar import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="HFDB Whereabouts", page_icon="📅", layout="wide")

# --- HELPER FUNCTIONS ---
def get_next_expiration():
    """Calculates the next Monday at 6:00 AM for session expiration."""
    now = datetime.now()
    if now.weekday() == 0 and now.hour < 6:
        return now.replace(hour=6, minute=0, second=0, microsecond=0)
    
    days_ahead = 0 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (now + timedelta(days_ahead)).replace(hour=6, minute=0, second=0, microsecond=0)

def check_session_expiration():
    """Clears session state if the current time is past the expiration timestamp."""
    if st.session_state.get('logged_in'):
        if datetime.now() > st.session_state.expiration_time:
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.user_division = None
            st.warning("Session expired. Please log in again for the new week.")

def generate_ucode():
    """Generates a random 10-character alphanumeric login code."""
    prefix = "HFDB-"
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return prefix + suffix

def send_email(to_email, name, code):
    """Sends the generated code to the user's email via standard SMTP."""
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
    """
    Initializes Google Sheets connection using Streamlit secrets.
    This replaces the old gspread.service_account(filename="credentials.json") method.
    """
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Pull the dictionary directly from the secrets TOML
    creds_dict = dict(st.secrets["gcp_service_account"])
    # Authenticate using the dictionary data
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
    client = gspread.authorize(creds)
    # Open the sheet via URL
    return client.open_by_url(st.secrets["sheets"]["whereabouts_url"])

def get_color_for_name(name):
    """Assigns consistent block colors for calendar events based on staff names."""
    colors = ["#FF5733", "#33FF57", "#3357FF", "#FF33A8", "#A833FF", "#33FFF5", "#FF8F33", "#E3FF33", "#FF4500", "#2E8B57"]
    return colors[hash(name) % len(colors)]


# --- INITIALIZATION ---
try:
    sh = init_google_sheets()
except Exception as e:
    st.error(f"Failed to connect to Google Sheets. Please double-check your st.secrets configuration. Error details: {e}")
    st.stop()

# Set up Session States
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
        
        # --- THE BULLETPROOF FIX ---
        # This forces all headers to be uppercase and removes any accidental spaces
        staff_df.columns = staff_df.columns.str.strip().str.upper()
        
    except Exception as e:
        st.error("Could not find or read the 'STAFF' tab in your Google Sheet.")
        st.stop()
    
    if not st.session_state.logged_in:
        selected_name = st.selectbox("Select Name", staff_df['NAME'].tolist())
        
        if st.button("Send Login Code"):
            # Find the user's data row
            user_row = staff_df[staff_df['NAME'] == selected_name].index[0]
            user_email = staff_df.at[user_row, 'EMAIL']
            
            new_code = generate_ucode()
            # Update UCODE in sheet (Row + 2 to account for pandas 0-index and sheet header)
            staff_sheet.update_cell(int(user_row) + 2, 1, new_code) 
            
            try:
                with st.spinner("Sending code via email..."):
                    send_email(user_email, selected_name, new_code)
                st.success(f"Code sent to {user_email}!")
            except Exception as e:
                st.error("Failed to send email. Check your email credentials in st.secrets.")
            
        entered_code = st.text_input("Enter Code", type="password")
        if st.button("Login"):
            # Pull a fresh copy of the sheet to ensure we get the newly written code
            fresh_staff_df = pd.DataFrame(staff_sheet.get_all_records())
            user_data = fresh_staff_df[fresh_staff_df['NAME'] == selected_name].iloc[0]
            
            if entered_code == str(user_data['UCODE']) and entered_code != "":
                st.session_state.logged_in = True
                st.session_state.current_user = selected_name
                st.session_state.user_division = user_data['DIVISION']
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
st.title("📅 HFDB Whereabouts Tracker")

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
                        # Format: Start Date, End Date, Name, Whereabouts
                        div_sheet.append_row([str(start_date), str(end_date), st.session_state.current_user, whereabouts])
                        st.success("Schedule successfully added to the tracker!")
                    except Exception as e:
                        st.error(f"Error saving to the {st.session_state.user_division} tab. Does it exist?")
                else:
                    st.error("Please ensure the End Date is after the Start Date and the Details are filled out.")

st.divider()

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
                # FullCalendar needs the end date to be exclusive to cover the whole day visually
                # We parse the date, add 1 day, and format it back to string
                try:
                    end_date_obj = datetime.strptime(str(row['End Date']), "%Y-%m-%d") + timedelta(days=1)
                    end_str = end_date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    # Fallback in case of weird date formatting in the sheet
                    end_str = str(row['End Date']) 
                
                calendar_events.append({
                    "title": f"{row['Name']} - {row['Whereabouts']}",
                    "start": str(row['Start Date']),
                    "end": end_str,
                    "backgroundColor": get_color_for_name(row['Name']),
                    "borderColor": get_color_for_name(row['Name'])
                })
        except Exception:
             pass # Skip if tab is empty or missing headers

# Configure Calendar Appearance
calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,dayGridWeek"
    },
    "displayEventTime": False, # Hide 12:00a text on bars
    "eventDisplay": "block",   # Forces the solid color bar style
    "height": 650
}

# Render Calendar
if calendar_events:
    calendar(events=calendar_events, options=calendar_options)
else:
    st.info(f"No whereabouts plotted yet for {selected_div}.")
