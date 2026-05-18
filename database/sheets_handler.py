import streamlit as st
import pandas as pd
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# CORE CONNECTION & UTILS
# -----------------------------------------------------------------------------
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def sanitize_and_pad_dataframe(df):
    expected_cols = ["Division", "Nickname", "Name of Staff", "Staff Email", "Division Email", "Code", "Category"]
    current_col_count = len(df.columns)
    if current_col_count < len(expected_cols):
        for i in range(current_col_count, len(expected_cols)):
            df[f"padded_col_{i}"] = ""
    df = df.iloc[:, :7]
    df.columns = expected_cols
    df["Code"] = df["Code"].astype(object)
    df["Category"] = df["Category"].astype(object)
    return df

# -----------------------------------------------------------------------------
# AUTOMATED EMAIL ENGINE
# -----------------------------------------------------------------------------
def send_credential_email(to_email, staff_name, code, is_recovery=False):
    """Sends account codes via secure SMTP email connection."""
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        port = int(st.secrets["email"]["port"])
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = str(to_email).strip()
        
        if is_recovery:
            msg['Subject'] = "🔐 HFDB Tracking System - Account Code Recovery"
            body = f"Hello {staff_name},\n\nYou requested your existing access credentials for the HFDB Document Tracking System.\n\nYour Access Code is: {code}\n\nUse this code to log in to your dashboard. Please keep it secure."
        else:
            msg['Subject'] = "🎉 HFDB Tracking System - New Account Registration"
            body = f"Hello {staff_name},\n\nWelcome to the HFDB Document Tracking System! Your account has been initialized.\n\nYour Access Code is: {code}\n\nPlease keep this code secure."
            
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"📧 Email delivery system failure: {e}")
        return False

# -----------------------------------------------------------------------------
# DATA READ OPERATIONS
# -----------------------------------------------------------------------------
@st.cache_data(ttl="10m") 
def get_staff_data():
    conn = get_connection()
    try:
        df = conn.read(worksheet="STAFF", ttl="10m")
        df = sanitize_and_pad_dataframe(df)
        df = df.dropna(subset=["Name of Staff"])
        return df
    except Exception as e:
        st.error(f"Failed to load STAFF sheet: {e}")
        return pd.DataFrame(columns=["Division", "Nickname", "Name of Staff", "Staff Email", "Division Email", "Code", "Category"])

def get_all_staff_names():
    """Returns a clean list of all staff names for the lookup menu."""
    df = get_staff_data()
    return df["Name of Staff"].tolist()

# -----------------------------------------------------------------------------
# AUTHENTICATION & PROCESSING INTERCEPT
# -----------------------------------------------------------------------------
def authenticate_user(login_code):
    df = get_staff_data()
    df["Code"] = df["Code"].astype(str).str.strip()
    match = df[df["Code"] == str(login_code).strip()]
    if not match.empty:
        user_info = match.iloc[0]
        return {
            "division": user_info["Division"], "nickname": user_info["Nickname"],
            "name": user_info["Name of Staff"], "staff_email": user_info["Staff Email"],
            "division_email": user_info["Division Email"], "code": user_info["Code"],
            "category": user_info["Category"]
        }
    return None

def process_registration_or_recovery(name_of_staff):
    """Intercepts request to determine if user needs a new code or a recovery email."""
    conn = get_connection()
    df = conn.read(worksheet="STAFF", ttl=0)
    df = sanitize_and_pad_dataframe(df)
    
    # Locate targeted row
    row_match = df[df["Name of Staff"] == name_of_staff]
    if row_match.empty:
        return "ERROR", "Staff member not found in baseline registry."
        
    user_row = row_match.iloc[0]
    existing_code = str(user_row["Code"]).strip()
    email_target = user_row["Staff Email"]
    
    if not email_target or pd.isna(email_target) or str(email_target).lower() == "nan":
        return "NO_EMAIL", f"No valid email found on sheet for {name_of_staff}. Contact your Admin."

    # CASE A: USER ALREADY HAS A VALID CODE -> TRIGGER RECOVERY EMAIL ONLY
    if existing_code and existing_code != "nan" and existing_code != "":
        email_success = send_credential_email(email_target, name_of_staff, existing_code, is_recovery=True)
        if email_success:
            return "RECOVERED", email_target
        return "EMAIL_FAIL", "Database found your code, but SMTP server failed to send email."
        
    # CASE B: BRAND NEW USER -> GENERATE, SAVE, AND EMAIL
    new_code = f"HFDB-{''.join(random.choices(string.ascii_letters + string.digits, k=12))}"
    df.loc[df["Name of Staff"] == name_of_staff, "Code"] = new_code
    
    try:
        conn.update(worksheet="STAFF", data=df)
        st.cache_data.clear()
        send_credential_email(email_target, name_of_staff, new_code, is_recovery=False)
        return "CREATED", new_code
    except Exception as e:
        return "WRITE_FAIL", str(e)

# -----------------------------------------------------------------------------
# CONFERENCE ROOM MODULE BACKEND OPERATIONS
# -----------------------------------------------------------------------------
@st.cache_data(ttl="1m")
def get_conference_data():
    conn = get_connection()
    try:
        df = conn.read(worksheet="CONFERENCE ROOM", ttl="1m")
        # Clean out completely empty Google Sheet rows
        df = df.dropna(how="all")
        expected = ["Date", "Room", "Activity Name", "Time Slot", "Requested By", "Division", "Status"]
        if df.empty: return pd.DataFrame(columns=expected)
        
        if len(df.columns) < len(expected):
            for i in range(len(df.columns), len(expected)): df[f"col_{i}"] = ""
        df = df.iloc[:, :7]
        df.columns = expected
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Room", "Activity Name", "Time Slot", "Requested By", "Division", "Status"])

def add_conference_booking(date, room, activity, time_slot, requested_by, division):
    conn = get_connection()
    try:
        df = conn.read(worksheet="CONFERENCE ROOM", ttl=0)
        df = df.dropna(how="all") # Prevent appending below 1000 empty rows
        expected = ["Date", "Room", "Activity Name", "Time Slot", "Requested By", "Division", "Status"]
        if not df.empty: df.columns = expected[:len(df.columns)]
        
        new_row = pd.DataFrame([{
            "Date": str(date), "Room": str(room), "Activity Name": str(activity),
            "Time Slot": str(time_slot), "Requested By": str(requested_by),
            "Division": str(division), "Status": "Pending"
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="CONFERENCE ROOM", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Booking registration error: {e}")
        return False

def confirm_conference_booking(activity_name, date_str):
    """Promotes reservation by exact Value Match instead of Row Index."""
    conn = get_connection()
    try:
        df = conn.read(worksheet="CONFERENCE ROOM", ttl=0)
        
        # Ensure we have at least 7 columns to prevent out-of-bounds errors
        if len(df.columns) < 7:
            for i in range(len(df.columns), 7): df[f"col_{i}"] = ""
            
        # Find the specific row by matching the Activity Name and Date
        mask = (df.iloc[:, 2].astype(str).str.strip() == str(activity_name).strip()) & \
               (df.iloc[:, 0].astype(str).str.strip() == str(date_str).strip())
        
        if mask.any():
            match_idx = df[mask].index[0] # Get the true Google Sheets row number
            df.iloc[match_idx, 6] = "Confirmed" # Column 7 (Index 6) is Status
            conn.update(worksheet="CONFERENCE ROOM", data=df)
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Approval transmission error: {e}")
        return False
