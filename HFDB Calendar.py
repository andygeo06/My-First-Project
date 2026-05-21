import streamlit as st
import gspread
import pandas as pd
import random
import string
import smtplib
from email.mime.text import MIMEText
from streamlit_calendar import calendar

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="HFDB Whereabouts", layout="wide")

# Connect to Google Sheets (Assuming standard service account JSON)
gc = gspread.service_account(filename="credentials.json")
sh = gc.open("HFDB Whereabouts")

# --- HELPER FUNCTIONS ---
def generate_ucode():
    prefix = "HFDB-"
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return prefix + suffix

def send_email(to_email, name, code):
    # Standard smtplib setup for sending the login code
    sender_email = "your_app_email@gmail.com"
    sender_password = "your_app_password" # Use App Passwords if using Gmail
    
    msg = MIMEText(f"Hello {name},\n\Your login code is: {code}")
    msg['Subject'] = 'HFDB Whereabouts Login Code'
    msg['From'] = sender_email
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'user_division' not in st.session_state:
    st.session_state.user_division = None

# --- UI: SIDEBAR LOGIN ---
with st.sidebar:
    st.header("🔑 Staff Login")
    
    # Fetch Staff Data
    staff_sheet = sh.worksheet("STAFF")
    staff_df = pd.DataFrame(staff_sheet.get_all_records())
    
    if not st.session_state.logged_in:
        selected_name = st.selectbox("Select Name", staff_df['NAME'].tolist())
        
        if st.button("Send Login Code"):
            user_row = staff_df[staff_df['NAME'] == selected_name].index[0]
            user_email = staff_df.at[user_row, 'EMAIL']
            
            new_code = generate_ucode()
            # Update UCODE in the actual Google Sheet (Row is index + 2 because of header)
            staff_sheet.update_cell(user_row + 2, 1, new_code) 
            
            send_email(user_email, selected_name, new_code)
            st.success(f"Code sent to your email!")
            
        entered_code = st.text_input("Enter Code", type="password")
        if st.button("Login"):
            # Verify code against the sheet
            fresh_staff_df = pd.DataFrame(staff_sheet.get_all_records())
            user_data = fresh_staff_df[fresh_staff_df['NAME'] == selected_name].iloc[0]
            
            if entered_code == user_data['UCODE']:
                st.session_state.logged_in = True
                st.session_state.current_user = selected_name
                st.session_state.user_division = user_data['DIVISION']
                st.rerun()
            else:
                st.error("Invalid Code.")
    else:
        st.success(f"Logged in as {st.session_state.current_user}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.rerun()

# --- UI: MAIN DASHBOARD ---
st.title("📅 HFDB Whereabouts Tracker")

# 1. Plotting Form (Only visible if logged in)
if st.session_state.logged_in:
    with st.expander("📝 Plot Your Schedule", expanded=True):
        with st.form("schedule_form"):
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Start Date")
            end_date = col2.date_input("End Date")
            whereabouts = st.text_input("Whereabouts / Activity Details")
            
            if st.form_submit_button("Save Schedule"):
                # Append to the user's division tab
                div_sheet = sh.worksheet(st.session_state.user_division)
                div_sheet.append_row([str(start_date), str(end_date), st.session_state.current_user, whereabouts])
                st.success("Schedule Updated!")

# 2. The Calendar View
st.divider()

# Division Filter
divisions = ["ALL", "DIRECTOR", "HSDMSD", "PPPDD", "FPMD", "ADMIN"]
selected_div = st.radio("Filter by Division", divisions, horizontal=True)

# Compile events from sheets into the format streamlit-calendar needs
calendar_events = []
color_map = {"PPPDD Staff 1": "#FF9900", "PPPDD Staff 2": "#FF00FF"} # Define your colors here

# (Logic here would loop through your chosen division sheets, fetch rows, and format them)
# Example of the dictionary format required by streamlit-calendar:
"""
for row in division_data:
    calendar_events.append({
        "title": f"{row['Name']} - {row['Whereabouts']}",
        "start": row['Start Date'],
        "end": row['End Date'],
        "backgroundColor": color_map.get(row['Name'], "#0000FF") # Fallback color
    })
"""

# Configure and render the calendar
calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek"
    }
}

# calendar(events=calendar_events, options=calendar_options)
st.info("Calendar will render here once data is pulled from the division tabs.")
