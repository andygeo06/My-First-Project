import streamlit as st
import uuid
import pandas as pd
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CORE CONFIG & FIXED DARK THEME ---
st.set_page_config(
    page_title="Project FORT", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CSS ENGINE (Forced Dark Mode & Expander Contrast) ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #0E1117; color: #C9D1D9; }}
    
    .section-header-strat {{
        background-color: #1A365D; padding: 15px; border-radius: 10px 10px 0 0;
        text-align: center; border-bottom: 2px solid #1F6FEB;
    }}
    .section-header-core {{
        background-color: #7B341E; padding: 15px; border-radius: 10px 10px 0 0;
        text-align: center; border-bottom: 2px solid #F56565;
    }}

    div[data-testid="stExpander"] {{
        background-color: #161B22 !important; border: 1px solid #30363D !important;
        border-radius: 8px !important; margin-bottom: 12px;
    }}
    
    div[data-testid="stExpander"] div[role="region"] {{
        background-color: #0D1117 !important; padding: 25px !important;
        border-top: 1px solid #30363D;
    }}

    div.stButton > button {{
        background-color: #21262D; color: white; border: 1px solid #30363D;
        border-radius: 8px; transition: 0.3s; height: 3em;
    }}
    div.stButton > button:hover {{ border-color: #58A6FF; background-color: #30363D; }}
</style>
""", unsafe_allow_html=True)

# --- 3. HELPER FUNCTIONS ---

def clean_pct(input_str):
    try:
        if not input_str: return 0.0
        return float(str(input_str).replace('%', '').strip())
    except ValueError: return 0.0

def score_calc(n, d, label):
    val = (n / d * 100) if d > 0 else 0
    st.markdown(f"📈 **Current {label} Performance:** `{val:.2f}%`")
    return val

def get_all_profiles():
    try: return conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
    except: return pd.DataFrame(columns=["User_ID", "Hospital_Name", "Service_Capability", "Encoder_Name", "Position", "Year"])

# --- 4. MODULE 1: THE FULL SCORECARD ---

def module_scorecard():
    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
        dd.columns = dd.columns.str.strip()
    except:
        st.error("Sheet 'Mod1_DD' not found or headers incorrect.")
        return

    # --- STRATEGIC SECTION ---
    st.markdown('<div class="section-header-strat"><h2>📊 STRATEGIC INDICATORS</h2></div>', unsafe_allow_html=True)
    
    with st.expander("🔹 SI 1: % Functionality of PHU", expanded=True):
        s1 = clean_pct(st.text_input("Percentage (e.g., 95%)", value="0%", key="si1_in"))
        st.caption(f"Captured: **{s1}%**")
        
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)"):
        s2 = clean_pct(st.text_input("GVA Score (e.g., 88%)", value="0%", key="si2_in"))
        st.caption(f"Captured: **{s2}%**")

    with st.expander("🔹 SI 3: Capital Formation"):
        c1, c2 = st.columns(2)
        cat = c1.selectbox("Category", dd["Indicator 3, DD1"].dropna().unique())
        src = c2.selectbox("Fund Source", dd["Indicator 3, DD2"].dropna().unique())
        if "Infrastructure" in str(cat):
            stat = st.selectbox("Status", dd["Indicator 3, DD3.a"].dropna().unique())
        else:
            stat = st.selectbox("Status", dd["Indicator 3, DD3.b"].dropna().unique())

    with st.expander("🔹 SI 4: ISO 9001:2015 Accreditation"):
        c1, c2 = st.columns(2)
        iso1 = c1.selectbox("ISO Status", dd["Indicator 4, DD1"].dropna().unique())
        iso2 = c2.selectbox("Internal Audit", dd["Indicator 4, DD2"].dropna().unique())

    with st.expander("🔹 SI 5: PGS Accreditation Status"):
        c1, c2 = st.columns(2)
        pgs1 = c1.selectbox("2024 PGS Status", dd["Indicator 5, DD1"].dropna().unique())
        pgs2 = c2.selectbox("2025 PGS Status", dd["Indicator 5, DD2"].dropna().unique())

    with st.expander("🔹 SI 6: Functional Specialty Centers"):
        c1, c2 = st.columns(2)
        s6v = score_calc(c1.number_input("Functional Centers", 0, key="s6n"), c2.number_input("Target Centers", 1, key="s6d"), "SI 6")

    with st.expander("🔹 SI 7: Zero Co-Payment Patients"):
        c1, c2 = st.columns(2)
        s7v = score_calc(c1.number_input("Zero Co-Pay Patients", 0, key="s7n"), c2.number_input("Total Basic Patients", 1, key="s7d"), "SI 7")

    with st.expander("🔹 SI 8: Paperless EMR Areas"):
        c1, c2 = st.columns(2)
        s8v = score_calc(c1.number_input("Paperless Areas", 0, key="s8n"), c2.number_input("Expected Areas", 1, key="s8d"), "SI 8")

    # --- CORE SECTION ---
    st.markdown('<div class="section-header-core"><h2>🎯 CORE INDICATORS</h2></div>', unsafe_allow_html=True)

    with st.expander("🔸 CI 1: ER Turnaround Time (<4 hrs)"):
        c1, c2 = st.columns(2)
        ci1v = score_calc(c1.number_input("ER <4h Count", 0, key="ci1n"), c2.number_input("Total ER Patients", 1, key="ci1d"), "ER TAT")

    with st.expander("🔸 CI 2: Discharge Turnaround (<6 hrs)"):
        c1, c2 = st.columns(2)
        ci2v = score_calc(c1.number_input("Discharge <6h Count", 0, key="ci2n"), c2.number_input("Total Discharges", 1, key="ci2d"), "Discharge TAT")

    with st.expander("🔸 CI 3: Lab Result Turnaround (<5 hrs)"):
        c1, c2 = st.columns(2)
        ci3v = score_calc(c1.number_input("Results <5h Count", 0, key="ci3n"), c2.number_input("Total Lab Tests", 1, key="ci3d"), "Lab TAT")

    with st.expander("🔸 CI 4: Healthcare Associated Infection Rate"):
        c1, c2 = st.columns(2)
        ci4v = score_calc(c1.number_input("Total HAI Cases", 0, key="ci4n"), c2.number_input("Discharges/Deaths >48h", 1, key="ci4d"), "HAI Rate")

    with st.expander("🔸 CI 5: Client Experience Survey"):
        c1, c2 = st.columns(2)
        ci5v = score_calc(c1.number_input("Outstanding Ratings", 0, key="ci5n"), c2.number_input("Total Respondents", 1, key="ci5d"), "Survey")

    with st.expander("🔸 CI 6: Disbursement Rate"):
        c1, c2 = st.columns(2)
        ci6v = score_calc(c1.number_input("Total Disbursement", 0.0, key="ci6n"), c2.number_input("Total Allocation", 1.0, key="ci6d"), "Disbursement")

    st.divider()
    c1, c2 = st.columns(2)
    h_name = c1.text_input("Name of Head of Facility:")
    h_pos = c2.text_input("Designation of Head of Facility:")

    if st.button("🖨️ GENERATE OFFICIAL REPORT", type="primary", use_container_width=True):
        res = {
            "s1": s1, "s2": s2, "cat": cat, "stat": stat,
            "ci1": ci1v, "ci2": ci2v, "ci3": ci3v, "ci4": ci4v, "ci5": ci5v, "ci6": ci6v,
            "h_name": h_name, "h_pos": h_pos
        }
        generate_print_view(res)

# --- 5. PRINT ENGINE ---

def generate_print_view(d):
    u = st.session_state.user_info
    html = f"""
    <div style="font-family: Arial; padding: 40px; background: white; color: black; border: 2px solid #333;">
        <center><h1>2025 DOH HOSPITAL SCORECARD</h1><h3>{u['hosp']} — {u['level']}</h3><hr></center>
        <h4>I. STRATEGIC PERFORMANCE</h4>
        <p>PHU: {d['s1']}% | Green Rating: {d['s2']}% | Capital: {d['cat']} ({d['stat']})</p>
        <h4>II. CORE QUALITY INDICATORS</h4>
        <table style="width:100%; border-collapse: collapse;">
            <tr style="background:#eee;"><th>Indicator</th><th>Result</th></tr>
            <tr><td>ER TAT (<4h)</td><td align="right">{d['ci1']:.2f}%</td></tr>
            <tr><td>Discharge TAT (<6h)</td><td align="right">{d['ci2']:.2f}%</td></tr>
            <tr><td>Lab TAT (<5h)</td><td align="right">{d['ci3']:.2f}%</td></tr>
            <tr><td>HAI Rate</td><td align="right">{d['ci4']:.2f}%</td></tr>
            <tr><td>Experience Survey</td><td align="right">{d['ci5']:.2f}%</td></tr>
            <tr><td>Disbursement Rate</td><td align="right">{d['ci6']:.2f}%</td></tr>
        </table>
        <br><br><table style="width:100%; text-align:center;">
            <tr><td>__________________________<br><b>{u['user']}</b><br>{u['pos']}</td>
                <td>__________________________<br><b>{d['h_name']}</b><br>{d['h_pos']}</td></tr>
        </table>
        <br><center><button onclick="window.print()">Print to PDF</button></center>
    </div>"""
    st.components.v1.html(html, height=800, scrolling=True)

# --- 6. ROUTING & DASHBOARD ---

def login_screen():
    st.title("🏥 HFDB Reporting Portal")
    if "auth_mode" not in st.session_state:
        c1, c2 = st.columns(2)
        if c1.button("🆕 NEW USER", use_container_width=True): st.session_state.auth_mode = "new"; st.rerun()
        if c2.button("🔑 EXISTING USER", use_container_width=True, type="primary"): st.session_state.auth_mode = "existing"; st.rerun()
    else:
        if st.button("⬅️ Back"): del st.session_state.auth_mode; st.rerun()
        if st.session_state.auth_mode == "new":
            h_name = st.selectbox("Hospital Name", [""] + sorted(conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List")["Facility_Name"].tolist()))
            h_level = st.selectbox("Level", ["", "Level 1", "Level 2", "Level 3", "Specialty"])
            u_name = st.text_input("Your Name"); u_pos = st.text_input("Your Designation")
            if st.button("Register Profile"):
                new_id = f"FORT-{uuid.uuid4().hex[:6].upper()}"
                st.session_state.user_id = new_id
                st.session_state.user_info = {"hosp": h_name, "level": h_level, "user": u_name, "pos": u_pos}
                st.success(f"Profile Created! ID: {new_id}"); time.sleep(1); st.rerun()
        elif st.session_state.auth_mode == "existing":
            uid = st.text_input("Enter ID Code")
            if st.button("Enter Portal"):
                p = get_all_profiles()
                if uid in p["User_ID"].values:
                    r = p[p["User_ID"] == uid].iloc[0]
                    st.session_state.user_id = uid
                    st.session_state.user_info = {"hosp": r["Hospital_Name"], "level": r["Service_Capability"], "user": r["Encoder_Name"], "pos": r["Position"]}
                    st.rerun()

def dashboard():
    u = st.session_state.user_info
    st.title("🏥 Project FORT Dashboard")
    st.info(f"Facility: **{u['hosp']}** ({u['level']}) | Encoder: **{u['user']}**")
    if st.button("📊 Hospital Scorecard", use_container_width=True):
        st.session_state.current_module = "Mod1"; st.rerun()
    if st.button("Logout"): st.session_state.clear(); st.rerun()

if "user_id" not in st.session_state: login_screen()
elif "current_module" in st.session_state:
    if st.button("🏠 Home"): del st.session_state.current_module; st.rerun()
    module_scorecard()
else: dashboard()
