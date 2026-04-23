import streamlit as st
import json
import os
from datetime import datetime

# 1. Configuration & Yearly Logic
CURRENT_YEAR = datetime.now().year
DATA_FILE = f"submission_state_{CURRENT_YEAR}.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "Hospital Scorecard": {"status": "Pending", "data": {}},
        "Financial Data": {"status": "Pending", "data": {}},
        "Hospital MOOE": {"status": "Pending", "data": {}}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialize Session State from JSON
if 'master_data' not in st.session_state:
    st.session_state.master_data = load_data()

# ---------------------------------------------------------
# UI BLOCKS
# ---------------------------------------------------------

def home_page():
    st.title(f"🏥 HFDB Online Data Submission Portal ({CURRENT_YEAR})")
    
    # Progress Calculation
    total = len(st.session_state.master_data)
    done = sum(1 for m in st.session_state.master_data.values() if m['status'] == "Submitted")
    
    st.subheader("Your Progress Dashboard")
    st.progress(done / total)
    st.write(f"**{done} of {total} Modules Completed**")

    # Dynamic Module Buttons
    cols = st.columns(total)
    for i, (name, info) in enumerate(st.session_state.master_data.items()):
        with cols[i]:
            if st.button(f"Go to {name}"):
                st.session_state.page = name
                st.rerun()

def module_template(module_name):
    st.title(f"📝 {module_name}")
    
    # Load previously saved (temporary) data
    existing_data = st.session_state.master_data[module_name].get("data", {})
    
    # Input fields linked to temporary save
    field_1 = st.text_input("Data Point A", value=existing_data.get("point_a", ""))
    
    # "Save Progress" Logic
    if st.button("Save Draft"):
        st.session_state.master_data[module_name]["data"] = {"point_a": field_1}
        st.session_state.master_data[module_name]["status"] = "In Progress"
        save_data(st.session_state.master_data)
        st.success("Draft Saved Locally!")

    if st.button("Final Submit"):
        st.session_state.master_data[module_name]["status"] = "Submitted"
        save_data(st.session_state.master_data)
        st.session_state.page = "Home"
        st.rerun()

# ---------------------------------------------------------
# ROUTER
# ---------------------------------------------------------
if 'page' not in st.session_state:
    st.session_state.page = "Home"

if st.session_state.page == "Home":
    home_page()
else:
    module_template(st.session_state.page)
