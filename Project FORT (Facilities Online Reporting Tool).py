import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. THE PAINT PALETTE (Centralized Styles) ---
COLORS = {
    "main_background": "#0E1117",      # Global background
    "sidebar_content": "#161B22",      
    "card_background": "#21262D",      # Module card color
    "card_text": "#C9D1D9",            # Font color
    "card_hover": "#30363D",           
    "new_user_btn": "#1F6FEB",         # Blue for New User
    "existing_user_btn": "#238636",    # Green for Existing User
    "border_color": "#30363D",
    "button_height": "auto",           # Compact setting
    "button_padding": "15px 10px",     # Tight padding around text
    "font_size": "1.1rem"
}

# --- 2. CONFIG & CONNECTION ---
st.set_page_config(page_title="Project FORT", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. DATABASE FUNCTIONS ---

def get_all_profiles():
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
    except:
        return pd.DataFrame(columns=["User_ID", "Hospital_Name", "Encoder_Name", "Position", "Year", "Created_At"])

def save_new_profile(user_id, h_name, u_name, pos):
    try:
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
        conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=updated_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return False

# --- 4. UI: LOGIN SCREEN ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.divider()

    if "auth_mode" not in st.session_state:
        st.subheader("Please choose an option to begin:")
        c1, c2 = st.columns(2)
        if c1.button("🆕\n\nNEW USER\n\nCreate a Profile", use_container_width=True, key="gate_new"):
            st.session_state.auth_mode = "new"
            st.rerun()
        if c2.button("🔑\n\nEXISTING USER\n\nContinue Work", use_container_width=True, type="primary", key="gate_exist"):
            st.session_state.auth_mode = "existing"
            st.rerun()
    else:
        if st.button("⬅️ Back to Selection"):
            del st.session_state.auth_mode
            st.rerun()

        if st.session_state.auth_mode == "new":
            st.subheader("📝 Register New Submitter Profile")
            h_name = st.text_input("Full Hospital Name:")
            u_name = st.text_input("Name of Encoder:")
            pos = st.text_input("Official Position:")
            
            if st.button("🚀 Register & Generate Code", type="secondary"):
                if not h_name or not u_name or not pos:
                    st.error("Fields cannot be blank.")
                else:
                    # 1. Fetch latest data to check for duplicates
                    profiles = get_all_profiles()
                    
                    # 2. Check if Hospital Name already exists (Case-insensitive)
                    existing_hospitals = profiles["Hospital_Name"].str.upper().str.strip().tolist()
                    current_h_input = h_name.upper().strip()

                    if current_h_input in existing_hospitals:
                        st.error(f"🛑 Error: {h_name} already has an existing account.")
                        st.info("Redirecting you to the Login screen...")
                        
                        # Wait 2 seconds so they can read the error, then redirect
                        import time
                        time.sleep(2.5)
                        st.session_state.auth_mode = "existing"
                        st.rerun()
                    else:
                        # 3. Proceed with Registration if no duplicate found
                        new_id = f"HFDB-2026-{uuid.uuid4().hex[:8].upper()}"
                        if save_new_profile(new_id, h_name, u_name, pos):
                            st.session_state.generated_id = new_id
                            st.session_state.reg_success = True
                            st.session_state.temp_info = {"hosp": h_name, "user": u_name}
                            
            if st.session_state.get("reg_success"):
                st.success("✅ Profile Registered!")
                st.code(st.session_state.generated_id)
                if st.button("Enter Dashboard", type="primary"):
                    st.session_state.user_id = st.session_state.generated_id
                    st.session_state.user_info = st.session_state.temp_info
                    st.rerun()

        elif st.session_state.auth_mode == "existing":
            st.subheader("🔓 Access Your Existing Profile")
            input_id = st.text_input("Enter User Identification Code:")
            if st.button("Verify & Enter Portal", type="primary"):
                profiles = get_all_profiles()
                if input_id in profiles["User_ID"].astype(str).tolist():
                    row = profiles[profiles["User_ID"] == input_id].iloc[0]
                    st.session_state.user_id = input_id
                    st.session_state.user_info = {"hosp": row["Hospital_Name"], "user": row["Encoder_Name"]}
                    st.rerun()
                else:
                    st.error("Code not found.")

# --- 5. UI: DASHBOARD ---

def dashboard():
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

# --- 6. ROUTER ---

if "user_id" not in st.session_state:
    login_screen()
elif "current_module" in st.session_state:
    st.header(f"{st.session_state.current_module['icon']} {st.session_state.current_module['name']}")
    if st.button("Back to Dashboard"):
        del st.session_state.current_module
        st.rerun()
else:
    dashboard()

# --- 7. CSS ENGINE ---
st.markdown(f"""
<style>
    .stApp {{
        background-color: {COLORS['main_background']};
        color: {COLORS['card_text']};
    }}
    div.stButton > button {{
        height: {COLORS['button_height']};
        padding: {COLORS['button_padding']} !important;
        border-radius: 12px;
        font-weight: 600;
        font-size: {COLORS['font_size']};
        background-color: {COLORS['card_background']};
        color: {COLORS['card_text']};
        border: 1px solid {COLORS['border_color']};
        transition: 0.3s;
    }}
    div.stButton > button:hover {{
        background-color: {COLORS['card_hover']} !important;
        border-color: {COLORS['new_user_btn']} !important;
    }}
    button[kind="primary"] {{
        background-color: {COLORS['existing_user_btn']} !important;
        color: white !important;
        border: none !important;
    }}
</style>
""", unsafe_allow_html=True)
