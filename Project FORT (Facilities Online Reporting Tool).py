import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. THE PAINT PALETTE (Dark Mode Edition) ---
COLORS = {
    "main_background": "#0E1117",      # Deep Midnight Background
    "sidebar_content": "#161B22",      # Secondary background for containers
    "card_background": "#21262D",      # Dark Slate for Module Cards
    "card_text": "#C9D1D9",            # Off-white/Gray text for readability
    "card_hover": "#30363D",           # Slightly lighter gray for hover
    
    "new_user_btn": "#1F6FEB",         # Bright Blue for "New User"
    "existing_user_btn": "#238636",    # Forest Green for "Existing User"
    "finalize_btn": "#DA3633",         # Alert Red for Finalizing
    
    "input_bg": "#0D1117",             # Input field background
    "input_text": "#FFFFFF",           # Input field text color
    "border_color": "#30363D"          # Subtle border color
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
        
        # Cleaner check: Convert the column to a list for a direct 'in' check
        if input_id in profiles["User_ID"].astype(str).tolist():
            row = profiles[profiles["User_ID"] == input_id].iloc[0]
            st.session_state.user_id = input_id
            st.session_state.user_info = {
                "hosp": row["Hospital_Name"], 
                "user": row["Encoder_Name"]
            }
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

# --- 7. CSS ENGINE (Enhanced for Dark Mode) ---
st.markdown(f"""
<style>
    /* Global App Background */
    .stApp {{
        background-color: {COLORS['main_background']};
        color: {COLORS['card_text']};
    }}

    /* Input Fields */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
        background-color: {COLORS['input_bg']} !important;
        color: {COLORS['input_text']} !important;
        border: 1px solid {COLORS['border_color']} !important;
    }}

    /* Large Card Buttons */
    div.stButton > button {{
        height: 140px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 18px;
        background-color: {COLORS['card_background']};
        color: {COLORS['card_text']};
        border: 1px solid {COLORS['border_color']};
        transition: 0.3s;
    }}

    /* Hover effect */
    div.stButton > button:hover {{
        background-color: {COLORS['card_hover']} !important;
        border-color: {COLORS['new_user_btn']} !important;
        color: #FFFFFF !important;
    }}

    /* "Primary" Button styling (Existing User / Proceed) */
    button[kind="primary"] {{
        background-color: {COLORS['existing_user_btn']} !important;
        color: white !important;
        border: none !important;
    }}

    /* Specific ID for New User Button to keep it Blue */
    button[key="btn_mode_new"] {{
        background-color: {COLORS['new_user_btn']} !important;
        color: white !important;
        border: none !important;
    }}
    
    /* Success/Warning box adjustments for Dark Mode */
    .stAlert {{
        background-color: {COLORS['sidebar_content']};
        border: 1px solid {COLORS['border_color']};
    }}
</style>
""", unsafe_allow_html=True)
