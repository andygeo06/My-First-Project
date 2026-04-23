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

# --- 2. CSS ENGINE (Custom Button Colors & Forced Dark Mode) ---
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

    /* Expander Styling */
    div[data-testid="stExpander"] {{
        background-color: #161B22 !important; border: 1px solid #30363D !important;
        border-radius: 8px !important; margin-bottom: 12px;
    }}
    div[data-testid="stExpander"] div[role="region"] {{
        background-color: #0D1117 !important; padding: 25px !important;
    }}

    /* --- CUSTOM BUTTON COLORS --- */
    /* Emerald Green for PRIMARY (Generate & Submit) */
    button[kind="primary"] {{
        background-color: #059669 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }}
    
    /* Amber/Orange for SECONDARY (Submit Only) */
    button[kind="secondary"] {{
        background-color: #D97706 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }}

    button:hover {{
        opacity: 0.8 !important;
        transition: 0.3s;
    }}
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

def submit_module_data(res_data, module_name="Mod1"):
    try:
        try: df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
        except: df = pd.DataFrame(columns=["User_ID", "Timestamp", "Hospital", "Encoder"])
            
        u = st.session_state.user_info
        new_record = {
            "User_ID": st.session_state.user_id,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Hospital": u["hosp"],
            "Encoder": u["user"]
        }
        new_record.update(res_data)
        new_df = pd.DataFrame([new_record])
        
        if "User_ID" in df.columns:
            df = df[df["User_ID"].astype(str) != str(st.session_state.user_id)]
            
        updated_df = pd.concat([df, new_df], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet=module_name, data=updated_df)
        
        # Trigger the "Collapse" effect
        st.session_state.expand_all = False
        st.toast(f"Data successfully synced to {module_name}!", icon="✅")
        return True
    except Exception as e:
        st.error(f"Submission failed: {e}")
        return False

# --- 4. MODULE 1: SCORECARD ---

def module_scorecard():
    # Initialize Expander state if not set
    if "expand_all" not in st.session_state:
        st.session_state.expand_all = True

    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
        dd.columns = dd.columns.str.strip()
    except:
        st.error("Sheet 'Mod1_DD' not found.")
        return

    # Use session state to control expander visibility
    is_exp = st.session_state.expand_all

    st.markdown('<div class="section-header-strat"><h2>📊 STRATEGIC PERFORMANCE INDICATORS</h2></div>', unsafe_allow_html=True)
    
    with st.expander("🔹 SI 1: % Functionality of PHU", expanded=is_exp):
        s1 = clean_pct(st.text_input("Percentage (e.g., 95%)", value="0%", key="si1_in"))
        st.caption(f"Captured: **{s1}%**")
        
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)", expanded=is_exp):
        s2 = clean_pct(st.text_input("GVA Score (e.g., 88%)", value="0%", key="si2_in"))
        st.caption(f"Captured: **{s2}%**")

    with st.expander("🔹 SI 3: Capital Formation", expanded=is_exp):
        c1, c2 = st.columns(2)
        cat = c1.selectbox("Category", dd["Indicator 3, DD1"].dropna().unique())
        src = c2.selectbox("Fund Source", dd["Indicator 3, DD2"].dropna().unique())
        stat = st.selectbox("Status", dd["Indicator 3, DD3.a"].dropna().unique() if "Infrastructure" in str(cat) else dd["Indicator 3, DD3.b"].dropna().unique())

    with st.expander("🔹 SI 4 & 5: ISO & PGS Status", expanded=is_exp):
        c1, c2 = st.columns(2)
        iso1 = c1.selectbox("ISO Status", dd["Indicator 4, DD1"].dropna().unique())
        pgs2 = c2.selectbox("PGS Status", dd["Indicator 5, DD2"].dropna().unique())

    with st.expander("🔹 SI 6, 7, 8: Quantitative Metrics", expanded=is_exp):
        col1, col2, col3 = st.columns(3)
        s6v = score_calc(col1.number_input("Functional Centers", 0, key="s6n"), col1.number_input("Target Centers", 1, key="s6d"), "SI 6")
        s7v = score_calc(col2.number_input("Zero Co-Pay Pts", 0, key="s7n"), col2.number_input("Total Pts", 1, key="s7d"), "SI 7")
        s8v = score_calc(col3.number_input("Paperless Areas", 0, key="s8n"), col3.number_input("Expected Areas", 1, key="s8d"), "SI 8")

    st.markdown('<div class="section-header-core"><h2>🎯 CORE QUALITY INDICATORS</h2></div>', unsafe_allow_html=True)

    with st.expander("🔸 CI 1 & 2: Turnaround Times", expanded=is_exp):
        c1, c2 = st.columns(2)
        ci1v = score_calc(c1.number_input("ER <4h Count", 0, key="ci1n"), c1.number_input("Total ER Pts", 1, key="ci1d"), "ER TAT")
        ci2v = score_calc(c2.number_input("Discharge <6h", 0, key="ci2n"), c2.number_input("Total Discharges", 1, key="ci2d"), "Discharge")

    with st.expander("🔸 CI 3, 4, 5, 6: Lab, HAI, Survey, Disbursement", expanded=is_exp):
        c1, c2 = st.columns(2)
        ci3v = score_calc(c1.number_input("Lab <5h", 0, key="ci3n"), c1.number_input("Total Lab", 1, key="ci3d"), "Lab")
        ci4v = score_calc(c2.number_input("HAI Cases", 0, key="ci4n"), c2.number_input("HAI Denom", 1, key="ci4d"), "HAI")
        ci5v = score_calc(c1.number_input("Outstanding Survey", 0, key="ci5n"), c1.number_input("Total Survey", 1, key="ci5d"), "Survey")
        ci6v = score_calc(c2.number_input("Disbursement", 0.0, key="ci6n"), c2.number_input("Allocation", 1.0, key="ci6d"), "Budget")

    st.divider()
    c1, c2 = st.columns(2)
    h_name = c1.text_input("Head of Facility Name:")
    h_pos = c2.text_input("Head of Facility Position:")

    res = {
        "SI1": s1, "SI2": s2, "SI3_Cat": cat, "SI3_Stat": stat, "SI4": iso1, "SI5": pgs2,
        "SI6": s6v, "SI7": s7v, "SI8": s8v, "CI1": ci1v, "CI2": ci2v, "CI3": ci3v, "CI4": ci4v, "CI5": ci5v, "CI6": ci6v,
        "Head_Name": h_name, "Head_Pos": h_pos
    }

    # --- ACTION BUTTONS ---
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        if st.button("🖨️ GENERATE REPORT & AUTO-SUBMIT", type="primary", use_container_width=True):
            submit_module_data(res, "Mod1")
            st.session_state.show_print = True
            st.rerun() # Forces the expanders to collapse immediately
            
    with btn_col2:
        if st.button("💾 SUBMIT DATA ONLY", type="secondary", use_container_width=True):
            submit_module_data(res, "Mod1")
            st.rerun()

    # If already submitted/printed, show navigation and report
    if st.session_state.get("show_print", False):
        if st.button("🏠 RETURN TO DASHBOARD", use_container_width=True):
            st.session_state.expand_all = True
            del st.session_state.show_print
            del st.session_state.current_module
            st.rerun()
        generate_print_view(res)

# --- 5. PRINT & ROUTING --- (Kept standard for speed)
def generate_print_view(d):
    u = st.session_state.user_info
    html = f"""<div style="font-family:Arial; padding:40px; background:white; color:black; border:2px solid #333; max-width:800px; margin:0 auto; text-align:center;">
        <h2>2025 DOH HOSPITAL SCORECARD</h2><h3>{u['hosp']}</h3><hr>
        <table style="width:100%; border-collapse:collapse; margin-top:20px;">
            <tr style="background:#1A365D; color:white;"><th colspan="2">OFFICIAL RESULTS</th></tr>
            <tr><td>PHU Functionality</td><td>{d['SI1']:.2f}%</td></tr>
            <tr><td>Green Viability</td><td>{d['SI2']:.2f}%</td></tr>
            <tr><td>ER Turnaround</td><td>{d['CI1']:.2f}%</td></tr>
            <tr><td>Client Experience</td><td>{d['CI5']:.2f}%</td></tr>
            <tr><td>Disbursement Rate</td><td>{d['CI6']:.2f}%</td></tr>
        </table>
        <br><br><b>{d['Head_Name']}</b><br>{d['Head_Pos']}<br><br>
        <button onclick="window.print()" style="padding:10px 20px; background:#059669; color:white; border:none; border-radius:5px;">Confirm & Print to PDF</button>
    </div>"""
    st.components.v1.html(html, height=800, scrolling=True)

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
                st.session_state.user_id, st.session_state.user_info = new_id, {"hosp": h_name, "level": h_level, "user": u_name, "pos": u_pos}
                st.success(f"Profile Created! ID: {new_id}"); time.sleep(1); st.rerun()
        elif st.session_state.auth_mode == "existing":
            uid = st.text_input("Enter ID Code")
            if st.button("Enter Portal"):
                p = get_all_profiles()
                if uid in p["User_ID"].astype(str).values:
                    r = p[p["User_ID"].astype(str) == uid].iloc[0]
                    st.session_state.user_id, st.session_state.user_info = uid, {"hosp": r["Hospital_Name"], "level": r["Service_Capability"], "user": r["Encoder_Name"], "pos": r["Position"]}
                    st.rerun()

def dashboard():
    u = st.session_state.user_info
    st.title("🏥 Project FORT Dashboard")
    st.info(f"Facility: **{u['hosp']}** ({u['level']}) | Encoder: **{u['user']}**")
    if st.button("📊 Hospital Scorecard", use_container_width=True):
        st.session_state.current_module = "Mod1"
        st.session_state.expand_all = True # Ensure open when entering
        st.rerun()
    if st.button("Logout"): st.session_state.clear(); st.rerun()

if "user_id" not in st.session_state: login_screen()
elif "current_module" in st.session_state:
    if st.button("🏠 Home"): 
        if "show_print" in st.session_state: del st.session_state.show_print
        st.session_state.expand_all = True
        del st.session_state.current_module; st.rerun()
    module_scorecard()
else: dashboard()
