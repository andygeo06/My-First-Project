import streamlit as st
import uuid
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="HFDB Online Data Submission Portal", layout="wide")

# Mock function to simulate Google Sheets connection
def get_submission_by_code(code, hospital_id, module_sheet):
    # In reality, this would be: conn.read(query=f"SELECT * FROM {module_sheet} WHERE Code='{code}'")
    return None # Returns None if new, or a Dict if editing

# --- SHARED COMPONENTS ---
def accountability_header(module_name):
    st.info(f"📍 Module: {module_name}")
    with st.expander("🔐 Accountability & Edit Access", expanded=True):
        c1, c2 = st.columns(2)
        edit_code = c1.text_input("Enter Edit Code (Leave blank for New Submission)", help="Enter a previous code to load your data.")
        
        st.divider()
        
        c3, c4, c5 = st.columns(3)
        hosp_name = c3.text_input("Hospital Name", value=st.session_state.get('hosp_name', ""))
        encoder = c4.text_input("Encoder Name", value=st.session_state.get('encoder', ""))
        position = c5.text_input("Position", value=st.session_state.get('pos', ""))
        
        # Persistence
        st.session_state.hosp_name, st.session_state.encoder, st.session_state.pos = hosp_name, encoder, position
        
    return edit_code, (hosp_name and encoder and position)

# --- HOME PAGE ---
def home_page():
    st.title("🏥 HFDB Online Data Submission Portal (2026)")
    
    # Dashboard Section
    st.subheader("Your Submission Progress")
    # Mock data for demonstration
    modules = {"Mod1: Scorecard": "Submitted", "Mod2: Financial": "In Progress", "Mod3: MOOE": "Pending"}
    
    cols = st.columns(len(modules))
    for i, (name, status) in enumerate(modules.items()):
        color = "🟢" if status == "Submitted" else "🟡" if status == "In Progress" else "⚪"
        cols[i].metric(label=name, value=status, delta=color, delta_color="normal")

    st.divider()
    if st.button("🚀 Enter Hospital MOOE Module (Mod3)", use_container_width=True):
        st.session_state.page = "MOOE"
        st.rerun()

# --- MODULE: MOOE ---
def module_mooe():
    st.header("📊 Hospital MOOE Entry")
    edit_code, is_valid = accountability_header("Hospital MOOE")
    
    # Logic to load previous data if edit_code is provided
    if edit_code:
        st.warning(f"Attempting to load data for code: {edit_code}...")
        # (Insert code here to fetch from Google Sheets and fill session_state)

    st.subheader("Financial Reporting")
    ps_value = st.number_input("Personnel Services (PS)", value=0)
    mooe_value = st.number_input("Maintenance and Other Operating Expenses", value=0)

    if st.button("Finalize & Get Submission Code", disabled=not is_valid):
        # Generate Code
        new_code = f"HFDB-{uuid.uuid4().hex[:6].upper()}"
        
        # ACTION: Save to Google Sheet (Hospital_ID, Code, Data, etc.)
        st.success(f"Successfully Submitted! Your Edit Code is: **{new_code}**")
        st.code(new_code)
        st.info("Keep this code safe. You will need it to edit this submission later.")
        
        if st.button("Return Home"):
            st.session_state.page = "Home"
            st.rerun()

# --- ROUTER ---
if 'page' not in st.session_state: st.session_state.page = "Home"

if st.session_state.page == "Home": home_page()
elif st.session_state.page == "MOOE": module_mooe()
