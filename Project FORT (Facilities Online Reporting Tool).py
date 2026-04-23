import streamlit as st
import uuid
import pandas as pd
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIG & STYLE PALETTE ---
st.set_page_config(page_title="Project FORT", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# Color Scheme for UI Groups
THEME = {
    "strategic_bg": "#1A365D", # Deep Blue
    "core_bg": "#7B341E",      # Deep Orange
    "card_bg": "#21262D",
    "text": "#C9D1D9"
}

# --- 2. DATABASE HELPERS ---

def get_all_profiles():
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
    except:
        return pd.DataFrame(columns=["User_ID", "Hospital_Name", "Service_Capability", "Encoder_Name", "Position", "Year"])

def get_facility_list():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List", ttl=0)
        return sorted(df["Facility_Name"].dropna().unique().tolist())
    except:
        return ["Facility List Error"]

def get_deadlines():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Config", ttl=0)
        return pd.Series(df.Deadline_Date.values, index=df.Module_Key).to_dict()
    except:
        return {}

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
    except: return False

# --- 3. UI COMPONENTS ---

def section_header(title, color):
    """Creates a beautiful colored divider for section logic."""
    st.markdown(f"""
        <div style="background-color:{color}; padding:15px; border-radius:10px; margin-top:25px; margin-bottom:15px;">
            <h2 style="color:white; margin:0; text-align:center; font-size:1.5rem;">{title}</h2>
        </div>
    """, unsafe_allow_html=True)

def score_calc(n, d, label):
    """Real-time math display."""
    val = (n / d * 100) if d > 0 else 0
    st.markdown(f"📈 **Current {label}:** `{val:.2f}%`")
    return val

# --- 4. MODULE 1: THE SCORECARD ---

# --- [UPDATE: Individual Umbrellas for SI 6, 7, 8] ---

def module_scorecard():
    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
        dd.columns = dd.columns.str.strip()
    except:
        st.error("Missing Mod1_DD worksheet or headers.")
        return

    # --- STRATEGIC SECTION ---
    section_header("📊 STRATEGIC PERFORMANCE INDICATORS", THEME["strategic_bg"])
    
    with st.expander("🔹 SI 1: % Functionality of PHU"):
        s1 = st.number_input("PHU Functionality Percentage", 0.0, 100.0, key="si1")
        
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)"):
        s2 = st.number_input("GVA Percentage Score", 0.0, 100.0, key="si2")

    with st.expander("🔹 SI 3: Capital Formation (Infra/Equip)"):
        c1, c2 = st.columns(2)
        cat = c1.selectbox("Category", dd["Indicator 3, DD1"].dropna().unique())
        src = c2.selectbox("Fund Source", dd["Indicator 3, DD2"].dropna().unique())
        if "Infrastructure" in str(cat):
            stat = st.selectbox("State of Completion", dd["Indicator 3, DD3.a"].dropna().unique())
        else:
            stat = st.selectbox("State of Completion", dd["Indicator 3, DD3.b"].dropna().unique())

    with st.expander("🔹 SI 4: ISO 9001:2015 Accreditation"):
        c1, c2 = st.columns(2)
        iso_s = c1.selectbox("ISO Status", dd["Indicator 4, DD1"].dropna().unique())
        iso_a = c2.selectbox("Internal Quality Audit", dd["Indicator 4, DD2"].dropna().unique())

    with st.expander("🔹 SI 5: PGS Accreditation Status"):
        c1, c2 = st.columns(2)
        p24 = c1.selectbox("2024 PGS Status", dd["Indicator 5, DD1"].dropna().unique())
        p25 = c2.selectbox("2025 PGS Status", dd["Indicator 5, DD2"].dropna().unique())

    # --- NOW FULLY SEPARATED ---
    with st.expander("🔹 SI 6: Functional Specialty Centers"):
        c1, c2 = st.columns(2)
        s6_v = score_calc(c1.number_input("No. of Specialty Centers (Functional)", 0, key="s6n"), 
                          c2.number_input("Total Designated Specialty Centers", 1, key="s6d"), "SI 6")
        
    with st.expander("🔹 SI 7: Zero Co-Payment Patients"):
        c1, c2 = st.columns(2)
        s7_v = score_calc(c1.number_input("No. of Zero Co-Pay Patients", 0, key="s7n"), 
                          c2.number_input("Total Basic Accommodation Patients", 1, key="s7d"), "SI 7")

    with st.expander("🔹 SI 8: Paperless EMR Areas"):
        c1, c2 = st.columns(2)
        s8_v = score_calc(c1.number_input("Areas with Paperless EMR", 0, key="s8n"), 
                          c2.number_input("Total Expected EMR Areas", 1, key="s8d"), "SI 8")

    # --- CORE SECTION ---
    section_header("🎯 CORE QUALITY INDICATORS", THEME["core_bg"])

    with st.expander("🔸 CI 1: ER Turnaround Time (<4 hrs)"):
        c1, c2 = st.columns(2)
        ci1_v = score_calc(c1.number_input("ER Patients <4hrs", 0, key="ci1n"), 
                           c2.number_input("Total ER Patients", 1, key="ci1d"), "ER TAT")

    with st.expander("🔸 CI 2: Discharge Turnaround (<6 hrs)"):
        c1, c2 = st.columns(2)
        ci2_v = score_calc(c1.number_input("Discharged <6hrs", 0, key="ci2n"), 
                           c2.number_input("Total Discharges", 1, key="ci2d"), "Discharge TAT")

    with st.expander("🔸 CI 3: Lab Result Turnaround (<5 hrs)"):
        c1, c2 = st.columns(2)
        ci3_v = score_calc(c1.number_input("Lab Results <5hrs", 0, key="ci3n"), 
                           c2.number_input("Total Lab Tests", 1, key="ci3d"), "Lab TAT")

    with st.expander("🔸 CI 4: Healthcare Associated Infection Rate"):
        c1, c2 = st.columns(2)
        ci4_v = score_calc(c1.number_input("Total HAI Cases", 0, key="ci4n"), 
                           c2.number_input("Total Discharges/Deaths (>48h)", 1, key="ci4d"), "HAI Rate")

    with st.expander("🔸 CI 5: Client Experience Survey"):
        c1, c2 = st.columns(2)
        ci5_v = score_calc(c1.number_input("Outstanding Ratings", 0, key="ci5n"), 
                           c2.number_input("Total Respondents", 1, key="ci5d"), "Survey Score")

    with st.expander("🔸 CI 6: Disbursement Rate"):
        c1, c2 = st.columns(2)
        ci6_v = score_calc(c1.number_input("Total Disbursement", 0.0, key="ci6n"), 
                           c2.number_input("Total Allocation (NCA+NTCA)", 1.0, key="ci6d"), "Disbursement")

    # ... [Rest of the Signature and Print logic remains the same] ...

    # --- VALIDATION & PRINT ---
    section_header("✍️ FINAL CERTIFICATION", "#2D3748")
    c1, c2 = st.columns(2)
    h_name = c1.text_input("Name of Head of Facility:")
    h_pos = c2.text_input("Designation of Head of Facility:")

    if st.button("🖨️ GENERATE OFFICIAL REPORT FOR SIGNING", type="primary", use_container_width=True):
        res = {
            "s1": s1, "s2": s2, "cat": cat, "stat": stat, "src": src,
            "ci1": ci1_v, "ci2": ci2_v, "ci3": ci3_v, "ci4": ci4_v, "ci5": ci5_v, "ci6": ci6_v,
            "h_name": h_name, "h_pos": h_pos
        }
        generate_print_view(res)

