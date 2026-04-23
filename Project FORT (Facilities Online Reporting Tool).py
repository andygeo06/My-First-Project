import streamlit as st
import uuid
import pandas as pd
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIG & CONNECTION ---
st.set_page_config(page_title="Project FORT", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

COLORS = {
    "main_background": "#0E1117",
    "card_background": "#21262D",
    "card_text": "#C9D1D9",
    "card_hover": "#30363D",
    "new_user_btn": "#1F6FEB",
    "existing_user_btn": "#238636",
    "border_color": "#30363D"
}

# --- 2. DATABASE FUNCTIONS ---

def get_all_profiles():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
        return df
    except:
        return pd.DataFrame(columns=["User_ID", "Hospital_Name", "Service_Capability", "Encoder_Name", "Position", "Year", "Created_At"])

def get_facility_list():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List", ttl=0)
        return sorted(df["Facility_Name"].dropna().unique().tolist())
    except:
        return ["DOH Hospital 1", "DOH Hospital 2"]

def save_new_profile(user_id, h_name, h_level, u_name, pos):
    try:
        existing = get_all_profiles()
        new_row = pd.DataFrame([{
            "User_ID": str(user_id), "Hospital_Name": str(h_name), "Service_Capability": str(h_level),
            "Encoder_Name": str(u_name), "Position": str(pos), "Year": 2026,
            "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        updated_df = pd.concat([existing, new_row], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=updated_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return False

# --- 3. UI: LOGIN & REGISTRATION ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.divider()

    if "auth_mode" not in st.session_state:
        st.subheader("Please choose an option to begin:")
        c1, c2 = st.columns(2)
        if c1.button("🆕\n\nNEW USER\n\nCreate a Profile", use_container_width=True):
            st.session_state.auth_mode = "new"
            st.rerun()
        if c2.button("🔑\n\nEXISTING USER\n\nContinue Work", use_container_width=True, type="primary"):
            st.session_state.auth_mode = "existing"
            st.rerun()
    else:
        if st.button("⬅️ Back"):
            del st.session_state.auth_mode
            st.rerun()

        if st.session_state.auth_mode == "new":
            st.subheader("📝 Register New Submitter Profile")
            h_name = st.selectbox("Select Your Hospital:", options=[""] + get_facility_list())
            h_level = st.selectbox("Service Capability:", options=["", "Level 1", "Level 2", "Level 3", "Specialty Hospital"])
            u_name = st.text_input("Name of Encoder:")
            pos = st.text_input("Official Designation:")
            
            if st.button("🚀 Register & Generate Code", type="primary"):
                if not h_name or not h_level or not u_name or not pos:
                    st.error("All fields required.")
                else:
                    new_id = f"HFDB-2026-{uuid.uuid4().hex[:8].upper()}"
                    if save_new_profile(new_id, h_name, h_level, u_name, pos):
                        st.session_state.generated_id = new_id
                        st.session_state.reg_success = True
                        st.session_state.temp_info = {"hosp": h_name, "level": h_level, "user": u_name, "pos": pos}
                        st.rerun()

            if st.session_state.get("reg_success"):
                st.success("✅ Registered! Save this code:")
                st.code(st.session_state.generated_id)
                if st.button("Enter Dashboard"):
                    st.session_state.user_id = st.session_state.generated_id
                    st.session_state.user_info = st.session_state.temp_info
                    st.rerun()

        elif st.session_state.auth_mode == "existing":
            st.subheader("🔓 Access Your Profile")
            input_id = st.text_input("Enter ID Code:")
            if st.button("Verify & Enter", type="primary"):
                profiles = get_all_profiles()
                if input_id in profiles["User_ID"].astype(str).tolist():
                    row = profiles[profiles["User_ID"] == input_id].iloc[0]
                    st.session_state.user_id = input_id
                    st.session_state.user_info = {
                        "hosp": row["Hospital_Name"], "level": row["Service_Capability"],
                        "user": row["Encoder_Name"], "pos": row["Position"]
                    }
                    st.rerun()
                else:
                    st.error("Invalid Code.")

# --- 4. MODULE 1: SCORECARD ---

def module_scorecard():
    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
        dd.columns = dd.columns.str.strip()
    except:
        st.error("Sheet 'Mod1_DD' not found or headers incorrect.")
        return

    def score_calc(n, d, label):
        val = (n / d * 100) if d > 0 else 0
        st.caption(f"**Calculated {label}: {val:.2f}%**")
        return val

    st.markdown("### 📋 STRATEGIC INDICATORS")
    
    with st.expander("SI 1-3: Functionality, Green, & Capital", expanded=True):
        s1 = st.number_input("SI 1: PHU Functionality (%)", 0.0, 100.0)
        s2 = st.number_input("SI 2: Green Rating (%)", 0.0, 100.0)
        st.divider()
        c1, c2 = st.columns(2)
        cat = c1.selectbox("Category", dd["Indicator 3, DD1"].dropna().unique())
        src = c2.selectbox("Fund Source", dd["Indicator 3, DD2"].dropna().unique())
        if "Infrastructure" in str(cat):
            stat = st.selectbox("State of Completion", dd["Indicator 3, DD3.a"].dropna().unique())
        else:
            stat = st.selectbox("State of Completion", dd["Indicator 3, DD3.b"].dropna().unique())

    with st.expander("SI 4-8: Accreditation & Specialty"):
        c1, c2 = st.columns(2)
        iso = c1.selectbox("ISO Status", dd["Indicator 4, DD1"].dropna().unique())
        aud = c2.selectbox("Internal Audit", dd["Indicator 4, DD2"].dropna().unique())
        pgs24 = c1.selectbox("2024 PGS", dd["Indicator 5, DD1"].dropna().unique())
        pgs25 = c2.selectbox("2025 PGS", dd["Indicator 5, DD2"].dropna().unique())
        st.divider()
        s6n = st.number_input("SI 6: Functional Specialty Centers", 0)
        s6d = st.number_input("SI 6: Target Centers", 1)
        s6_v = score_calc(s6n, s6d, "SI 6")
        s7n = st.number_input("SI 7: Zero Co-Pay Patients", 0)
        s7d = st.number_input("SI 7: Total Patients", 1)
        s7_v = score_calc(s7n, s7d, "SI 7")
        s8n = st.number_input("SI 8: Areas with Paperless EMR", 0)
        s8d = st.number_input("SI 8: Expected Areas", 1)
        s8_v = score_calc(s8n, s8d, "SI 8")

    st.markdown("### 🎯 CORE INDICATORS")
    with st.expander("CI 1-6: Turnaround & Quality"):
        c1, c2 = st.columns(2)
        ci1n = c1.number_input("CI 1: ER <4hrs", 0); ci1d = c1.number_input("CI 1 Total", 1)
        ci1v = score_calc(ci1n, ci1d, "CI 1")
        ci2n = c2.number_input("CI 2: Discharge <6hrs", 0); ci2d = c2.number_input("CI 2 Total", 1)
        ci2v = score_calc(ci2n, ci2d, "CI 2")
        ci5n = st.number_input("CI 5: Outstanding Ratings", 0); ci5d = st.number_input("CI 5 Total", 1)
        ci5v = score_calc(ci5n, ci5d, "CI 5")
        ci6n = st.number_input("CI 6: Disbursement", 0.0); ci6d = st.number_input("CI 6 Total Allocation", 1.0)
        ci6v = score_calc(ci6n, ci6d, "CI 6")

    st.markdown("### ✍️ SIGNATURE")
    c1, c2 = st.columns(2)
    h_head = c1.text_input("Head of Facility Name:")
    h_pos = c2.text_input("Head of Facility Designation:")

    if st.button("🖨️ Print Submission", type="primary"):
        # We pass only what we need for the report
        res = {"si1": s1, "si2": s2, "cat": cat, "stat": stat, "ci1": ci1v, "ci5": ci5v, "ci6": ci6v, "h_head": h_head, "h_pos": h_pos}
        generate_print_view(res)

# --- 5. PRINT & ROUTER ---

def generate_print_view(data):
    u = st.session_state.user_info
    html = f"""
    <div style="font-family: Arial; padding: 20px; background: white; color: black; border: 1px solid #000;">
        <center><h2>2025 DOH HOSPITAL SCORECARD</h2><h3>{u['hosp']} ({u['level']})</h3><hr></center>
        <p><b>PHU Functionality:</b> {data['si1']}% | <b>Green Rating:</b> {data['si2']}%</p>
        <p><b>Capital Formation:</b> {data['cat']} - {data['stat']}</p>
        <p><b>ER TAT (<4h):</b> {data['ci1']:.2f}% | <b>Client Experience:</b> {data['ci5']:.2f}%</p>
        <br><br>
        <table style="width:100%;">
            <tr><td align="center"><b>{u['user']}</b><br>{u['pos']}</td><td align="center"><b>{data['h_head']}</b><br>{data['h_pos']}</td></tr>
        </table>
        <br><button onclick="window.print()">Print PDF</button>
    </div>"""
    st.components.v1.html(html, height=600)

def dashboard():
    u = st.session_state.user_info
    st.title("🏥 Project FORT Dashboard")
    st.info(f"Welcome, **{u.get('user')}** | **{u.get('hosp')}** ({u.get('level', 'N/A')})")
    
    if st.button("📊 Hospital Scorecard", use_container_width=True):
        st.session_state.current_module = "Mod1"
        st.rerun()
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# --- RUNTIME ---
if "user_id" not in st.session_state:
    login_screen()
elif "current_module" in st.session_state:
    if st.button("🏠 Home"):
        del st.session_state.current_module
        st.rerun()
    module_scorecard()
else:
    dashboard()

st.markdown(f"<style>div.stButton > button {{ background-color: {COLORS['card_background']}; color: white; border-radius: 8px; }}</style>", unsafe_allow_html=True)
