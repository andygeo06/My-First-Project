import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. THE PAINT PALETTE (Change your colors here!) ---
COLORS = {
    "main_background": "#FFFFFF",      # App Background
    "card_background": "#F0F2F6",      # Default Module Card color
    "new_user_btn": "#1f77b4",         # "New User" Button (Blue)
    "existing_user_btn": "#2E7D32",    # "Existing User" Button (Green)
    "back_btn": "#6c757d",             # "Back" Button (Gray)
    "finalize_btn": "#d32f2f",         # "Finalize" Button (Red)
    "card_text": "#000000",            # Text inside cards
    "card_hover": "#E8F5E9"            # Color when hovering over a card
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

# --- 4. UI COMPONENTS ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.markdown("### National Health Facility Data Entry (2026)")
    st.divider()

    # STEP 1: MODE SELECTION
    if "auth_mode" not in st.session_state:
        st.subheader("Please choose an option to begin:")
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("🆕\n\nNEW USER\n\nCreate a Profile", use_container_width=True, key="btn_mode_new"):
                st.session_state.auth_mode = "new"
                st.rerun()
        with c2:
            # We use type="primary" to link to our custom Green CSS later
            if st.button("🔑\n\nEXISTING USER\n\nContinue Work", use_container_width=True, type="primary", key="btn_mode_exist"):
                st.session_state.auth_mode = "existing"
                st.rerun()

    # STEP 2: INPUTS
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
                    new_id = f"HFDB-2026-{uuid.uuid4().hex[:8].upper()}"
                    if save_new_profile(new_id, h_name, u_name, pos):
                        st.session_state.generated_id = new_id
                        st.session_state.reg_success = True
                        st.session_state.temp_info = {"hosp": h_name, "user": u_name}

            # If registered successfully, show code and the 'Enter' button
            if st.session_state.get("reg_success"):
                st.success("✅ Profile Registered in Project FORT!")
                st.code(st.session_state.generated_id)
                st.warning("⚠️ **SAVE THIS CODE.** You cannot log back in without it.")
                
                if st.button("Proceed to Dashboard", type="primary"):
                    st.session_state.user_id = st.session_state.generated_id
                    st.session_state.user_info = st.session_state.temp_info
                    st.rerun()

        elif st.session_state.auth_mode == "existing":
            st.subheader("🔓 Access Your Existing Profile")
            input_id = st.text_input("Enter User Identification Code:")
            if st.button("Verify & Enter Portal", type="primary"):
                profiles = get_all_profiles()
                if input_id in profiles["User_ID"].values():
                    row = profiles[profiles["User_ID"] == input_id].iloc[0]
                    st.session_state.user_id = input_id
                    st.session_state.user_info = {"hosp": row["Hospital_Name"], "user": row["Encoder_Name"]}
                    st.rerun()
                else:
                    st.error("Code not found. Please check your spelling or register as new.")

# --- 5. DASHBOARD ---

def dashboard():
    st.title("🏥 Module Selection")
    st.info(f"Facility: **{st.session_state.user_info['hosp']}** | User: **{st.session_state.user_info['user']}**")
    
    modules = [
        {"key": "Mod1", "name": "Hospital Scorecard", "icon": "📊"},
        {"key": "Mod2", "name": "Financial Data", "icon": "💰"},
        {"key": "Mod3", "name": "Hospital MOOE", "icon": "🏥"}
    ]
    
    cols = st.columns(3)
    for i, mod in enumerate(modules):
        with cols[i]:
            if st.button(f"{mod['icon']} {mod['name']}\n\nStatus: ⚪ Pending", key=mod['key'], use_container_width=True):
                st.session_state.current_module = mod
                st.rerun()
    
    st.divider()
    if st.button("Logout / Switch User"):
        st.session_state.clear()
        st.rerun()

# --- 6. ROUTER ---

if "user_id" not in st.session_state:
    login_screen()
elif "current_module" in st.session_state:
    st.header(f"{st.session_state.current_module['icon']} {st.session_state.current_module['name']}")
    st.write("Form fields will be added here next.")
    if st.button("Back to Dashboard"):
        del st.session_state.current_module
        st.rerun()
else:
    dashboard()

# --- 7. CSS ENGINE (Uses the Paint Palette) ---
st.markdown(f"""
<style>
    /* Global Background */
    .stApp {{
        background-color: {COLORS['main_background']};
    }}

    /* Large Card Buttons */
    div.stButton > button {{
        height: 140px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 18px;
        background-color: {COLORS['card_background']};
        color: {COLORS['card_text']};
        border: 1px solid #d1d5db;
        transition: 0.3s;
    }}

    /* Hover effect for all buttons */
    div.stButton > button:hover {{
        background-color: {COLORS['card_hover']} !important;
        border-color: {COLORS['existing_user_btn']} !important;
    }}

    /* "Primary" Button styling (Existing User / Proceed) */
    button[kind="primary"] {{
        background-color: {COLORS['existing_user_btn']} !important;
        color: white !important;
    }}

    /* "Secondary" Button styling (New User) */
    button[key="btn_mode_new"] {{
        background-color: {COLORS['new_user_btn']} !important;
        color: white !important;
    }}

</style>
""", unsafe_allow_html=True)
