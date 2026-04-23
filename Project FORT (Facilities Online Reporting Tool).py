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

def get_facility_list():
    """Fetches the master list of authorized facilities."""
    try:
        # Pulls from the new 'Facility_List' tab
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List", ttl=0)
        # Convert the column to a sorted list, removing any empty rows
        return sorted(df["Facility_Name"].dropna().unique().tolist())
    except Exception as e:
        st.error(f"Error loading Facility List: {e}")
        return ["Error loading list..."]

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

def get_module_config(mod_key):
    """Fetches deadline and instructions for a specific module."""
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Config", ttl=0)
        config = df[df["Module_Key"] == mod_key].iloc[0]
        return {
            "deadline": config["Deadline_Date"],
            "notes": config["Instructions"]
        }
    except Exception:
        return {"deadline": "Not Set", "notes": "No specific instructions."}

def get_all_deadlines():
    """Fetches all deadlines from the Config tab as a dictionary."""
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Config", ttl=0)
        # Creates a dictionary like: {"Mod1": "2026-05-15", "Mod2": "2026-06-01"}
        return pd.Series(df.Deadline_Date.values, index=df.Module_Key).to_dict()
    except:
        return {}

# --- 4. UI: LOGIN SCREEN ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.divider()

    if "auth_mode" not in st.session_state:
        # ... (keep your Mode Selection buttons here) ...
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
            
            # --- NEW DROPDOWN LOGIC ---
            authorized_facilities = get_facility_list()
            h_name = st.selectbox("Select Your Hospital/Facility:", options=[""] + authorized_facilities, help="Start typing to search")
            
            u_name = st.text_input("Name of Encoder:")
            pos = st.text_input("Official Position:")
            
            if st.button("🚀 Register & Generate Code", type="secondary"):
                if not h_name or not u_name or not pos:
                    st.error("Please select a hospital and fill in all fields.")
                else:
                    profiles = get_all_profiles()
                    existing_hospitals = profiles["Hospital_Name"].str.upper().str.strip().tolist()
                    current_h_input = h_name.upper().strip()

                    if current_h_input in existing_hospitals:
                        st.error(f"🛑 Error: {h_name} already has an existing account.")
                        st.info("Redirecting to Login screen...")
                        import time
                        time.sleep(2.5)
                        st.session_state.auth_mode = "existing"
                        st.rerun()
                    else:
                        new_id = f"HFDB-2026-{uuid.uuid4().hex[:8].upper()}"
                        if save_new_profile(new_id, h_name, u_name, pos):
                            st.session_state.generated_id = new_id
                            st.session_state.reg_success = True
                            st.session_state.temp_info = {"hosp": h_name, "user": u_name}

            if st.session_state.get("reg_success"):
                # ... (keep your success and Enter Dashboard code) ...
                st.success("✅ Profile Registered!")
                st.code(st.session_state.generated_id)
                if st.button("Enter Dashboard", type="primary"):
                    st.session_state.user_id = st.session_state.generated_id
                    st.session_state.user_info = st.session_state.temp_info
                    st.rerun()

        # ... (keep your Existing User elif block) ...
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
    
    # 1. Fetch all deadlines at once
    deadlines = get_all_deadlines()
    
    modules = [
        {"key": "Mod1", "name": "Hospital Scorecard", "icon": "📊"},
        {"key": "Mod2", "name": "Financial Data", "icon": "💰"},
        {"key": "Mod3", "name": "Hospital MOOE", "icon": "🏥"}
    ]
    
    cols = st.columns(3)
    
    for i, mod in enumerate(modules):
        # 2. Get the specific date for this key
        date_str = deadlines.get(mod['key'], "TBD")
        
        with cols[i]:
            # 3. Embed the deadline directly into the button text
            # We use \n\n to create clear separation
            button_label = (
                f"{mod['icon']} {mod['name']}\n\n"
                f"📅 Deadline: {date_str}\n\n"
                f"Status: ⚪ Pending"
            )
            
            if st.button(button_label, key=mod['key'], use_container_width=True):
                st.session_state.current_module = mod
                st.rerun()
    
    st.divider()
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# --- 6. ROUTER ---

# --- 6. UPDATED ROUTER WITH DEADLINE BANNER ---

if "user_id" not in st.session_state:
    login_screen()
elif "current_module" in st.session_state:
    # 1. Fetch the deadline info immediately
    mod_info = st.session_state.current_module
    config = get_module_config(mod_info['key'])
    
    # 2. Header & Navigation
    c_head, c_back = st.columns([5, 1])
    c_head.header(f"{mod_info['icon']} {mod_info['name']}")
    if c_back.button("🏠 Home", use_container_width=True):
        del st.session_state.current_module
        st.rerun()
    
    # 3. HIGH-VISIBILITY DEADLINE PROMPT
    # We use a columns layout to put the deadline right at the top
    st.divider()
    d1, d2 = st.columns([1, 2])
    with d1:
        st.error(f"🗓️ **DEADLINE:** \n\n {config['deadline']}")
    with d2:
        st.warning(f"📝 **INSTRUCTIONS:** \n\n {config['notes']}")
    st.divider()

    # 4. Route to the specific module function
    mod_key = mod_info['key']
    if mod_key == "Mod1":
        module_scorecard()
    elif mod_key == "Mod2":
        module_financial()
    elif mod_key == "Mod3":
        module_mooe()
else:
    dashboard()

# --- 7. CSS ENGINE (Tiered Font Sizes) ---
st.markdown(f"""
<style>
    /* Global App Background */
    .stApp {{
        background-color: {COLORS['main_background']};
        color: {COLORS['card_text']};
    }}

    /* Balanced Card Buttons */
    div.stButton > button {{
        height: auto;
        padding: 25px 15px !important;
        border-radius: 12px;
        background-color: {COLORS['card_background']};
        color: {COLORS['card_text']};
        border: 1px solid {COLORS['border_color']};
        transition: all 0.2s ease;
        
        /* This is the key: it treats the text as a block */
        display: block; 
        text-align: center;
        line-height: 1.6;
    }}

    /* Targeting the first line (Module Name) */
    div.stButton > button::first-line {{
        font-size: 1.4rem !important;
        font-weight: bold !important;
        color: #FFFFFF !important;
    }}

    /* Targeting everything after the first line (Deadline & Status) */
    div.stButton > button {{
        font-size: 0.9rem;
        font-weight: 400;
    }}

    /* Hover effect */
    div.stButton > button:hover {{
        background-color: {COLORS['card_hover']} !important;
        border-color: {COLORS['new_user_btn']} !important;
        transform: translateY(-2px);
    }}

    /* Existing User / Primary Button styling */
    button[kind="primary"] {{
        background-color: {COLORS['existing_user_btn']} !important;
        color: white !important;
        border: none !important;
    }}
</style>
""", unsafe_allow_html=True)
