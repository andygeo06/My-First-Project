import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. INITIAL CONFIGURATION ---
st.set_page_config(page_title="HFDB Online Data Submission Portal", layout="wide")

# The URL of your master sheet for explicit connection
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"

# Initialize Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CORE DATABASE FUNCTIONS ---

def get_all_profiles():
    """Retrieves the list of registered users from the Google Sheet."""
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl="0")
    except Exception:
        # Returns an empty DataFrame with correct columns if sheet is empty/missing
        return pd.DataFrame(columns=["User_ID", "Hospital_Name", "Encoder_Name", "Position", "Year", "Created_At"])

def save_new_profile(user_id, h_name, u_name, pos):
    """Appends a new user profile to the master list."""
    existing_profiles = get_all_profiles()
    
    new_row = pd.DataFrame([{
        "User_ID": user_id,
        "Hospital_Name": h_name,
        "Encoder_Name": u_name,
        "Position": pos,
        "Year": 2026,
        "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    # Combine and update
    updated_df = pd.concat([existing_profiles, new_row], ignore_index=True)
    conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=updated_df)
    st.cache_data.clear()

# --- 3. UI: LOGIN & REGISTRATION ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.markdown("### National Health Facility Data Entry (2026)")
    st.divider()

    # STEP 1: MODE SELECTION
    if "auth_mode" not in st.session_state:
        st.subheader("Please choose an option to begin:")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🆕\n\nNEW USER\n\nCreate a Profile", use_container_width=True):
                st.session_state.auth_mode = "new"
                st.rerun()
                
        with col2:
            if st.button("🔑\n\nEXISTING USER\n\nContinue Work", use_container_width=True, type="primary"):
                st.session_state.auth_mode = "existing"
                st.rerun()

    # STEP 2: INPUT FIELDS
    else:
        if st.button("⬅️ Back to Selection"):
            del st.session_state.auth_mode
            st.rerun()
        
        st.divider()

        if st.session_state.auth_mode == "new":
            st.subheader("📝 Register New Submitter Profile")
            h_name = st.text_input("Full Hospital Name:")
            u_name = st.text_input("Name of Encoder (Firstname Lastname):")
            pos = st.text_input("Official Position:")
            
            if st.button("🚀 Register & Generate My Code", type="primary"):
                invalid_entries = ["N/A", "NA", "NONE", ".", " ", "NOT APPLICABLE"]
                if not h_name or not u_name or not pos:
                    st.error("All fields are mandatory for accountability.")
                elif any(x == h_name.upper().strip() for x in invalid_entries):
                    st.error("Please provide valid facility information.")
                else:
                    new_id = f"HFDB-2026-{uuid.uuid4().hex[:8].upper()}"
                    save_new_profile(new_id, h_name, u_name, pos)
                    
                    st.success("✅ Profile Registered in Project FORT!")
                    st.warning("⚠️ **IMPORTANT:** Save the code below. You cannot log in without it.")
                    st.code(new_id, language="text")
                    
                    if st.button("OK - Proceed to Dashboard"):
                        st.session_state.user_id = new_id
                        st.session_state.user_info = {"hosp": h_name, "user": u_name}
                        st.rerun()

        elif st.session_state.auth_mode == "existing":
            st.subheader("🔓 Access Your Existing Profile")
            input_id = st.text_input("Enter User Identification Code:", placeholder="HFDB-2026-XXXXXXXX")
            
            if st.button("Verify & Enter", type="primary"):
                profiles = get_all_profiles()
                if input_id in profiles["User_ID"].values():
                    user_row = profiles[profiles["User_ID"] == input_id].iloc[0]
                    st.session_state.user_id = input_id
                    st.session_state.user_info = {
                        "hosp": user_row["Hospital_Name"], 
                        "user": user_row["Encoder_Name"]
                    }
                    st.success(f"Welcome back, {user_row['Encoder_Name']}!")
                    st.rerun()
                else:
                    st.error("Code not found. Please verify the code or register as a New User.")

# --- 4. UI: DASHBOARD & MODULES ---

def home_dashboard():
    st.title("🏥 Module Selection")
    st.info(f"Facility: **{st.session_state.user_info['hosp']}** | User: **{st.session_state.user_info['user']}**")
    
    cols = st.columns(3)
    modules = [
        {"key": "Mod1", "name": "Hospital Scorecard", "icon": "📊"},
        {"key": "Mod2", "name": "Financial Data", "icon": "💰"},
        {"key": "Mod3", "name": "Hospital MOOE", "icon": "🏥"}
    ]
    
    for i, mod in enumerate(modules):
        with cols[i]:
            if st.button(f"{mod['icon']} {mod['name']}\n\nStatus: ⚪ Pending", key=mod['key'], use_container_width=True):
                st.session_state.current_module = mod
                st.rerun()
    
    st.divider()
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

def module_page():
    mod = st.session_state.current_module
    st.header(f"{mod['icon']} {mod['name']}")
    st.write(f"Logged in as: {st.session_state.user_info['user']}")
    
    # Placeholder fields for data entry
    st.text_area("Observations")
    st.number_input("Numerical Data", min_value=0)
    
    if st.button("Back to Dashboard"):
        del st.session_state.current_module
        st.rerun()

# --- 5. ROUTER ---

if "user_id" not in st.session_state:
    login_screen()
elif "current_module" in st.session_state:
    module_page()
else:
    home_dashboard()

# --- 6. CSS STYLING ---
st.markdown("""
<style>
    div.stButton > button {
        height: 150px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 18px;
        white-space: pre-wrap;
    }
    button[kind="primary"] {
        background-color: #2e7d32 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)