# --- 5. PRINT & ROUTING ---

def generate_print_view(d):
    u = st.session_state.user_info
    html = f"""
    <div style="font-family: Arial; padding: 30px; background: white; color: black; border: 3px solid #333;">
        <center>
            <h1 style="margin:0;">2025 DOH HOSPITAL SCORECARD</h1>
            <h3 style="margin:5px 0;">{u['hosp']} — {u['level']}</h3>
            <hr>
        </center>
        <h4>I. STRATEGIC INDICATORS</h4>
        <p>PHU: {d['s1']}% | Green Rating: {d['s2']}%</p>
        <p>Capital: {d['cat']} ({d['src']}) — <b>{d['stat']}</b></p>
        <h4>II. CORE QUALITY INDICATORS</h4>
        <ul>
            <li>ER TAT (<4h): {d['ci1']:.2f}%</li>
            <li>Discharge TAT (<6h): {d['ci2']:.2f}%</li>
            <li>Inpatient Lab (<5h): {d['ci3']:.2f}%</li>
            <li>HAI Rate: {d['ci4']:.2f}%</li>
            <li>Experience Score: {d['ci5']:.2f}%</li>
            <li>Disbursement: {d['ci6']:.2f}%</li>
        </ul>
        <br><br><br>
        <table style="width:100%; text-align:center;">
            <tr>
                <td>__________________________<br><b>{u['user']}</b><br>{u['pos']}</td>
                <td>__________________________<br><b>{d['h_name']}</b><br>{d['h_pos']}</td>
            </tr>
        </table>
        <br><button onclick="window.print()" style="background:#1A365D; color:white; border:none; padding:10px 20px; cursor:pointer;">Confirm & Print PDF</button>
    </div>
    """
    st.components.v1.html(html, height=800, scrolling=True)

def dashboard():
    u = st.session_state.user_info
    deadlines = get_deadlines()
    st.title("🏥 Project FORT Dashboard")
    st.info(f"Logged in as: **{u['user']}** | Facility: **{u['hosp']}** ({u['level']})")
    
    cols = st.columns(3)
    modules = [
        {"key": "Mod1", "name": "Hospital Scorecard", "icon": "📊"},
        {"key": "Mod2", "name": "Financial Data", "icon": "💰"},
        {"key": "Mod3", "name": "Hospital MOOE", "icon": "🏥"}
    ]
    
    for i, m in enumerate(modules):
        due = deadlines.get(m['key'], "TBD")
        with cols[i]:
            if st.button(f"{m['icon']} {m['name']}\n\n📅 Due: {due}\nStatus: ⚪ Pending", key=m['key'], use_container_width=True):
                st.session_state.current_module = m['key']
                st.rerun()
    
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# --- MAIN LOOP ---
if "user_id" not in st.session_state:
    import uuid
    def login_screen_wrapper():
        login_screen() # Call existing login function
    login_screen()
elif "current_module" in st.session_state:
    if st.button("⬅️ Back to Dashboard"):
        del st.session_state.current_module
        st.rerun()
    if st.session_state.current_module == "Mod1":
        module_scorecard()
    else:
        st.warning("This module is under development.")
else:
    dashboard()

# CSS Engine for Card buttons
st.markdown(f"<style>div.stButton > button {{ background-color: #21262D; color: white; border-radius: 10px; height: 120px; }}</style>", unsafe_allow_html=True)
