import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIG & CONNECTION ---
st.set_page_config(page_title="HFDB Online Data Submission Portal", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_all_profiles():
    return conn.read(worksheet="User_Profiles", ttl="0")

def save_new_profile(user_id, h_name, u_name, pos):
    # 1. Fetch existing profiles first
    existing_profiles = get_all_profiles()
    
    # 2. Create the new row
    new_row = pd.DataFrame([{
        "User_ID": user_id,
        "Hospital_Name": h_name,
        "Encoder_Name": u_name,
        "Position": pos,
        "Year": 2026,
        "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    # 3. Combine them (Stack the new row at the bottom of the old data)
    updated_df = pd.concat([existing_profiles, new_row], ignore_index=True)
    
    # 4. Use .update() instead of .create() 
    # This writes the updated list back to the specific worksheet
    conn.update(worksheet="User_Profiles", data=updated_df)
    
    st.cache_data.clear() # Clear cache so the app sees the new user immediately

# --- UI: THE NEW AUTHENTICATION GATE ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.markdown("### National Health Facility Data Entry (2026)")
    st.divider()

    # Step 1: Mode Selection (Hidden if a mode is already selected)
    if "auth_mode" not in st.session_state:
        st.subheader("Please choose an option to begin:")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🆕\n\nNEW USER\n\nCreate a Profile", use_container_width=True):
                st.session_state.auth_mode = "new"
                st.rerun()
                
        with col2:
            # Styled via CSS below to appear Green
            if st.button("🔑\n\nEXISTING USER\n\nContinue Work", use_container_width=True, type="primary"):
                st.session_state.auth_mode = "existing"
                st.rerun()

    # Step 2: Conditional Input Fields
    else:
        # Button to return to the selection screen
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
                invalid = ["N/A", "NA", "NONE", ".", " ", "NOT APPLICABLE"]
                if not h_name or not u_name or not pos:
                    st.error("All fields are required to establish accountability.")
                elif any(x == h_name.upper().strip() for x in invalid):
                    st.error("Invalid input detected. Please provide your actual hospital name.")
                else:
                    new_id = f"HFDB-2026-{uuid.uuid4().hex[:8].upper()}"
                    save_new_profile(new_id, h_name, u_name, pos)
                    
                    st.success("✅ Profile Registered in Project FORT!")
                    st.warning("⚠️ **CRITICAL: RECORD YOUR ACCESS CODE.** You cannot log in without it.")
                    st.code(new_id, language="text")
                    
                    if st.button("I Have Saved My Code - Enter Portal"):
                        st.session_state.user_id = new_id
                        st.session_state.user_info = {"hosp": h_name, "user": u_name}
                        st.rerun()

        elif st.session_state.auth_mode == "existing":
            st.subheader("🔓 Access Your Existing Profile")
            input_id = st.text_input("Enter Your User Identification Code:", 
                                     placeholder="Example: HFDB-2026-A1B2C3D4")
            
            if st.button("Verify & Enter", type="primary"):
                profiles = get_all_profiles()
                if input_id in profiles["User_ID"].values():
                    user_row = profiles[profiles["User_ID"] == input_id].iloc[0]
                    st.session_state.user_id = input_id
                    st.session_state.user_info = {
                        "hosp": user_row["Hospital_Name"], 
                        "user": user_row["Encoder_Name"]
                    }
                    st.success(f"Identity Verified. Welcome back, {user_row['Encoder_Name']}.")
                    st.rerun()
                else:
                    st.error("Identification Code not found. Please verify the code or register as a New User.")

# --- UI: DASHBOARD ---

def dashboard():
    st.title("🏥 Module Selection")
    st.info(f"Facility: **{st.session_state.user_info['hosp']}** | User: **{st.session_state.user_info['user']}**")
    
    # Grid of Module Cards
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
    if st.button("Logout / Exit Session"):
        st.session_state.clear()
        st.rerun()

# --- ROUTER ---
if "user_id" not in st.session_state:
    login_screen()
elif "current_module" in st.session_state:
    # Placeholder for Module Content
    st.header(f"Module: {st.session_state.current_module['name']}")
    if st.button("Back to Dashboard"):
        del st.session_state.current_module
        st.rerun()
else:
    dashboard()

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Large Buttons for Mode Selection and Modules */
    div.stButton > button {
        height: 150px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 20px;
        white-space: pre-wrap; /* Allows emojis and text to stack */
    }
    
    /* Ensuring the Primary (Existing User) button is clearly visible */
    button[kind="primary"] {
        background-color: #2e7d32 !important;
        color: white !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)
