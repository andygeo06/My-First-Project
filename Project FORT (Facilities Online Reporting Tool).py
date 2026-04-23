import streamlit as st
import uuid
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="HFDB Online Data Submission Portal", layout="wide")

def generate_user_id():
    """Generates the HFDB-YEAR-RANDOMCODE format."""
    year = datetime.now().year
    random_part = uuid.uuid4().hex[:8].upper()
    return f"HFDB-{year}-{random_part}"

# --- STAGE 1: THE LOGIN GATEKEEPER ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.markdown("### Welcome. Please identify yourself to proceed.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🆕 New User", use_container_width=True, type="primary"):
            st.session_state.auth_mode = "new"
            
    with col2:
        if st.button("🔑 Existing User", use_container_width=True):
            st.session_state.auth_mode = "existing"

    # --- Mode: New User Registration ---
    if st.session_state.get("auth_mode") == "new":
        st.divider()
        st.subheader("Create New Submitter Profile")
        h_name = st.text_input("Hospital Name:")
        u_name = st.text_input("User Name:")
        pos = st.text_input("Position:")
        
        if st.button("Generate My Access Code"):
            # Validation: No blanks, No "N/A"
            invalid_terms = ["N/A", "NA", "NONE", ".", " "]
            if not h_name or not u_name or not pos:
                st.error("Fields cannot be blank.")
            elif any(term == h_name.upper().strip() for term in invalid_terms) or \
                 any(term == u_name.upper().strip() for term in invalid_terms):
                st.error("Please provide valid information. 'N/A' is not accepted.")
            else:
                # Success Logic
                new_id = generate_user_id()
                st.session_state.temp_id = new_id
                st.session_state.user_profile = {"hosp": h_name, "user": u_name, "pos": pos}
                st.success("Profile Validated!")
                
                # Solid Prompt for Code
                st.warning("⚠️ **IMPORTANT: SAVE THIS CODE.** You will need it to return to your work.")
                st.code(new_id, language="text")
                st.info("You can copy the code above. Store it in a Notepad or on a sheet of paper.")
                
                if st.button("OK - Proceed to Modules"):
                    st.session_state.user_id = new_id
                    st.session_state.authenticated = True
                    st.rerun()

    # --- Mode: Existing User Login ---
    elif st.session_state.get("auth_mode") == "existing":
        st.divider()
        st.subheader("Return to Your Work")
        input_id = st.text_input("Enter User Identification Code:", placeholder="Format: HFDB-2026-XXXXXXXX")
        
        if st.button("Submit"):
            if input_id.startswith("HFDB-2026-") and len(input_id) > 12:
                # In production: Check Google Sheets if ID exists
                st.session_state.user_id = input_id
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid Code Format. Please check your code and try again.")

# --- STAGE 2: THE DASHBOARD ---

def home_dashboard():
    st.title("🏥 Module Selection Screen")
    st.write(f"Logged in as: `{st.session_state.user_id}`")
    
    # Large Card Buttons
    modules = [
        {"id": "Mod1", "name": "Hospital Scorecard", "icon": "📊"},
        {"id": "Mod2", "name": "Financial Data", "icon": "💰"},
        {"id": "Mod3", "name": "Hospital MOOE", "icon": "🏥"}
    ]
    
    cols = st.columns(3)
    for i, mod in enumerate(modules):
        with cols[i]:
            # Pull status from sheet (mocked here)
            if st.button(f"{mod['icon']} {mod['name']}\n\nStatus: ⚪ Pending", key=mod['id'], use_container_width=True):
                st.session_state.current_page = mod['id']
                st.rerun()

# --- APP ROUTER ---
if "authenticated" not in st.session_state:
    login_screen()
elif st.session_state.get("current_page"):
    # Module Detail Page
    st.header(f"Editing: {st.session_state.current_page}")
    if st.button("Back to Modules"):
        del st.session_state.current_page
        st.rerun()
else:
    home_dashboard()

# --- STYLING ---
st.markdown("""
<style>
    div.stButton > button {
        height: 120px;
        border-radius: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)
