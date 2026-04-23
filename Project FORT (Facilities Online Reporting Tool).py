import streamlit as st
import pandas as pd
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CORE CONFIG ---
st.set_page_config(page_title="Project FORT", layout="wide", initial_sidebar_state="collapsed")

# Connection to Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. CSS ENGINE ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #C9D1D9; }
    .section-header-strat { background-color: #1A365D; padding: 15px; border-radius: 10px 10px 0 0; text-align: center; border-bottom: 2px solid #1F6FEB; margin-top: 25px; }
    .section-header-core { background-color: #7B341E; padding: 15px; border-radius: 10px 10px 0 0; text-align: center; border-bottom: 2px solid #F56565; margin-top: 25px; }
    div[data-testid="stExpander"] { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 8px !important; margin-bottom: 15px; }
    div[data-testid="stExpander"] div[role="region"] { background-color: #0D1117 !important; padding: 30px !important; }
    button[kind="primary"] { background-color: #059669 !important; color: white !important; font-weight: bold !important; height: 3.8em; }
    button[kind="secondary"] { background-color: #D97706 !important; color: white !important; font-weight: bold !important; height: 3.8em; }
</style>
""", unsafe_allow_html=True)

# --- 3. GLOBAL HELPERS ---
def safe_read(worksheet_name):
    try: return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
    except: return None

def clean_pct(input_str):
    try: return float(str(input_str).replace('%', '').strip()) if input_str else 0.0
    except: return 0.0

def score_calc(n, d, label):
    val = (n / d * 100) if d > 0 else 0
    st.markdown(f"📈 **{label} Performance:** `{val:.2f}%`")
    return val

def get_previous_entry(module_name="Mod1"):
    df = safe_read(module_name)
    if df is not None and "User_ID" in df.columns:
        user_data = df[df["User_ID"].astype(str) == str(st.session_state.user_id)]
        if not user_data.empty: return user_data.iloc[-1].to_dict()
    return {}

def show_strategic_indicators(prev, dd, is_exp):
    st.markdown('<div class="section-header-strat"><h2>📊 STRATEGIC PERFORMANCE INDICATORS</h2></div>', unsafe_allow_html=True)
    
    with st.expander("🔹 SI 1: % Functionality of PHU", expanded=is_exp):
        s1 = clean_pct(st.text_input("Percentage", value=str(prev.get("SI1", "0%")), key="si1"))
        
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)", expanded=is_exp):
        s2 = clean_pct(st.text_input("GVA Score", value=str(prev.get("SI2", "0%")), key="si2"))

    with st.expander("🔹 SI 3: Capital Formation", expanded=is_exp):
        c_opts = list(dd["Indicator 3, DD1"].dropna().unique()) if dd is not None else ["Infrastructure"]
        cat = st.selectbox("Category", c_opts, index=c_opts.index(prev["SI3_Cat"]) if prev.get("SI3_Cat") in c_opts else 0)
        f_opts = list(dd["Indicator 3, DD2"].dropna().unique()) if dd is not None else ["GAA"]
        src = st.selectbox("Fund Source", f_opts, index=f_opts.index(prev["SI3_Src"]) if prev.get("SI3_Src") in f_opts else 0)
        stat_col = "Indicator 3, DD3.a" if "Infrastructure" in str(cat) else "Indicator 3, DD3.b"
        s_opts = list(dd[stat_col].dropna().unique()) if dd is not None else ["Ongoing"]
        stat = st.selectbox("Status", s_opts, index=s_opts.index(prev["SI3_Stat"]) if prev.get("SI3_Stat") in s_opts else 0)

    with st.expander("🔹 SI 4: ISO 9001:2015 Accreditation", expanded=is_exp):
        s4_std = ["Not Certified", "Certified", "Recertified"]
        iso = st.selectbox("ISO Status", s4_std, index=s4_std.index(prev["SI4"]) if prev.get("SI4") in s4_std else 0)

    with st.expander("🔹 SI 5: PGS Accreditation Status", expanded=is_exp):
        s5_std = ["Initiated", "Compliant", "Proficient", "Institutionalized"]
        pgs = st.selectbox("PGS Level", s5_std, index=s5_std.index(prev["SI5"]) if prev.get("SI5") in s5_std else 0)

    with st.expander("🔹 SI 6: Functional Specialty Centers", expanded=is_exp):
        s6n = st.number_input("Functional Centers", value=int(float(prev.get("SI6_N", 0))), key="s6n")
        s6d = st.number_input("Target Centers", value=int(float(prev.get("SI6_D", 1))), key="s6d")
        s6v = score_calc(s6n, s6d, "SI 6")

    with st.expander("🔹 SI 7: Zero Co-Payment Patients", expanded=is_exp):
        s7n = st.number_input("Zero Co-Pay Patients", value=int(float(prev.get("SI7_N", 0))), key="s7n")
        s7d = st.number_input("Total Basic Patients", value=int(float(prev.get("SI7_D", 1))), key="s7d")
        s7v = score_calc(s7n, s7d, "SI 7")

    with st.expander("🔹 SI 8: Paperless EMR Areas", expanded=is_exp):
        s8n = st.number_input("Paperless Clinical Areas", value=int(float(prev.get("SI8_N", 0))), key="s8n")
        s8d = st.number_input("Total Clinical Areas", value=int(float(prev.get("SI8_D", 1))), key="s8d")
        s8v = score_calc(s8n, s8d, "SI 8")

    return [s1, s2, cat, src, stat, iso, pgs, s6v, s7v, s8v, s6n, s6d, s7n, s7d, s8n, s8d]

def show_core_indicators(prev, is_exp):
    st.markdown('<div class="section-header-core"><h2>🎯 CORE QUALITY INDICATORS</h2></div>', unsafe_allow_html=True)

    with st.expander("🔸 CI 1: ER Turnaround Time (<4 hrs)", expanded=is_exp):
        c1n = st.number_input("ER Pts <4h", value=int(float(prev.get("CI1_N", 0))), key="c1n")
        c1d = st.number_input("Total ER Pts", value=int(float(prev.get("CI1_D", 1))), key="c1d")
        c1v = score_calc(c1n, c1d, "CI 1")

    with st.expander("🔸 CI 2: Discharge Turnaround (<6 hrs)", expanded=is_exp):
        c2n = st.number_input("Discharges <6h", value=int(float(prev.get("CI2_N", 0))), key="c2n")
        c2d = st.number_input("Total Discharges", value=int(float(prev.get("CI2_D", 1))), key="c2d")
        c2v = score_calc(c2n, c2d, "CI 2")

    with st.expander("🔸 CI 3: Lab Result Turnaround (<5 hrs)", expanded=is_exp):
        c3n = st.number_input("Results <5h", value=int(float(prev.get("CI3_N", 0))), key="c3n")
        c3d = st.number_input("Total Lab Tests", value=int(float(prev.get("CI3_D", 1))), key="c3d")
        c3v = score_calc(c3n, c3d, "CI 3")

    with st.expander("🔸 CI 4: Healthcare Associated Infection Rate", expanded=is_exp):
        c4n = st.number_input("HAI Cases", value=int(float(prev.get("CI4_N", 0))), key="c4n")
        c4d = st.number_input("D/D >48h", value=int(float(prev.get("CI4_D", 1))), key="c4d")
        c4v = score_calc(c4n, c4d, "CI 4")

    with st.expander("🔸 CI 5: Client Experience Survey", expanded=is_exp):
        c5n = st.number_input("Outstanding Ratings", value=int(float(prev.get("CI5_N", 0))), key="c5n")
        c5d = st.number_input("Total Respondents", value=int(float(prev.get("CI5_D", 1))), key="c5d")
        c5v = score_calc(c5n, c5d, "CI 5")

    with st.expander("🔸 CI 6: Disbursement Rate", expanded=is_exp):
        c6n = st.number_input("Actual Disbursed", value=float(prev.get("CI6_N", 0.0)), key="c6n")
        c6d = st.number_input("Total Allocation", value=float(prev.get("CI6_D", 1.0)), key="c6d")
        c6v = score_calc(c6n, c6d, "CI 6")

    st.divider()
    h_name = st.text_input("Name of Head of Facility", value=prev.get("Head_Name", ""))
    h_pos = st.text_input("Position/Designation", value=prev.get("Head_Pos", ""))
    
    return [c1v, c2v, c3v, c4v, c5v, c6v, h_name, h_pos, c1n, c1d, c2n, c2d, c3n, c3d, c4n, c4d, c5n, c5d, c6n, c6d]

def module_scorecard():
    prev = get_previous_entry("Mod1")
    dd = safe_read("Mod1_DD")
    
    # Run UI Blocks
    s_data = show_strategic_indicators(prev, dd, True)
    c_data = show_core_indicators(prev, True)

    if st.button("💾 SUBMIT TO HFDB PORTAL", type="primary", use_container_width=True):
        res = {
            "User_ID": st.session_state.user_id, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Hospital": st.session_state.user_info["hosp"], "Encoder": st.session_state.user_info["user"],
            "SI1": s_data[0], "SI2": s_data[1], "SI3_Cat": s_data[2], "SI3_Src": s_data[3], "SI3_Stat": s_data[4],
            "SI4": s_data[5], "SI5": s_data[6], "SI6": s_data[7], "SI7": s_data[8], "SI8": s_data[9],
            "CI1": c_data[0], "CI2": c_data[1], "CI3": c_data[2], "CI4": c_data[3], "CI5": c_data[4], "CI6": c_data[5],
            "Head_Name": c_data[6], "Head_Pos": c_data[7],
            "SI6_N": s_data[10], "SI6_D": s_data[11], "SI7_N": s_data[12], "SI7_D": s_data[13], "SI8_N": s_data[14], "SI8_D": s_data[15],
            "CI1_N": c_data[8], "CI1_D": c_data[9], "CI2_N": c_data[10], "CI2_D": c_data[11], "CI3_N": c_data[12], "CI3_D": c_data[13],
            "CI4_N": c_data[14], "CI4_D": c_data[15], "CI5_N": c_data[16], "CI5_D": c_data[17], "CI6_N": c_data[18], "CI6_D": c_data[19]
        }
        
        df = safe_read("Mod1")
        if df is not None:
            df = df[df["User_ID"].astype(str) != str(st.session_state.user_id)]
            new_df = pd.concat([df, pd.DataFrame([res])], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Mod1", data=new_df)
            st.success("Submission Successful!"); time.sleep(1); st.rerun()

def login_screen():
    st.title("🏥 HFDB Portal Login")
    uid = st.text_input("Enter Portal ID")
    if st.button("Access"):
        p = safe_read("User_Profiles")
        if p is not None and uid in p["User_ID"].astype(str).values:
            r = p[p["User_ID"].astype(str) == uid].iloc[0]
            st.session_state.user_id, st.session_state.user_info = uid, {"hosp": r["Hospital_Name"], "user": r["Encoder_Name"]}
            st.rerun()

# --- MAIN ROUTER ---
if "user_id" not in st.session_state: login_screen()
elif "current_module" in st.session_state:
    if st.button("🏠 Home"): del st.session_state.current_module; st.rerun()
    module_scorecard()
else:
    st.title("🏥 Dashboard")
    if st.button("📊 Open Scorecard", use_container_width=True): st.session_state.current_module = "Mod1"; st.rerun()
