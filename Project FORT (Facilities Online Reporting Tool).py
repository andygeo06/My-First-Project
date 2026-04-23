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

# --- NEW: SUBMIT & OVERRIDE LOGIC ---
def submit_scorecard_data(res_data):
    """Saves or overrides scorecard data in the Google Sheet"""
    try:
        # 1. Pull current data or create blank df
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Scorecard_Data", ttl=0)
        except:
            df = pd.DataFrame(columns=["User_ID", "Timestamp", "Hospital", "Encoder"])
            
        u = st.session_state.user_info
        
        # 2. Prep the new record
        new_record = {
            "User_ID": st.session_state.user_id,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Hospital": u["hosp"],
            "Encoder": u["user"]
        }
        # Flatten all values from scorecard into the record
        for key, value in res_data.items():
            new_record[key] = value
            
        new_df = pd.DataFrame([new_record])
        
        # 3. Handle Override (Remove old entry if User_ID exists)
        if st.session_state.user_id in df["User_ID"].astype(str).values:
            df = df[df["User_ID"].astype(str) != st.session_state.user_id]
            st.toast("Existing entry found. Overwriting data...", icon="🔄")
            
        # 4. Merge and push back to Google Sheets
        updated_df = pd.concat([df, new_df], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet="Scorecard_Data", data=updated_df)
        st.toast("Data successfully submitted to HFDB!", icon="🚀")
        return True
    except Exception as e:
        st.error(f"Submission failed: {e}")
        return False

# --- 4. MODULE 1: THE FULL SCORECARD ---

def module_scorecard():
    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
        dd.columns = dd.columns.str.strip()
    except:
        st.error("Sheet 'Mod1_DD' not found or headers incorrect.")
        return

    # --- STRATEGIC SECTION ---
    st.markdown('<div class="section-header-strat"><h2>📊 STRATEGIC PERFORMANCE INDICATORS</h2></div>', unsafe_allow_html=True)
    
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
    st.markdown('<div class="section-header-core"><h2>🎯 CORE QUALITY INDICATORS</h2></div>', unsafe_allow_html=True)

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

    # Map all captured values to a dictionary
    res = {
        "SI1": s1, "SI2": s2, "SI3_Cat": cat, "SI3_Src": src, "SI3_Stat": stat,
        "SI4_Status": iso1, "SI4_Audit": iso2, "SI5_24": pgs1, "SI5_25": pgs2,
        "SI6": s6v, "SI7": s7v, "SI8": s8v,
        "CI1": ci1v, "CI2": ci2v, "CI3": ci3v, "CI4": ci4v, "CI5": ci5v, "CI6": ci6v,
        "Head_Name": h_name, "Head_Pos": h_pos
    }

    # --- ACTION BUTTONS (SIDE BY SIDE) ---
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        if st.button("🖨️ GENERATE REPORT & AUTO-SUBMIT", type="primary", use_container_width=True):
            submit_scorecard_data(res)
            st.session_state.show_print = True
            
    with btn_col2:
        if st.button("💾 SUBMIT DATA ONLY", use_container_width=True):
            submit_scorecard_data(res)

    # Display Print Frame if triggered
    if st.session_state.get("show_print", False):
        generate_print_view(res)

# --- 5. PRINT ENGINE (Centered & Sized) ---

def generate_print_view(d):
    u = st.session_state.user_info
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 40px; background: white; color: black; border: 2px solid #333; max-width: 800px; margin: 0 auto;">
        <center>
            <h1 style="margin:0; color:#111;">2025 DOH HOSPITAL SCORECARD</h1>
            <h3 style="margin:5px 0; color:#444;">{u['hosp']} — {u['level']}</h3>
            <hr style="border:1px solid #111;">
        </center>
        
        <br>
        <table style="width: 100%; border-collapse: collapse; text-align: center; margin: 0 auto;">
            <tr style="background-color: #1A365D; color: white;">
                <th colspan="2" style="padding: 10px; border: 1px solid #333;">I. STRATEGIC PERFORMANCE INDICATORS</th>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 8px; border: 1px solid #333; width: 60%;">Indicator</th>
                <th style="padding: 8px; border: 1px solid #333; width: 40%;">Performance / Status</th>
            </tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 1: Functionality of PHU</td><td style="padding: 8px; border: 1px solid #333;">{d['SI1']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 2: Green Viability Assessment</td><td style="padding: 8px; border: 1px solid #333;">{d['SI2']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 3: Capital Formation</td><td style="padding: 8px; border: 1px solid #333;">{d['SI3_Cat']} ({d['SI3_Stat']})</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 4: ISO Accreditation</td><td style="padding: 8px; border: 1px solid #333;">{d['SI4_Status']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 5: PGS Accreditation</td><td style="padding: 8px; border: 1px solid #333;">{d['SI5_25']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 6: Specialty Centers</td><td style="padding: 8px; border: 1px solid #333;">{d['SI6']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 7: Zero Co-Payment</td><td style="padding: 8px; border: 1px solid #333;">{d['SI7']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 8: Paperless EMR</td><td style="padding: 8px; border: 1px solid #333;">{d['SI8']:.2f}%</td></tr>
            
            <tr style="background-color: #7B341E; color: white;">
                <th colspan="2" style="padding: 10px; border: 1px solid #333;">II. CORE QUALITY INDICATORS</th>
            </tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 1: ER TAT (<4h)</td><td style="padding: 8px; border: 1px solid #333;">{d['CI1']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 2: Discharge TAT (<6h)</td><td style="padding: 8px; border: 1px solid #333;">{d['CI2']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 3: Lab TAT (<5h)</td><td style="padding: 8px; border: 1px solid #333;">{d['CI3']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 4: HAI Rate</td><td style="padding: 8px; border: 1px solid #333;">{d['CI4']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 5: Client Experience Survey</td><td style="padding: 8px; border: 1px solid #333;">{d['CI5']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 6: Disbursement Rate</td><td style="padding: 8px; border: 1px solid #333;">{d['CI6']:.2f}%</td></tr>
        </table>
        
        <br><br><br>
        <table style="width:100%; text-align:center;">
            <tr>
                <td>__________________________<br><b>{u['user']}</b><br>{u['pos']}</td>
                <td>__________________________<br><b>{d['Head_Name']}</b><br>{d['Head_Pos']}</td>
            </tr>
        </table>
        
        <br><br>
        <center><button onclick="window.print()" style="padding:12px 25px; background:#1A365D; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print to PDF</button></center>
    </div>"""
    st.components.v1.html(html, height=1000, scrolling=True)

# --- 6. ROUTING & LOGIN ---

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
                if uid in p["User_ID"].astype(str).values:
                    r = p[p["User_ID"].astype(str) == uid].iloc[0]
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
    if st.button("🏠 Home"): 
        if "show_print" in st.session_state: del st.session_state.show_print
        del st.session_state.current_module
        st.rerun()
    module_scorecard()
else: dashboard()
