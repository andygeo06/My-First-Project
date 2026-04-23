import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. INITIAL CONFIG & CONNECTION ---
st.set_page_config(page_title="HFDB Online Data Submission Portal", layout="wide")

# Connection to Project FORT
conn = st.connection("gsheets", type=GSheetsConnection)

def get_all_profiles():
    return conn.read(worksheet="User_Profiles", ttl="0") # TTL=0 ensures fresh data every read

# --- 2. AUTHENTICATION LOGIC ---

def generate_user_id():
    year = datetime.now().year
    random_part = uuid.uuid4().hex[:8].upper()
    return f"HFDB-{year}-{random_part}"

def save_new_profile(user_id, h_name, u_name, pos):
    new_data = pd.DataFrame([{
        "User_ID": user_id,
        "Hospital_Name": h_name,
        "Encoder_Name": u_name,
        "Position": pos,
        "Year": 2026,
        "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    # Append to the User_Profiles worksheet
    conn.create(worksheet="User_Profiles", data=new_data)
    st.cache_data.clear() # Force app to see the new data

# --- 3. UI: LOGIN GATE ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.markdown("### National Health Facility Data Entry")
    
    choice = st.radio("Choose Access Method:", ["New User", "Existing User"], horizontal=True)
    st.divider()

    if choice == "New User":
        h_name = st.text_input("Hospital Name:")
        u_name = st.text_input("User Name:")
        pos = st.text_input("Position:")
        
        if st.button("🚀 Register & Generate Access Code", type="primary"):
            invalid = ["N/A", "NA", "NONE", ".", " "]
            if not h_name or not u_name or not pos:
                st.error("All fields are mandatory.")
            elif any(x == h_name.upper().strip() for x in invalid):
                st.error("Please enter a valid Hospital Name.")
            else:
                new_id = generate_user_id()
                save_new_profile(new_id, h_name, u_name, pos)
                
                st.success("✅ Profile Created and Logged to Project FORT!")
                st.warning("⚠️ **SAVE THIS CODE NOW.** It is your only way to return to your work.")
                st.code(new_id, language="text")
                
                if st.button("Proceed to Modules"):
                    st.session_state.user_id = new_id
                    st.session_state.user_info = {"hosp": h_name, "user": u_name}
                    st.rerun()

    else:
        input_id = st.text_input("Enter User Identification Code:", placeholder="HFDB-2026-XXXXXXXX")
        if st.button("Access Portal"):
            profiles = get_all_profiles()
            if input_id in profiles["User_ID"].values():
                user_row = profiles[profiles["User_ID"] == input_id].iloc[0]
                st.session_state.user_id = input_id
                st.session_state.user_info = {"hosp": user_row["Hospital_Name"], "user": user_row["Encoder_Name"]}
                st.success(f"Welcome back, {user_row['Encoder_Name']}!")
                st.rerun()
            else:
                st.error("Code not found. Please verify or register as a New User.")

# --- 4. UI: MODULE SELECTION (DASHBOARD) ---

def dashboard():
    st.title("🏥 Module Selection")
    st.write(f"Facility: **{st.session_state.user_info['hosp']}** | ID: `{st.session_state.user_id}`")
    
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
    
    if st.button("Logout"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 5. UI: MODULE ENTRY SHELL ---

def module_page():
    mod = st.session_state.current_module
    st.header(f"{mod['icon']} {mod['name']}")
    st.info(f"Encoding as: {st.session_state.user_info['user']} ({st.session_state.user_info['hosp']})")
    
    # Placeholder for actual module fields
    st.text_area("Observations / General Remarks")
    st.number_input("Numerical Indicator Sample", min_value=0)
    
    col1, col2 = st.columns(2)
    if col1.button("Save Draft"):
        st.toast("Draft saved to Google Sheets.")
    if col2.button("Finalize Submission", type="primary"):
        st.success("Module Finalized!")
        del st.session_state.current_module
        st.rerun()
    
    st.button("Exit to Dashboard", on_click=lambda: st.session_state.pop("current_module"))

# --- ROUTER ---
if "user_id" not in st.session_state:
    login_screen()
elif "current_module" in st.session_state:
    module_page()
else:
    dashboard()

# --- STYLING ---
st.markdown("""
<style>
    div.stButton > button { height: 100px; border-radius: 12px; font-weight: bold; }
    .stTextInput>div>div>input { font-size: 18px; }
</style>
""", unsafe_allow_html=True)
