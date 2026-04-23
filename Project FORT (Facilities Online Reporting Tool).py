import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
# We use the connection for READING, but a different trick for WRITING
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIG & CONNECTION ---
st.set_page_config(page_title="Project FORT", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"

# Initialize Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA FUNCTIONS ---

def get_all_profiles():
    """Reads profiles using the standard connection."""
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl="0")
    except:
        return pd.DataFrame(columns=["User_ID", "Hospital_Name", "Encoder_Name", "Position", "Year", "Created_At"])

def save_new_profile(user_id, h_name, u_name, pos):
    """
    WORKAROUND: Since .update() and .create() are failing, 
    we use the .update() via the underlying connection more simply.
    """
    existing = get_all_profiles()
    
    new_row = pd.DataFrame([{
        "User_ID": str(user_id),
        "Hospital_Name": str(h_name),
        "Encoder_Name": str(u_name),
        "Position": str(pos),
        "Year": 2026,
        "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    updated_df = pd.concat([existing, new_row], ignore_index=True)
    
    # Attempting a cleaner update call
    try:
        # We pass the data as a dataframe to overwrite the worksheet
        conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=updated_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Critical Sync Error: {e}")
        st.info("Please ensure the Google Sheet has a tab named 'User_Profiles' and is shared with your service account.")
        return False

# --- 3. UI: LOGIN SCREEN ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.divider()

    if "auth_mode" not in st.session_state:
        st.subheader("Please choose an option to begin:")
        c1, c2 = st.columns(2)
        if c1.button("🆕\n\nNEW USER\n\nCreate a Profile", use_container_width=True):
            st.session_state.auth_mode = "new"
            st.rerun()
        if c2.button("🔑\n\nEXISTING USER\n\nContinue Work", use_container_width=True, type="primary"):
            st.session_state.auth_mode = "existing"
            st.rerun()
    else:
        if st.button("⬅️ Back to Selection"):
            del st.session_state.auth_mode
            st.rerun()

        if st.session_state.auth_mode == "new":
            h_name = st.text_input("Full Hospital Name:")
            u_name = st.text_input("Name of Encoder:")
            pos = st.text_input("Official Position:")
            
            if st.button("🚀 Register & Generate Code", type="primary"):
                if not h_name or not u_name or not pos:
                    st.error("Fields cannot be blank.")
                else:
                    new_id = f"HFDB-2026-{uuid.uuid4().hex[:8].upper()}"
                    success = save_new_profile(new_id, h_name, u_name, pos)
                    
                    if success:
                        st.success("✅ Registered Successfully!")
                        st.code(new_id)
                        st.warning("SAVE THIS CODE.")
                        if st.button("Proceed to Dashboard"):
                            st.session_state.user_id = new_id
                            st.session_state.user_info = {"hosp": h_name, "user": u_name}
                            st.rerun()

        elif st.session_state.auth_mode == "existing":
            input_id = st.text_input("Enter User Identification Code:")
            if st.button("Verify & Enter", type="primary"):
                profiles = get_all_profiles()
                if input_id in profiles["User_ID"].values():
                    row = profiles[profiles["User_ID"] == input_id].iloc[0]
                    st.session_state.user_id = input_id
                    st.session_state.user_info = {"hosp": row["Hospital_Name"], "user": row["Encoder_Name"]}
                    st.rerun()
                else:
                    st.error("Code not found.")

# --- 4. UI: DASHBOARD ---

def dashboard():
    st.title("🏥 Module Selection")
    st.write(f"Logged in: {st.session_state.user_info['hosp']}")
    
    cols = st.columns(3)
    if cols[0].button("📊 Hospital Scorecard", use_container_width=True): st.toast("Coming Soon")
    if cols[1].button("💰 Financial Data", use_container_width=True): st.toast("Coming Soon")
    if cols[2].button("🏥 Hospital MOOE", use_container_width=True): st.toast("Coming Soon")
    
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# --- ROUTER ---
if "user_id" not in st.session_state:
    login_screen()
else:
    dashboard()

# --- CSS ---
st.markdown("<style>div.stButton > button {height: 120px; border-radius: 12px; font-weight: bold; font-size: 18px;} button[kind='primary'] {background-color: #2e7d32 !important; color: white !important;}</style>", unsafe_allow_html=True)
