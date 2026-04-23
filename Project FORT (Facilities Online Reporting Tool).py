import streamlit as st
import uuid
import pandas as pd
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CORE CONFIG ---
st.set_page_config(
    page_title="Project FORT", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CSS ENGINE (Strictly Individualized) ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #0E1117; color: #C9D1D9; }}
    .section-header-strat {{
        background-color: #1A365D; padding: 15px; border-radius: 10px 10px 0 0;
        text-align: center; border-bottom: 2px solid #1F6FEB; margin-top: 25px;
    }}
    .section-header-core {{
        background-color: #7B341E; padding: 15px; border-radius: 10px 10px 0 0;
        text-align: center; border-bottom: 2px solid #F56565; margin-top: 25px;
    }}
    div[data-testid="stExpander"] {{
        background-color: #161B22 !important; border: 1px solid #30363D !important;
        border-radius: 8px !important; margin-bottom: 15px;
    }}
    div[data-testid="stExpander"] div[role="region"] {{
        background-color: #0D1117 !important; padding: 30px !important;
    }}
    button[kind="primary"] {{ background-color: #059669 !important; color: white !important; font-weight: bold !important; height: 3.8em; }}
    button[kind="secondary"] {{ background-color: #D97706 !important; color: white !important; font-weight: bold !important; height: 3.8em; }}
</style>
""", unsafe_allow_html=True)

# --- 3. PERSISTENCE HELPERS ---

def get_previous_entry(module_name="Mod1"):
    """Fetches existing data for the logged-in user."""
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
        user_id = str(st.session_state.user_id)
        if "User_ID" in df.columns:
            user_data = df[df["User_ID"].astype(str) == user_id]
            if not user_data.empty:
                return user_data.iloc[-1].to_dict() # Get most recent entry
        return {}
    except:
        return {}

def clean_pct(input_str):
    try:
        if not input_str: return 0.0
        return float(str(input_str).replace('%', '').strip())
    except: return 0.0

def score_calc(n, d, label):
    val = (n / d * 100) if d > 0 else 0
    st.markdown(f"📈 **{label} Performance:** `{val:.2f}%`")
    return val

def submit_module_data(res_data, module_name="Mod1"):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
        u = st.session_state.user_info
        new_record = {
            "User_ID": st.session_state.user_id,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Hospital": u["hosp"], "Encoder": u["user"]
        }
        new_record.update(res_data)
        if "User_ID" in df.columns:
            df = df[df["User_ID"].astype(str) != str(st.session_state.user_id)]
        updated_df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet=module_name, data=updated_df)
        st.session_state.expand_all = False
        st.toast("Data successfully synced to Google Sheets!", icon="✅")
        return True
    except Exception as e:
        st.error(f"Sync error: {e}"); return False

# --- 4. MODULE 1: INDIVIDUALIZED & PERSISTENT ---

def module_scorecard():
    if "expand_all" not in st.session_state: st.session_state.expand_all = True
    is_exp = st.session_state.expand_all

    # LOAD PREVIOUS DATA
    prev = get_previous_entry("Mod1")
    if prev: st.success(f"📌 Welcome back. Loading your last saved data from {prev.get('Timestamp', 'N/A')}")

    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
        dd.columns = dd.columns.str.strip()
    except: st.error("Missing Data Dictionary."); return

    # --- STRATEGIC ---
    st.markdown('<div class="section-header-strat"><h2>📊 STRATEGIC PERFORMANCE INDICATORS</h2></div>', unsafe_allow_html=True)
    
    with st.expander("🔹 SI 1: % Functionality of PHU", expanded=is_exp):
        val1 = str(prev.get("SI1", "0%"))
        s1 = clean_pct(st.text_input("Percentage", value=val1, key="si1"))
        
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)", expanded=is_exp):
        val2 = str(prev.get("SI2", "0%"))
        s2 = clean_pct(st.text_input("GVA Score", value=val2, key="si2"))

    with st.expander("🔹 SI 3: Capital Formation", expanded=is_exp):
        cat_opts = list(dd["Indicator 3, DD1"].dropna().unique())
        cat_idx = cat_opts.index(prev["SI3_Cat"]) if prev.get("SI3_Cat") in cat_opts else 0
        cat = st.selectbox("Category", cat_opts, index=cat_idx, key="s3c")
        
        src_opts = list(dd["Indicator 3, DD2"].dropna().unique())
        src_idx = src_opts.index(prev["SI3_Src"]) if prev.get("SI3_Src") in src_opts else 0
        src = st.selectbox("Fund Source", src_opts, index=src_idx, key="s3f")
        
        stat_col = "Indicator 3, DD3.a" if "Infrastructure" in str(cat) else "Indicator 3, DD3.b"
        stat_opts = list(dd[stat_col].dropna().unique())
        stat_idx = stat_opts.index(prev["SI3_Stat"]) if prev.get("SI3_Stat") in stat_opts else 0
        stat = st.selectbox("Status", stat_opts, index=stat_idx, key="s3s")

    with st.expander("🔹 SI 4: ISO 9001:2015 Accreditation", expanded=is_exp):
        s4_opts = list(dd["Indicator 4, DD1"].dropna().unique())
        s4_idx = s4_opts.index(prev["SI4"]) if prev.get("SI4") in s4_opts else 0
        s4 = st.selectbox("ISO Status", s4_opts, index=s4_idx, key="s4")

    with st.expander("🔹 SI 5: PGS Accreditation Status", expanded=is_exp):
        s5_opts = list(dd["Indicator 5, DD2"].dropna().unique())
        s5_idx = s5_opts.index(prev["SI5"]) if prev.get("SI5") in s5_opts else 0
        s5 = st.selectbox("PGS Status", s5_opts, index=s5_idx, key="s5")

    with st.expander("🔹 SI 6: Functional Specialty Centers", expanded=is_exp):
        s6n = st.number_input("Functional Centers", value=int(float(prev.get("SI6_N", 0))), key="s6n")
        s6d = st.number_input("Target Centers", value=int(float(prev.get("SI6_D", 1))), key="s6d")
        s6v = score_calc(s6n, s6d, "SI 6")

    with st.expander("🔹 SI 7: Zero Co-Payment Patients", expanded=is_exp):
        s7n = st.number_input("Zero Co-Pay Pts", value=int(float(prev.get("SI7_N", 0))), key="s7n")
        s7d = st.number_input("Total Basic Pts", value=int(float(prev.get("SI7_D", 1))), key="s7d")
        s7v = score_calc(s7n, s7d, "SI 7")

    with st.expander("🔹 SI 8: Paperless EMR Areas", expanded=is_exp):
        s8n = st.number_input("Paperless Areas", value=int(float(prev.get("SI8_N", 0))), key="s8n")
        s8d = st.number_input("Total Areas", value=int(float(prev.get("SI8_D", 1))), key="s8d")
        s8v = score_calc(s8n, s8d, "SI 8")

    # --- CORE ---
    st.markdown('<div class="section-header-core"><h2>🎯 CORE QUALITY INDICATORS</h2></div>', unsafe_allow_html=True)

    with st.expander("🔸 CI 1: ER Turnaround Time (<4 hrs)", expanded=is_exp):
        ci1n = st.number_input("ER <4h", value=int(float(prev.get("CI1_N", 0))), key="c1n")
        ci1d = st.number_input("Total ER", value=int(float(prev.get("CI1_D", 1))), key="c1d")
        ci1v = score_calc(ci1n, ci1d, "ER TAT")

    with st.expander("🔸 CI 2: Discharge Turnaround (<6 hrs)", expanded=is_exp):
        ci2n = st.number_input("Disch <6h", value=int(float(prev.get("CI2_N", 0))), key="c2n")
        ci2d = st.number_input("Total Disch", value=int(float(prev.get("CI2_D", 1))), key="c2d")
        ci2v = score_calc(ci2n, ci2d, "Discharge TAT")

    with st.expander("🔸 CI 3: Lab Result Turnaround (<5 hrs)", expanded=is_exp):
        ci3n = st.number_input("Lab <5h", value=int(float(prev.get("CI3_N", 0))), key="c3n")
        ci3d = st.number_input("Total Lab", value=int(float(prev.get("CI3_D", 1))), key="c3d")
        ci3v = score_calc(ci3n, ci3d, "Lab TAT")

    with st.expander("🔸 CI 4: Healthcare Associated Infection Rate", expanded=is_exp):
        ci4n = st.number_input("HAI Cases", value=int(float(prev.get("CI4_N", 0))), key="c4n")
        ci4d = st.number_input("Total D/D >48h", value=int(float(prev.get("CI4_D", 1))), key="c4d")
        ci4v = score_calc(ci4n, ci4d, "HAI Rate")

    with st.expander("🔸 CI 5: Client Experience Survey", expanded=is_exp):
        ci5n = st.number_input("Outstanding", value=int(float(prev.get("CI5_N", 0))), key="c5n")
        ci5d = st.number_input("Total Respondents", value=int(float(prev.get("CI5_D", 1))), key="c5d")
        ci5v = score_calc(ci5n, ci5d, "Survey")

    with st.expander("🔸 CI 6: Disbursement Rate", expanded=is_exp):
        ci6n = st.number_input("Disbursed", value=float(prev.get("CI6_N", 0.0)), key="c6n")
        ci6d = st.number_input("Allocated", value=float(prev.get("CI6_D", 1.0)), key="c6d")
        ci6v = score_calc(ci6n, ci6d, "Disbursement")

    st.divider()
    h_name = st.text_input("Head Name", value=prev.get("Head_Name", ""))
    h_pos = st.text_input("Designation", value=prev.get("Head_Pos", ""))

    res = {
        "SI1": s1, "SI2": s2, "SI3_Cat": cat, "SI3_Src": src, "SI3_Stat": stat,
        "SI4": s4, "SI5": s5, "SI6": s6v, "SI7": s7v, "SI8": s8v,
        "CI1": ci1v, "CI2": ci2v, "CI3": ci3v, "CI4": ci4v, "CI5": ci5v, "CI6": ci6v,
        "Head_Name": h_name, "Head_Pos": h_pos,
        "SI6_N": s6n, "SI6_D": s6d, "SI7_N": s7n, "SI7_D": s7d, "SI8_N": s8n, "SI8_D": s8d,
        "CI1_N": ci1n, "CI1_D": ci1d, "CI2_N": ci2n, "CI2_D": ci2d, "CI3_N": ci3n, "CI3_D": ci3d,
        "CI4_N": ci4n, "CI4_D": ci4d, "CI5_N": ci5n, "CI5_D": ci5d, "CI6_N": ci6n, "CI6_D": ci6d
    }

    b1, b2 = st.columns(2)
    if b1.button("🖨️ GENERATE REPORT & AUTO-SUBMIT", type="primary", use_container_width=True):
        if submit_module_data(res, "Mod1"): st.session_state.show_print = True; st.rerun()
    if b2.button("💾 SUBMIT DATA ONLY", type="secondary", use_container_width=True):
        if submit_module_data(res, "Mod1"): st.rerun()

    if st.session_state.get("show_print", False):
        if st.button("🏠 DASHBOARD"): del st.session_state.show_print; del st.session_state.current_module; st.rerun()
        generate_print_view(res)

# --- 5. LOGIC & ROUTING ---

def generate_print_view(d):
    u = st.session_state.user_info
    html = f"""<div style="font-family:Arial; padding:30px; background:white; color:black; border:2px solid #333; text-align:center;">
        <h2>2025 HOSPITAL SCORECARD</h2><h3>{u['hosp']}</h3><hr>
        <p>Strategic Score: {d['SI1']:.2f}% | Core Score: {d['CI5']:.2f}%</p>
        <br><b>{d['Head_Name']}</b><br>{d['Head_Pos']}
        <br><br><button onclick="window.print()">Print PDF</button></div>"""
    st.components.v1.html(html, height=600)

def login_screen():
    st.title("🏥 HFDB Portal")
    if "auth_mode" not in st.session_state:
        c1, c2 = st.columns(2)
        if c1.button("🆕 NEW REGISTRATION", use_container_width=True): st.session_state.auth_mode = "new"; st.rerun()
        if c2.button("🔑 LOGIN ID", use_container_width=True, type="primary"): st.session_state.auth_mode = "existing"; st.rerun()
    else:
        if st.button("⬅️ Back"): del st.session_state.auth_mode; st.rerun()
        if st.session_state.auth_mode == "new":
            facilities = conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List")["Facility_Name"].tolist()
            h_name = st.selectbox("Hospital", [""] + sorted(facilities))
            h_level = st.selectbox("Level", ["", "Level 1", "Level 2", "Level 3", "Specialty"])
            u_name = st.text_input("Encoder Name")
            u_pos = st.text_input("Designation")
            if st.button("Create Profile"):
                new_id = f"FORT-{uuid.uuid4().hex[:6].upper()}"
                st.session_state.user_id = new_id
                st.session_state.user_info = {"hosp": h_name, "level": h_level, "user": u_name, "pos": u_pos}
                st.success(f"ID: {new_id}"); time.sleep(1.5); st.rerun()
        elif st.session_state.auth_mode == "existing":
            uid = st.text_input("Enter ID Code")
            if st.button("Access Portal"):
                p = conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
                if uid in p["User_ID"].astype(str).values:
                    r = p[p["User_ID"].astype(str) == uid].iloc[0]
                    st.session_state.user_id, st.session_state.user_info = uid, {"hosp": r["Hospital_Name"], "level": r["Service_Capability"], "user": r["Encoder_Name"], "pos": r["Position"]}
                    st.rerun()

def dashboard():
    u = st.session_state.user_info
    st.title("🏥 Project FORT")
    if st.button("📊 Hospital Scorecard", use_container_width=True):
        st.session_state.current_module = "Mod1"; st.session_state.expand_all = True; st.rerun()
    if st.button("Logout"): st.session_state.clear(); st.rerun()

if "user_id" not in st.session_state: login_screen()
elif "current_module" in st.session_state:
    if st.button("🏠 Home"): del st.session_state.current_module; st.rerun()
    module_scorecard()
else: dashboard()
