import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIG & CONNECTION ---
st.set_page_config(page_title="Project FORT", layout="wide")

# The URL of your master sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"

# Initialize Connection using Service Account (defined in secrets.toml)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA FUNCTIONS ---

def get_all_profiles():
    """Reads profiles. Service account must have access to the sheet."""
    try:
        # We use the connection to read the specific worksheet
        return conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
    except Exception as e:
        st.error(f"Read Error: {e}")
        return pd.DataFrame(columns=["User_ID", "Hospital_Name", "Encoder_Name", "Position", "Year", "Created_At"])

def save_new_profile(user_id, h_name, u_name, pos):
    """Writes the updated dataframe back to the Google Sheet."""
    try:
        # 1. Get existing data
        existing = get_all_profiles()
        
        # 2. Prepare new row
        new_row = pd.DataFrame([{
            "User_ID": str(user_id),
            "Hospital_Name": str(h_name),
            "Encoder_Name": str(u_name),
            "Position": str(pos),
            "Year": 2026,
            "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        
        # 3. Combine
        updated_df = pd.concat([existing, new_row], ignore_index=True)
        
        # 4. Push update using the authenticated connection
        conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=updated_df)
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Critical Sync Error: {e}")
        st.info("Check: Is the Service Account email added as an 'Editor' on the Google Sheet?")
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
                    if save_new_profile(new_id, h_name, u_name, pos):
                        st.success("✅ Profile Registered!")
                        st.code(new_id)
                        st.warning("⚠️ SAVE THIS CODE. You need it to log back in.")
                        if st.button("Enter Dashboard"):
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
                    st.error("Code not found. Please check or register as new.")

# --- 4. UI: DASHBOARD ---

def dashboard():
    st.title("🏥 Module Selection")
    st.info(f"Facility: **{st.session_state.user_info['hosp']}** | User: **{st.session_state.user_info['user']}**")
    
    cols = st.columns(3)
    if cols[0].button("📊 Hospital Scorecard", use_container_width=True): st.toast("Mod1 Loading...")
    if cols[1].button("💰 Financial Data", use_container_width=True): st.toast("Mod2 Loading...")
    if cols[2].button("🏥 Hospital MOOE", use_container_width=True): st.toast("Mod3 Loading...")
    
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
