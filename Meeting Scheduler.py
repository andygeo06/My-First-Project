import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import google.auth
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread
import pandas as pd
import streamlit as st

# --- CONFIGURATION & SECRETS ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1D4ED6iOhLxRObPMOJOkMTNhNws7feeCexhMFsnDZnI0/edit?gid=1337273052#gid=1337273052"
STATIC_MEET_LINK = "https://meet.google.com/ift-tjse-knu"  # <-- Replace with your permanent/reusable Google Meet link

# 🔒 FIX THE MEETING DATE HERE (Change this whenever you have a new schedule date)
# Format: datetime.date(YYYY, MM, DD)
FIXED_BOOKING_DATE = datetime.date(2026, 10, 31)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",  # Required for open_by_url connection
    "https://www.googleapis.com/auth/calendar",
]


@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client, creds


def send_email_smtp(to_email, applicant_name, date_str, time_str, meet_link):
    sender_email = st.secrets["smtp"]["email"]
    app_password = st.secrets["smtp"]["app_password"]

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = f"Interview Confirmed: {date_str} at {time_str}"

    body = f"""
    Hi {applicant_name},

    Your meeting slot has been successfully booked!

    📅 Date: {date_str}
    ⏰ Time: {time_str}
    🔗 Google Meet Link: {meet_link}

    IMPORTANT GUIDELINES:
    - Please join the meeting strictly on time. 
    - Each session is strictly capped at 30 minutes to accommodate all applicants.
    - Late arrivals will not be given time extensions. Sessions that exceed the allotted window will be automatically closed.

    Best regards,
    Scheduling Team
    """
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False


# --- UI SETUP ---
st.title("📅 Applicant Meeting Scheduler")
st.write(
    "Select your name, verify your email, and pick an available 30-minute time slot for the scheduled date."
)

try:
    client, creds = get_gspread_client()
    # Connect directly via URL and target the "Details" tab
    spreadsheet = client.open_by_url(SPREADSHEET_URL)
    sheet = spreadsheet.worksheet("Details")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(
        f"Error connecting to Google Sheets. Please check your credentials and URL. Details: {e}"
    )
    st.stop()

# Ensure required columns exist
expected_columns = [
    "Name",
    "Email",
    "Booking Date",
    "Booking Time",
    "Meet Link",
    "Status",
]
for col in expected_columns:
    if col not in df.columns:
        df[col] = ""

# --- STEP 1: AUTHENTICATION ---
names = df["Name"].dropna().unique().tolist()
selected_name = st.selectbox("Select Your Name", ["-- Select --"] + names)

if selected_name != "-- Select --":
    # Get the registered email for this applicant (DataFrame index + 2 for header offset)
    applicant_row_idx = df[df["Name"] == selected_name].index[0] + 2
    registered_email = df.loc[df["Name"] == selected_name, "Email"].values[0]
    current_status = df.loc[df["Name"] == selected_name, "Status"].values[0]

    # Check if already booked
    if str(current_status).strip().lower() == "booked":
        st.warning(
            f"⚠️ **{selected_name}**, you have already booked a schedule!"
        )
        existing_link = df.loc[
            df["Name"] == selected_name, "Meet Link"
        ].values[0]
        st.info(f"Your Google Meet Link: {existing_link}")
        st.stop()

    # Email Verification Input
    entered_email = st.text_input(
        "Enter your registered Email Address to verify identity:"
    )

    if entered_email:
        if entered_email.strip().lower() == str(registered_email).strip().lower():
            st.success("✅ Identity verified successfully!")

            st.divider()
            
            # --- PROMINENT POLICY & TIME RESTRICTION WARNING ---
            st.warning(
                "⚠️ **IMPORTANT POLICY & TIME RESTRICTIONS**\n\n"
                "- **Operating Hours:** Interviews run strictly from **8:00 AM to 5:00 PM**.\n"
                "- **Duration:** Each slot is strictly capped at **25 minutes**.\n"
                "- **Enforcement:** Late arrivals will **not** be given time extensions. Sessions will close promptly at the end of your scheduled 25-minute block to prevent overlap with other applicants."
            )

            st.subheader("Select Your Meeting Slot")

            # Display the fixed date
            formatted_date_str = FIXED_BOOKING_DATE.strftime("%B %d, %Y")
            st.info(f"📅 **Scheduled Meeting Date:** {formatted_date_str}")

            # Generate 30-min time slots from 8:00 AM to 5:00 PM
            start_time = datetime.time(8, 0)
            end_time = datetime.time(17, 0)
            slots = []
            current_t = datetime.datetime.combine(
                datetime.date.today(), start_time
            )
            while current_t.time() < end_time:
                slot_str = current_t.strftime("%I:%M %p")
                slots.append(slot_str)
                current_t += datetime.timedelta(minutes=30)

            # Check already booked slots for this fixed date
            booked_slots_on_date = df[
                (df["Booking Date"].astype(str) == str(FIXED_BOOKING_DATE))
                & (df["Status"].astype(str).str.lower() == "booked")
            ]["Booking Time"].tolist()

            available_slots = [s for s in slots if s not in booked_slots_on_date]

            if not available_slots:
                st.error("❌ All time slots are fully booked for this date.")
            else:
                selected_slot = st.selectbox("Available Time Slots (30 mins)", available_slots)

                if st.button("Confirm and Book Schedule", type="primary"):
                    with st.spinner("Booking slot and sending confirmation..."):
                        try:
                            # 1. Create clean 30-min calendar block on primary calendar
                            calendar_service = build("calendar", "v3", credentials=creds)

                            time_obj = datetime.datetime.strptime(selected_slot, "%I:%M %p").time()
                            start_datetime = datetime.datetime.combine(FIXED_BOOKING_DATE, time_obj)
                            end_datetime = start_datetime + datetime.timedelta(minutes=30)

                            event_body = {
                                "summary": f"Meeting: {selected_name}",
                                "description": f"Applicant: {selected_name}\nEmail: {registered_email}\nGoogle Meet Link: {STATIC_MEET_LINK}",
                                "start": {"dateTime": start_datetime.isoformat(), "timeZone": "Asia/Manila"},
                                "end": {"dateTime": end_datetime.isoformat(), "timeZone": "Asia/Manila"},
                                "location": STATIC_MEET_LINK
                            }
                            calendar_service.events().insert(calendarId="primary", body=event_body).execute()

                            # 2. Update Google Sheet
                            sheet.update_cell(applicant_row_idx, 3, str(FIXED_BOOKING_DATE))
                            sheet.update_cell(applicant_row_idx, 4, selected_slot)
                            sheet.update_cell(applicant_row_idx, 5, STATIC_MEET_LINK)
                            sheet.update_cell(applicant_row_idx, 6, "Booked")

                            # 3. Send Email via SMTP
                            email_sent = send_email_smtp(registered_email, selected_name, str(FIXED_BOOKING_DATE), selected_slot, STATIC_MEET_LINK)

                            st.success("🎉 Booking confirmed successfully!")
                            st.balloons()
                            st.markdown(f"**Google Meet Link:** [{STATIC_MEET_LINK}]({STATIC_MEET_LINK})")
                            if email_sent:
                                st.info(f"📧 Confirmation email successfully sent to {registered_email}!")

                        except Exception as e:
                            st.error(f"An error occurred during booking: {e}")

        else:
            st.error("❌ Email does not match our records for this name. Please try again.")
