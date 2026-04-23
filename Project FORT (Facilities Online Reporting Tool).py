import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. INITIAL CONFIGURATION ---
st.set_page_config(page_title="HFDB Online Data Submission Portal", layout="wide", initial_sidebar_state="collapsed")

# Connection to Google Sheets (Project FORT)
# Note: Ensure secrets are set in Streamlit Cloud for GSheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Module Mapping
MODULES = {
    "Mod1": {"name": "Hospital Scorecard", "icon": "📊", "sheet": "Mod1"},
    "Mod2": {"name": "Financial Data", "icon": "💰", "sheet": "Mod2"},
    "Mod3": {"name": "Hospital MOOE", "icon": "🏥", "sheet": "Mod3"}
}

# --- 2. SHARED FUNCTIONS (ACCOUNTABILITY & UTILITIES) ---

def generate_edit_code():
    return f"HFDB-{uuid.uuid4().hex[:6].upper()}"

def get_status_color(status):
    if status == "Submitted": return "🟢"
    if status == "In Progress": return "🟡"
    return "⚪"

def accountability_header(mod_name):
    """Reusable header for all modules to ensure accountability."""
    st.markdown(f"### 🔐 {mod_name}: Verification")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        hosp = c1.text_input("Hospital Name", value=st.session_state.get('hosp_name', ""))
        enc = c2.text_input("Encoder Name", value=st.session_state.get('encoder', ""))
        pos = c3.text_input("Position", value=st.session_state.get('position', ""))
        
        # Save to session state for persistence across modules
        st.session_state.hosp_name, st.session_state.encoder, st.session_state.position = hosp, enc, pos
    
    return hosp and enc and pos

# --- 3. PAGE: HOME DASHBOARD ---

def home_page():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.markdown("#### *2026 Data Cycle*")
    st.divider()

    # Dashboard Progress Section
    st.subheader("Your Submission Modules")
    
    # Grid Layout for Mobile-Friendly Cards
    cols = st.columns(len(MODULES))
    
    for i, (key, info) in enumerate(MODULES.items()):
        # Mock status check - in production, this reads 'Status' from the GSheet
        status = st.session_state.get(f"status_{key}", "Pending")
        indicator = get_status_color(status)
        
        with cols[i]:
            # The Card Component (Styled Button)
            card_label = f"{info['icon']} {info['name']}\n\n{indicator} {status}"
            if st.button(card_label, key=key, use_container_width=True):
                st.session_state.current_mod = key
                st.session_state.page = "Module_Entry"
                st.rerun()

# --- 4. PAGE: UNIVERSAL MODULE ENTRY ---

def module_entry_page():
    mod_key = st.session_state.current_mod
    mod_info = MODULES[mod_key]
    
    st.button("⬅️ Back to Dashboard", on_click=lambda: st.session_state.update({"page": "Home"}))
    st.header(f"{mod_info['icon']} {mod_info['name']}")
    
    # A. EDIT CODE BLOCK
    with st.expander("🔑 Have an Edit Code? Click here to load previous data"):
        edit_code_input = st.text_input("Enter 8-digit Code")
        if st.button("Retrieve Submission"):
            st.info("Searching Project FORT for your record...")
            # Logic: conn.read() where Code == edit_code_input

    # B. ACCOUNTABILITY HEADER
    is_valid = accountability_header(mod_info['name'])
    
    # C. DYNAMIC DATA FIELDS (Sample Fields)
    st.markdown("---")
    st.subheader("Entry Form")
    with st.container():
        # Example fields - these will change per module in the future
        data_a = st.number_input("Numerical Data Point", min_value=0)
        data_b = st.text_area("Narrative/Remarks")

    # D. SUBMISSION ACTIONS
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button("💾 Save as Temporary Draft"):
            # Update Status to In Progress and Sync to Sheet
            st.session_state[f"status_{mod_key}"] = "In Progress"
            st.toast("Draft saved to Google Sheets.")
            
    with c2:
        if st.button("✅ Finalize Submission", type="primary", disabled=not is_valid):
            new_code = generate_edit_code()
            # Logic to write to GSheets 'ModX' sheet
            st.session_state[f"status_{mod_key}"] = "Submitted"
            st.success(f"Successfully Submitted! **Edit Code: {new_code}**")
            st.balloons()

# --- 5. APP ROUTER ---

if 'page' not in st.session_state:
    st.session_state.page = "Home"

if st.session_state.page == "Home":
    home_page()
elif st.session_state.page == "Module_Entry":
    module_entry_page()

# --- CSS FOR CUSTOM BUTTON HEIGHTS (MOBILE OPTIMIZATION) ---
st.markdown("""
<style>
    div.stButton > button {
        height: 150px;
        border-radius: 15px;
        font-size: 18px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)
