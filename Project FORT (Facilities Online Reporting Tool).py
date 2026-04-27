import streamlit as st
import pandas as pd
import time
import string
import random
import uuid
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CORE CONFIG & COMPACT THEME ---
st.set_page_config(
    page_title="Project FORT", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. PREMIUM COMPACT CSS ENGINE (SILVER BULLET) ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #0E1117; color: #C9D1D9; }}
    .block-container {{ padding-top: 2.5rem !important; padding-bottom: 2.5rem !important; }}
    
    .sticky-header {{
        position: -webkit-sticky; position: sticky; top: 2.8rem;
        background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(10px);
        padding: 12px 20px; border-radius: 8px; border: 1px solid #3B82F6;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); z-index: 9999; margin-bottom: 25px; text-align: center;
    }}
    .sticky-title {{ margin: 0; color: #F8FAFC; font-size: 1.3rem; font-weight: bold; }}
    .sticky-sub {{ margin: 0; color: #94A3B8; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}

    .section-header-strat {{ background-color: #1A365D; padding: 10px; border-radius: 8px 8px 0 0; text-align: center; border-bottom: 3px solid #3B82F6; margin-bottom: 10px; }}
    .section-header-core {{ background-color: #7B341E; padding: 10px; border-radius: 8px 8px 0 0; text-align: center; border-bottom: 3px solid #EF4444; margin-bottom: 10px; }}
    .section-header-green {{ background-color: #064E3B; padding: 10px; border-radius: 8px 8px 0 0; text-align: center; border-bottom: 3px solid #10B981; margin-bottom: 10px; }}

    div[data-testid="stExpander"] {{ background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 6px !important; margin-bottom: 8px; transition: 0.3s; }}
    div[data-testid="stExpander"]:hover {{ border-color: #58A6FF !important; }}
    div[data-testid="stExpander"] div[role="region"] {{ background-color: #0D1117 !important; padding: 15px !important; border-top: 1px solid #30363D; }}

    div.element-container:has(.marker) {{ display: none !important; }}
    div.element-container:has(.marker-green) + div.element-container button {{ background-color: #15803d !important; color: white !important; border: 1px solid #22c55e !important; font-weight: bold !important; height: 3em !important; width: 100% !important; transition: 0.3s !important; }}
    div.element-container:has(.marker-green) + div.element-container button:hover {{ background-color: #166534 !important; border-color: #FFFFFF !important; }}
    div.element-container:has(.marker-blue) + div.element-container button {{ background-color: #1A365D !important; color: white !important; border: 1px solid #3B82F6 !important; font-weight: bold !important; height: 3em !important; width: 100% !important; transition: 0.3s !important; }}
    div.element-container:has(.marker-blue) + div.element-container button:hover {{ background-color: #2563EB !important; border-color: #FFFFFF !important; }}
    div.element-container:has(.marker-red) + div.element-container button {{ background-color: #dc2626 !important; color: white !important; border: 1px solid #ef4444 !important; font-weight: bold !important; height: 3em !important; width: 100% !important; transition: 0.3s !important; }}
    div.element-container:has(.marker-red) + div.element-container button:hover {{ background-color: #991b1b !important; border-color: #FFFFFF !important; }}
    div.element-container:has(.marker-amber) + div.element-container button {{ background-color: #d97706 !important; color: white !important; border: 1px solid #f59e0b !important; font-weight: bold !important; height: 3em !important; width: 100% !important; transition: 0.3s !important; }}
    div.element-container:has(.marker-amber) + div.element-container button:hover {{ background-color: #b45309 !important; border-color: #FFFFFF !important; }}
</style>
""", unsafe_allow_html=True)

# --- 3. SMART MEMORY CACHE ---
@st.cache_data(ttl="10m")
def get_static_sheet(sheet_name):
    try: return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
    except: return pd.DataFrame()

def clear_app_memory():
    get_static_sheet.clear()

def generate_custom_id():
    return f"HFDB-2026-{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"

def clean_pct(input_str):
    try: return float(str(input_str).replace('%', '').strip()) if input_str else 0.0
    except ValueError: return 0.0

def score_calc(n, d, label):
    val = (n / d * 100) if d > 0 else 0
    st.markdown(f"📈 **Current {label} Performance:** `{val:.2f}%`")
    return val

def get_idx(opts_series, val):
    opts_list = list(opts_series.dropna().unique())
    return opts_list.index(val) if val in opts_list else 0

def get_module_config(module_name="Mod1"):
    df = get_static_sheet("Config")
    if not df.empty:
        row = df[df.iloc[:, 0] == module_name]
        if not row.empty:
            deadline_str = str(row.iloc[0, 1]).strip()
            if deadline_str.upper() == "NOT SET" or not deadline_str: return "Not Set", False
            return deadline_str, datetime.now() > datetime.strptime(deadline_str, "%Y-%m-%d")
    return "Not Set", False

def get_previous_entry(module_name="Mod1"):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
        if df is not None and "User_ID" in df.columns:
            user_data = df[df["User_ID"].astype(str) == str(st.session_state.user_id)]
            if not user_data.empty: return user_data.fillna("").iloc[-1].to_dict()
    except: pass
    return {}

def submit_module_data(res_data, module_name="Mod1"):
    with st.spinner(f"Syncing data to {module_name}..."):
        try:
            try: df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
            except: df = pd.DataFrame(columns=["User_ID", "Timestamp", "Hospital", "Department", "Encoder"])
            u = st.session_state.user_info
            new_record = {"User_ID": st.session_state.user_id, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Hospital": u["hosp"], "Department": u["dept"], "Encoder": u["user"]}
            new_record.update(res_data)
            if "User_ID" in df.columns: df = df[df["User_ID"].astype(str) != str(st.session_state.user_id)]
            updated_df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet=module_name, data=updated_df)
            st.toast(f"Data successfully synced to {module_name}!", icon="✅")
            return True
        except Exception as e: st.error(f"Submission failed: {e}"); return False

def display_sticky_header():
    u = st.session_state.user_info
    st.markdown(f"""
        <div class="sticky-header">
            <p class="sticky-title">🏥 {u['hosp']}</p>
            <p class="sticky-sub">{u['dept']} Department</p>
        </div>
    """, unsafe_allow_html=True)

def render_upload_section(module_name):
    st.divider()
    st.markdown("### 📤 FINAL STEP: Upload Signed PDF Submission")
    st.info("Please print the documents, secure the required signatures, and upload the scanned PDF.")
    st.link_button("📂 OPEN HFDB GOOGLE DRIVE FOLDER", "https://drive.google.com/drive/", type="primary")
    pdf_link = st.text_input("Paste Google Drive File Link Here:", placeholder="https://drive.google.com/file/d/...")
    if st.button("💾 Save Drive Link", type="secondary", key=f"btn_save_link_{module_name}"):
        if pdf_link:
            try:
                df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
                mask = df["User_ID"].astype(str) == str(st.session_state.user_id)
                if mask.any():
                    df.loc[mask, "Scanned_PDF"] = pdf_link
                    conn.update(spreadsheet=SHEET_URL, worksheet=module_name, data=df)
                    st.success("✅ PDF Link securely encoded to database!")
            except Exception as e: st.error(f"Failed to attach link: {e}")

# --- UNIVERSAL MODULAR PRINT ENGINE ---
def render_modular_print(title, content_html):
    """Generates the HTML payload for a specific isolated print section."""
    u = st.session_state.user_info
    html = f"""
    <style>@media print {{ .no-print {{ display: none !important; }} }}</style>
    <div style="font-family: Arial, sans-serif; padding: 40px; background: white; color: black; border: 2px solid #333; max-width: 850px; margin: 0 auto;">
        <center>
            <h2 style="margin:0;">2026 GREEN VIABILITY ASSESSMENT</h2>
            <h4 style="margin:5px 0; color:#444;">{u['hosp']} — {u['dept']}</h4>
            <h3 style="margin:15px 0; padding:8px; background:#064E3B; color:white; border-radius: 5px;">{title}</h3>
            <hr style="border:1px solid #111;">
        </center>
        <div style="margin: 20px 0; font-size: 13px;">
            {content_html}
        </div>
        <br><br><br>
        <table style="width:100%; text-align:center; font-size:14px; margin-top: 40px;">
            <tr>
                <td style="width:50%;">__________________________<br><b>{u['user']}</b><br>{u['pos']}</td>
                <td style="width:50%;">__________________________<br><b>Authorized Signatory</b><br>Head of Facility</td>
            </tr>
            <tr>
                <td style="padding-top:5px; color:#666;">(Signature Over Printed Name)</td>
                <td style="padding-top:5px; color:#666;">(Signature Over Printed Name)</td>
            </tr>
        </table>
        <center><br><button class="no-print" onclick="window.print()" style="padding:12px 25px; background:#222; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print {title}</button></center>
    </div>"""
    st.session_state.isolated_print_html = html
    st.rerun()

# --- 4. MODULE 1: HOSPITAL SCORECARD ---
def module_scorecard():
    display_sticky_header()
    dd = get_static_sheet("Mod1_DD")
    if dd.empty: st.error("Sheet 'Mod1_DD' not found."); return
    dd.columns = dd.columns.str.strip()
    if "staged_data" not in st.session_state or st.session_state.staged_data is None: st.session_state.staged_data = get_previous_entry("Mod1")
    prev = st.session_state.staged_data 
    deadline_str, locked = get_module_config("Mod1")
    if locked: st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is in READ-ONLY mode.")

    st.markdown('<div class="section-header-strat"><h3 style="margin:0;">📊 STRATEGIC PERFORMANCE INDICATORS</h3></div>', unsafe_allow_html=True)
    with st.expander("🔹 Basic Setup: Service Capability", expanded=True):
        lvl_opts = ["Level 1", "Level 2", "Level 3", "Specialty"]
        h_level = st.selectbox("Current Health Facility Service Capability Level:", lvl_opts, index=get_idx(pd.Series(lvl_opts), prev.get("Level")), disabled=locked)
    with st.expander("🔹 SI 1: % Functionality of PHU", expanded=False):
        s1 = clean_pct(st.text_input("Percentage (e.g., 95%)", value=str(prev.get("SI1", "0%")), disabled=locked))
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)", expanded=False):
        s2 = clean_pct(st.text_input("GVA Score (e.g., 88%)", value=str(prev.get("SI2", "0%")), disabled=locked))
    with st.expander("🔹 SI 3: Capital Formation", expanded=False):
        c1, c2 = st.columns(2)
        cat_opts, src_opts = dd["Indicator 3, DD1"], dd["Indicator 3, DD2"]
        cat = c1.selectbox("Category", cat_opts.dropna().unique(), index=get_idx(cat_opts, prev.get("SI3_Cat")), disabled=locked)
        src = c2.selectbox("Fund Source", src_opts.dropna().unique(), index=get_idx(src_opts, prev.get("SI3_Src")), disabled=locked)
        stat_opts = dd["Indicator 3, DD3.a"] if "Infrastructure" in str(cat) else dd["Indicator 3, DD3.b"]
        stat = st.selectbox("Status", stat_opts.dropna().unique(), index=get_idx(stat_opts, prev.get("SI3_Stat")), disabled=locked)
    with st.expander("🔹 SI 4: ISO 9001:2015 Accreditation", expanded=False):
        c1, c2 = st.columns(2)
        iso1 = c1.selectbox("ISO Status", dd["Indicator 4, DD1"].dropna().unique(), index=get_idx(dd["Indicator 4, DD1"], prev.get("SI4_Status")), disabled=locked)
        iso2 = c2.selectbox("Internal Audit", dd["Indicator 4, DD2"].dropna().unique(), index=get_idx(dd["Indicator 4, DD2"], prev.get("SI4_Audit")), disabled=locked)
    with st.expander("🔹 SI 5: PGS Accreditation Status", expanded=False):
        c1, c2 = st.columns(2)
        pgs1 = c1.selectbox("2024 PGS Status", dd["Indicator 5, DD1"].dropna().unique(), index=get_idx(dd["Indicator 5, DD1"], prev.get("SI5_24")), disabled=locked)
        pgs2 = c2.selectbox("2025 PGS Status", dd["Indicator 5, DD2"].dropna().unique(), index=get_idx(dd["Indicator 5, DD2"], prev.get("SI5_25")), disabled=locked)
    with st.expander("🔹 SI 6: Functional Specialty Centers", expanded=False):
        c1, c2 = st.columns(2)
        s6n = c1.number_input("Functional Centers", value=int(float(prev.get("SI6_N", 0) or 0)), disabled=locked)
        s6d = c2.number_input("Target Centers", value=int(float(prev.get("SI6_D", 1) or 1)), disabled=locked)
        s6v = score_calc(s6n, s6d, "SI 6")
    with st.expander("🔹 SI 7: Zero Co-Payment Patients", expanded=False):
        c1, c2 = st.columns(2)
        s7n = c1.number_input("Zero Co-Pay Patients", value=int(float(prev.get("SI7_N", 0) or 0)), disabled=locked)
        s7d = c2.number_input("Total Basic Patients", value=int(float(prev.get("SI7_D", 1) or 1)), disabled=locked)
        s7v = score_calc(s7n, s7d, "SI 7")
    with st.expander("🔹 SI 8: Paperless EMR Areas", expanded=False):
        c1, c2 = st.columns(2)
        s8n = c1.number_input("Paperless Areas", value=int(float(prev.get("SI8_N", 0) or 0)), disabled=locked)
        s8d = c2.number_input("Expected Areas", value=int(float(prev.get("SI8_D", 1) or 1)), disabled=locked)
        s8v = score_calc(s8n, s8d, "SI 8")

    st.markdown('<div class="section-header-core"><h3 style="margin:0;">🎯 CORE QUALITY INDICATORS</h3></div>', unsafe_allow_html=True)
    with st.expander("🔸 CI 1: ER Turnaround Time (<4 hrs)", expanded=False):
        c1, c2 = st.columns(2)
        ci1n = c1.number_input("ER <4h Count", value=int(float(prev.get("CI1_N", 0) or 0)), disabled=locked)
        ci1d = c2.number_input("Total ER Patients", value=int(float(prev.get("CI1_D", 1) or 1)), disabled=locked)
        ci1v = score_calc(ci1n, ci1d, "ER TAT")
    with st.expander("🔸 CI 2: Discharge Turnaround (<6 hrs)", expanded=False):
        c1, c2 = st.columns(2)
        ci2n = c1.number_input("Discharge <6h Count", value=int(float(prev.get("CI2_N", 0) or 0)), disabled=locked)
        ci2d = c2.number_input("Total Discharges", value=int(float(prev.get("CI2_D", 1) or 1)), disabled=locked)
        ci2v = score_calc(ci2n, ci2d, "Discharge TAT")
    with st.expander("🔸 CI 3: Lab Result Turnaround (<5 hrs)", expanded=False):
        c1, c2 = st.columns(2)
        ci3n = c1.number_input("Results <5h Count", value=int(float(prev.get("CI3_N", 0) or 0)), disabled=locked)
        ci3d = c2.number_input("Total Lab Tests", value=int(float(prev.get("CI3_D", 1) or 1)), disabled=locked)
        ci3v = score_calc(ci3n, ci3d, "Lab TAT")
    with st.expander("🔸 CI 4: Healthcare Associated Infection Rate", expanded=False):
        c1, c2 = st.columns(2)
        ci4n = c1.number_input("Total HAI Cases", value=int(float(prev.get("CI4_N", 0) or 0)), disabled=locked)
        ci4d = c2.number_input("Discharges/Deaths >48h", value=int(float(prev.get("CI4_D", 1) or 1)), disabled=locked)
        ci4v = score_calc(ci4n, ci4d, "HAI Rate")
    with st.expander("🔸 CI 5: Client Experience Survey", expanded=False):
        c1, c2 = st.columns(2)
        ci5n = c1.number_input("Outstanding Ratings", value=int(float(prev.get("CI5_N", 0) or 0)), disabled=locked)
        ci5d = c2.number_input("Total Respondents", value=int(float(prev.get("CI5_D", 1) or 1)), disabled=locked)
        ci5v = score_calc(ci5n, ci5d, "Survey")
    with st.expander("🔸 CI 6: Disbursement Rate", expanded=False):
        c1, c2 = st.columns(2)
        ci6n = c1.number_input("Total Disbursement", value=float(prev.get("CI6_N", 0.0) or 0.0), disabled=locked)
        ci6d = c2.number_input("Total Allocation", value=float(prev.get("CI6_D", 1.0) or 1.0), disabled=locked)
        ci6v = score_calc(ci6n, ci6d, "Disbursement")

    st.divider()
    c1, c2 = st.columns(2)
    h_name = c1.text_input("Name of Head of Facility:", value=prev.get("Head_Name", ""), disabled=locked)
    h_pos = c2.text_input("Designation of Head of Facility:", value=prev.get("Head_Pos", ""), disabled=locked)

    res_db = {
        "Level": h_level, "SI1": s1, "SI2": s2, "SI3_Cat": cat, "SI3_Src": src, "SI3_Stat": stat,
        "SI4_Status": iso1, "SI4_Audit": iso2, "SI5_24": pgs1, "SI5_25": pgs2,
        "SI6_N": s6n, "SI6_D": s6d, "SI7_N": s7n, "SI7_D": s7d, "SI8_N": s8n, "SI8_D": s8d,
        "CI1_N": ci1n, "CI1_D": ci1d, "CI2_N": ci2n, "CI2_D": ci2d, "CI3_N": ci3n, "CI3_D": ci3d,
        "CI4_N": ci4n, "CI4_D": ci4d, "CI5_N": ci5n, "CI5_D": ci5d, "CI6_N": ci6n, "CI6_D": ci6d,
        "Head_Name": h_name, "Head_Pos": h_pos
    }
    res_print = res_db.copy()
    res_print.update({"SI6": s6v, "SI7": s7v, "SI8": s8v, "CI1": ci1v, "CI2": ci2v, "CI3": ci3v, "CI4": ci4v, "CI5": ci5v, "CI6": ci6v})

    if not locked:
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🖨️ GENERATE REPORT & AUTO-SUBMIT", type="primary", use_container_width=True):
                if submit_module_data(res_db, "Mod1"):
                    st.session_state.staged_data.update(res_db)
                    st.session_state.show_print = True
                    st.rerun()
        with btn_col2:
            if st.button("💾 SUBMIT DATA ONLY", use_container_width=True):
                if submit_module_data(res_db, "Mod1"):
                    st.session_state.staged_data.update(res_db)
                    st.session_state.show_print = False
                    st.rerun()
    else:
        if st.button("🖨️ PRINT SUBMITTED DATA (READ-ONLY)", type="primary", use_container_width=True):
            st.session_state.show_print = True; st.rerun()

    if st.session_state.get("show_print", False):
        generate_print_view(res_print)
        render_upload_section("Mod1")

# --- 5. MODULE 2: HOSPITAL CENSUS & HCPN ---
def module_census_data():
    display_sticky_header()
    if "staged_data" not in st.session_state or st.session_state.staged_data is None: st.session_state.staged_data = get_previous_entry("Mod2")
    prev = st.session_state.staged_data
    deadline_str, locked = get_module_config("Mod2")
    DRIVE_LINK = "https://drive.google.com/drive/folders/placeholder"
    if locked: st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is in READ-ONLY mode.")

    st.markdown('<div class="section-header-core"><h3 style="margin:0;">📈 MODULE 2: BASIC INFO, CENSUS & HCPN</h3></div>', unsafe_allow_html=True)
    st.header("1️⃣ BASIC INFORMATION")
    with st.expander("Expand to fill out Facility Capability & Bed Capacity", expanded=False):
        h1, h2, h3 = st.columns([5, 2, 2])
        lv_opts = ["Level 1", "Level 2", "Level 3", "Specialty"]
        
        r1_1, r1_2, r1_3 = st.columns([5, 2, 2])
        r1_1.markdown("**Service Capability Level (2026):**")
        lv_26 = r1_2.selectbox("Level 26", lv_opts, index=get_idx(pd.Series(lv_opts), prev.get("LV_26")), disabled=locked, label_visibility="collapsed")
        rm_lv26 = r1_3.text_input("Remarks LV26", value=str(prev.get("RM_LV26", "")), disabled=locked, label_visibility="collapsed")

        r2_1, r2_2, r2_3 = st.columns([5, 2, 2])
        r2_1.markdown("**Target Service Capability Level in 2027:**")
        lv_27 = r2_2.selectbox("Level 27", lv_opts, index=get_idx(pd.Series(lv_opts), prev.get("LV_27")), disabled=locked, label_visibility="collapsed")
        rm_lv27 = r2_3.text_input("Remarks LV27", value=str(prev.get("RM_LV27", "")), disabled=locked, label_visibility="collapsed")

        labels = [("ABC by Licensing (2025):", "ABC_25"), ("Target ABC by Licensing (2026):", "ABC_26"), ("ABC by Law (2025):", "LAW_25"), ("ABC by Law (2026):", "LAW_26")]
        res_beds = {}
        for label, key in labels:
            c1, c2, c3 = st.columns([5, 2, 2])
            c1.markdown(f"**{label}**")
            res_beds[key] = c2.number_input(label, value=int(float(prev.get(key, 0) or 0)), step=1, disabled=locked, label_visibility="collapsed")
            res_beds[f"RM_{key}"] = c3.text_input(f"Remarks {key}", value=str(prev.get(f"RM_{key}", "")), disabled=locked, label_visibility="collapsed")

        r8_1, r8_2, r8_3 = st.columns([5, 2, 2])
        r8_1.markdown("**Target ABC by Licensing in 2027:**")
        abc_27 = r8_2.number_input("ABC 27", value=int(float(prev.get("ABC_27", 0) or 0)), step=1, disabled=locked, label_visibility="collapsed")
        rm_abc27 = r8_3.text_input("Remarks ABC27", value=str(prev.get("RM_ABC27", "")), disabled=locked, label_visibility="collapsed")

        r9_1, r9_2, r9_3 = st.columns([5, 2, 2])
        r9_1.markdown("**Implementing Bed Capacity (IBC) (2025):**")
        ibc_25 = r9_2.number_input("IBC 25", value=int(float(prev.get("IBC_25", 0) or 0)), step=1, disabled=locked, label_visibility="collapsed")
        rm_ibc25 = r9_3.text_input("Remarks IBC25", value=str(prev.get("RM_IBC25", "")), disabled=locked, label_visibility="collapsed")

    st.header("2️⃣ HOSPITAL CENSUS DATA")
    with st.expander("Expand to fill out Census Data", expanded=False):
        census_data = [
            ("Bed Occupancy Rate (BOR) (2025):", "BOR_25", "pct"), ("Average Length of Stay (ALOS) (2025):", "ALOS_25", "float"),
            ("Total Inpatient Days Served (TIDS):", "TIDS_25", "int"), ("Total Number of Inpatients (2025):", "INP_25", "int"),
            ("Total Number of Outpatient Visits:", "OUT_25", "int"), ("Total ER Visits (2025):", "ERV_25", "int")
        ]
        res_census = {}
        for label, key, dtype in census_data:
            c1, c2, c3 = st.columns([5, 2, 2])
            c1.markdown(f"**{label}**")
            if dtype == "pct": res_census[key] = c2.text_input(label, value=str(prev.get(key, "0%")), disabled=locked, label_visibility="collapsed")
            elif dtype == "float": res_census[key] = c2.number_input(label, value=float(prev.get(key, 0.0) or 0.0), step=0.1, disabled=locked, label_visibility="collapsed")
            else: res_census[key] = c2.number_input(label, value=int(float(prev.get(key, 0) or 0)), step=1, disabled=locked, label_visibility="collapsed")
            res_census[f"RM_{key}"] = c3.text_input(f"Remarks {key}", value=str(prev.get(f"RM_{key}", "")), disabled=locked, label_visibility="collapsed")

    st.header("3️⃣ HCPN, BUCAS AND COORDINATES")
    with st.expander("Expand to fill out HCPN & BUCAS Data", expanded=False):
        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("**Based on DC No. 2025-0554, is the hospital identified as Apex or End-Referral Hospital?**")
        apex = c2.selectbox("Apex", ["Yes", "No"], index=get_idx(pd.Series(["Yes", "No"]), prev.get("APEX")), disabled=locked, label_visibility="collapsed")
        rm_apex = c3.text_input("Remarks Apex", value=str(prev.get("RM_APEX", "")), disabled=locked, label_visibility="collapsed")

        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("**If the hospital already has MOA/MOU with a HCPN/province, how many HCPNs are they linked with?**")
        hcpn_count = c2.number_input("HCPN Count", value=int(float(prev.get("HCPN_COUNT", 0) or 0)), step=1, disabled=locked, label_visibility="collapsed")
        rm_hcpn = c3.text_input("Remarks HCPN", value=str(prev.get("RM_HCPN", "")), disabled=locked, label_visibility="collapsed")

        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("**Does the hospital operate a BUCAS Center/s?**")
        bucas = c2.selectbox("BUCAS", ["Yes", "No"], index=get_idx(pd.Series(["Yes", "No"]), prev.get("BUCAS")), disabled=locked, label_visibility="collapsed")
        rm_bucas = c3.text_input("Remarks BUCAS", value=str(prev.get("RM_BUCAS", "")), disabled=locked, label_visibility="collapsed")

        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("**Coordinates of the BUCAS Center (Lat, Long)**")
        coords = c2.text_input("Coords", value=str(prev.get("COORDS", "")), disabled=locked, label_visibility="collapsed")
        rm_coords = c3.text_input("Remarks Coords", value=str(prev.get("RM_COORDS", "")), disabled=locked, label_visibility="collapsed")

    st.divider()
    h_col1, h_col2 = st.columns(2)
    h_name = h_col1.text_input("Name of Head of Facility:", value=str(prev.get("Head_Name", "")), disabled=locked)
    h_pos = h_col2.text_input("Designation of Head of Facility:", value=str(prev.get("Head_Pos", "")), disabled=locked)

    final_data = {
        "LV_26": lv_26, "RM_LV26": rm_lv26, "LV_27": lv_27, "RM_LV27": rm_lv27,
        "ABC_25": res_beds["ABC_25"], "RM_ABC_25": res_beds["RM_ABC_25"], "ABC_26": res_beds["ABC_26"], "RM_ABC_26": res_beds["RM_ABC_26"],
        "LAW_25": res_beds["LAW_25"], "RM_LAW_25": res_beds["RM_LAW_25"], "LAW_26": res_beds["LAW_26"], "RM_LAW_26": res_beds["RM_LAW_26"],
        "ABC_27": abc_27, "RM_ABC27": rm_abc27, "IBC_25": ibc_25, "RM_IBC25": rm_ibc25,
        "APEX": apex, "RM_APEX": rm_apex, "HCPN_COUNT": hcpn_count, "RM_HCPN": rm_hcpn,
        "BUCAS": bucas, "RM_BUCAS": rm_bucas, "COORDS": coords, "RM_COORDS": rm_coords,
        "Head_Name": h_name, "Head_Pos": h_pos
    }
    final_data.update(res_census)

    if not locked:
        btn1, btn2 = st.columns(2)
        if btn1.button("🖨️ GENERATE CENSUS REPORT & AUTO-SUBMIT", type="primary", use_container_width=True):
            if submit_module_data(final_data, "Mod2"):
                st.session_state.staged_data.update(final_data)
                st.session_state.show_print = True
                st.rerun()
        if btn2.button("💾 SAVE PROGRESS ONLY", use_container_width=True):
            if submit_module_data(final_data, "Mod2"):
                st.session_state.staged_data.update(final_data)
                st.success("Progress saved!")
    else:
        if st.button("🖨️ PRINT SUBMITTED DATA (READ-ONLY)", type="primary", use_container_width=True):
            st.session_state.show_print = True; st.rerun()

    if st.session_state.get("show_print", False):
        generate_print_view_mod2(final_data)
        render_upload_section("Mod2")

# --- 6. MODULE 3: GREEN VIABILITY ASSESSMENT (PHASE 2 - DYNAMIC ENGINE & MODULAR PRINT) ---
def get_blank_consumption_grid():
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return pd.DataFrame({
        "Month": months, "Electricity (kWh)": [0.0]*12, "Fuel (L)": [0.0]*12,
        "Water (m3)": [0.0]*12, "General Waste (kg)": [0.0]*12, "Haz Waste (kg)": [0.0]*12
    })

def module_gva():
    display_sticky_header()
    u = st.session_state.user_info
    
    # Block rendering of the main form if we are in Print Isolation Mode
    if st.session_state.get("isolated_print_html"):
        st.components.v1.html(st.session_state.isolated_print_html, height=1200, scrolling=True)
        if st.button("⬅️ Back to Assessment Form", type="primary"):
            del st.session_state.isolated_print_html; st.rerun()
        return

    # Data Fetch & Smart Locks
    mod2_data = get_previous_entry("Mod2")
    prev = get_previous_entry("Mod3")
    
    auto_abc = mod2_data.get("ABC_25", prev.get("ABC", ""))
    auto_coords = mod2_data.get("COORDS", prev.get("Coordinates", ""))
    
    abc_locked = True if str(auto_abc).strip() not in ["", "0", "0.0", "nan"] else False
    coords_locked = True if str(auto_coords).strip() not in ["", "0", "0.0", "nan"] else False
    
    deadline_str, locked = get_module_config("Mod3")
    if locked: st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is READ-ONLY.")

    st.markdown('<div class="section-header-green"><h3 style="margin:0;">🌿 MODULE 3: GREEN VIABILITY ASSESSMENT</h3></div>', unsafe_allow_html=True)
    
    # --- PART 1: GENERAL INFO ---
    st.header("1️⃣ GENERAL INFORMATION")
    with st.expander("Expand to fill General & Geographical Info", expanded=True):
        c1, c2 = st.columns(2)
        c1.text_input("Name of Health Facility:", value=u['hosp'], disabled=True)
        c2.text_input("Service Capability Level:", value=u.get('level', 'Level 1'), disabled=True)
        
        c3, c4 = st.columns(2)
        final_abc = c3.text_input("Authorized Bed Capacity (ABC):", value=auto_abc, disabled=(locked or abc_locked))
        final_coords = c4.text_input("Coordinates (Lat, Long):", value=auto_coords, disabled=(locked or coords_locked))
        
        st.divider()
        st.markdown("**Facility Dimensions & Testing**")
        dim1, dim2 = st.columns(2)
        lot_area = dim1.number_input("Total Lot Area (sq.m):", value=float(prev.get("Lot_Area", 0.0) or 0.0), disabled=locked)
        green_space = dim2.number_input("Green Space Area (sq.m):", value=float(prev.get("Green_Space", 0.0) or 0.0), disabled=locked)
        
        test1, test2 = st.columns(2)
        soil_test = test1.selectbox("Conducted soil testing in premise?", ["No", "Yes"], index=get_idx(pd.Series(["No", "Yes"]), prev.get("Soil_Test")), disabled=locked)
        soil_date = test2.text_input("If yes, when?", value=str(prev.get("Soil_Date", "")), disabled=locked)
        hsi_test = test1.selectbox("Conducted Hospital Safety Index?", ["No", "Yes"], index=get_idx(pd.Series(["No", "Yes"]), prev.get("HSI_Test")), disabled=locked)
        hsi_date = test2.text_input("If yes, date & buildings?", value=str(prev.get("HSI_Date", "")), disabled=locked)

        st.divider()
        st.markdown("**Hazard Susceptibility (Check all that apply)**")
        haz1, haz2, haz3, haz4 = st.columns(4)
        c_coast = haz1.checkbox("Coastal Area", value=bool(prev.get("C_Coast", False)), disabled=locked)
        c_low = haz2.checkbox("Low Lying Area", value=bool(prev.get("C_Low", False)), disabled=locked)
        c_land = haz3.checkbox("Landslide Prone", value=bool(prev.get("C_Land", False)), disabled=locked)
        c_mount = haz4.checkbox("Mountainous Terrain", value=bool(prev.get("C_Mount", False)), disabled=locked)
        
        st.markdown("**Location / Distance in Kilometer/meter**")
        d1, d2, d3 = st.columns(3)
        dist_fault = d1.number_input("Distance from fault line (km):", value=float(prev.get("Dist_Fault", 0.0) or 0.0), disabled=locked)
        dist_volc = d2.number_input("Distance from volcano (km):", value=float(prev.get("Dist_Volc", 0.0) or 0.0), disabled=locked)
        dist_sea = d3.number_input("Distance from sea (km):", value=float(prev.get("Dist_Sea", 0.0) or 0.0), disabled=locked)

        st.divider()
        st.markdown("**Personnel Profiling**")
        p1, p2, p3 = st.columns(3)
        clin_staff = p1.number_input("Clinical Staff Count:", value=int(float(prev.get("Clin_Staff", 0) or 0)), step=1, disabled=locked)
        non_clin = p2.number_input("Non-Clinical Staff Count:", value=int(float(prev.get("Non_Clin_Staff", 0) or 0)), step=1, disabled=locked)
        jan_sec = p3.number_input("Janitorial/Security Count:", value=int(float(prev.get("Jan_Sec_Staff", 0) or 0)), step=1, disabled=locked)
        
        st.divider()
        st.markdown("**Physical Distribution (Dynamic Building List)**")
        if "bldg_df" not in st.session_state:
            st.session_state.bldg_df = pd.DataFrame([{"Building Name": "Main Hospital", "Floor Area (sq.m)": 0.0}])
        bldg_res = st.data_editor(st.session_state.bldg_df, num_rows="dynamic", use_container_width=True, disabled=locked)
        
        # Modular Print for General Info
        st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
        if st.button("🖨️ Print General Information for Signature", use_container_width=True):
            html = f"""
            <table style="width:100%; border-collapse: collapse; font-size: 13px;">
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Facility:</b> {u['hosp']}</td><td style="border: 1px solid #333; padding: 8px;"><b>Level:</b> {u.get('level','Level 1')}</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Lot Area:</b> {lot_area} sq.m</td><td style="border: 1px solid #333; padding: 8px;"><b>Green Space:</b> {green_space} sq.m</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Fault Line Dist:</b> {dist_fault} km</td><td style="border: 1px solid #333; padding: 8px;"><b>Volcano Dist:</b> {dist_volc} km</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Clinical Staff:</b> {clin_staff}</td><td style="border: 1px solid #333; padding: 8px;"><b>Non-Clinical:</b> {non_clin}</td></tr>
            </table>
            """
            render_modular_print("GENERAL INFORMATION", html)

    # --- PART 2: CONSUMPTION DATA ---
    st.header("2️⃣ MULTI-YEAR CONSUMPTION DATA")
    years = [str(y) for y in range(2022, 2029)]
    tabs = st.tabs(years)
    live_consumption = {}
    
    for i, year in enumerate(years):
        with tabs[i]:
            if f"grid_{year}" not in st.session_state: st.session_state[f"grid_{year}"] = get_blank_consumption_grid()
            grid_result = st.data_editor(st.session_state[f"grid_{year}"], hide_index=True, use_container_width=True, disabled=locked)
            live_consumption[year] = grid_result
            
            st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
            if st.button(f"🖨️ Print {year} Consumption for Signature", use_container_width=True, key=f"p_cons_{year}"):
                html = grid_result.to_html(index=False, border=1, classes="my-table", justify="center")
                html = html.replace('class="dataframe my-table"', 'style="width: 100%; border-collapse: collapse; text-align: center;"')
                html = html.replace('<th>', '<th style="background-color: #eee; padding: 8px; border: 1px solid #333;">')
                html = html.replace('<td>', '<td style="padding: 6px; border: 1px solid #333;">')
                render_modular_print(f"{year} CONSUMPTION DATA", html)

    # Calculate CO2e silently for Admin Dashboard save
    factors = {"Electricity (kWh)": 0.79, "Fuel (L)": 3.28, "Water (m3)": 0.28}
    admin_co2e_save = {}
    for year in years:
        df = live_consumption[year]
        total_co2 = (pd.to_numeric(df["Electricity (kWh)"], errors='coerce').fillna(0).sum() * factors["Electricity (kWh)"]) + \
                    (pd.to_numeric(df["Fuel (L)"], errors='coerce').fillna(0).sum() * factors["Fuel (L)"]) + \
                    (pd.to_numeric(df["Water (m3)"], errors='coerce').fillna(0).sum() * factors["Water (m3)"])
        admin_co2e_save[f"CO2e_{year}"] = total_co2

    # --- PART 3: PERFORMANCE STANDARDS (THE DYNAMIC EXCEL MAGIC ENGINE) ---
    st.header("3️⃣ PERFORMANCE STANDARDS")
    st.caption("These questions are synced directly from your Google Sheet!")
    
    gva_answers = {}
    score_summary = []
    perf_df = get_static_sheet("Performance Standards")
    
    if perf_df.empty:
        st.warning("⚠️ Could not find the 'Performance Standards' tab. Add it to see the checklist!")
    else:
        perf_df.columns = perf_df.columns.str.strip()
        if 'CRITERION' in perf_df.columns and 'Ref. #' in perf_df.columns and 'QUESTIONS' in perf_df.columns:
            # Forward-fill to fix merged cells
            perf_df['CRITERION'] = perf_df['CRITERION'].ffill()
            sub_col = 'SUB- CATEGORY' if 'SUB- CATEGORY' in perf_df.columns else 'SUB-CATEGORY' if 'SUB-CATEGORY' in perf_df.columns else None
            if sub_col: perf_df[sub_col] = perf_df[sub_col].ffill()
            
            questions_only = perf_df.dropna(subset=['Ref. #', 'QUESTIONS'])
            categories = questions_only['CRITERION'].unique()
            
            for cat in categories:
                cat_max = 0
                cat_actual = 0
                cat_questions = questions_only[questions_only['CRITERION'] == cat]
                
                with st.expander(f"📌 {cat}", expanded=False):
                    if sub_col:
                        subs = cat_questions[sub_col].unique()
                        for sub in subs:
                            st.markdown(f"<h5 style='color:#3B82F6;'>🔹 {sub}</h5>", unsafe_allow_html=True)
                            sub_qs = cat_questions[cat_questions[sub_col] == sub]
                            
                            for _, row in sub_qs.iterrows():
                                q_ref, q_text = str(row['Ref. #']).strip(), str(row['QUESTIONS']).strip()
                                st.markdown(f"**{q_ref}:** {q_text}")
                                
                                prev_ans = prev.get(f"GVA_{q_ref}", "No (0 pt)")
                                ans = st.radio("Status", ["Yes (1 pt)", "In Progress (0.5 pt)", "No (0 pt)"], index=get_idx(pd.Series(["Yes (1 pt)", "In Progress (0.5 pt)", "No (0 pt)"]), prev_ans), horizontal=True, key=f"rad_{q_ref}", disabled=locked, label_visibility="collapsed")
                                gva_answers[f"GVA_{q_ref}"] = ans
                                
                                cat_max += 1.0
                                if "Yes" in ans: cat_actual += 1.0
                                elif "In Progress" in ans: cat_actual += 0.5
                                st.divider()
                    
                    # Modular Print Button for this specific Criterion
                    st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
                    if st.button(f"🖨️ Print {cat} for Signature", use_container_width=True, key=f"p_cat_{cat}"):
                        html_lines = [f"<h4>{cat}</h4><table style='width:100%; border-collapse: collapse;'><tr><th style='border:1px solid #333; padding:6px; background:#eee;'>Ref</th><th style='border:1px solid #333; padding:6px; background:#eee;'>Question</th><th style='border:1px solid #333; padding:6px; background:#eee;'>Answer</th></tr>"]
                        for _, row in cat_questions.iterrows():
                            ref = str(row['Ref. #']).strip()
                            html_lines.append(f"<tr><td style='border:1px solid #333; padding:6px;'>{ref}</td><td style='border:1px solid #333; padding:6px;'>{row['QUESTIONS']}</td><td style='border:1px solid #333; padding:6px; text-align:center;'><b>{gva_answers[f'GVA_{ref}']}</b></td></tr>")
                        html_lines.append("</table>")
                        render_modular_print(cat, "".join(html_lines))
                
                pct = (cat_actual/cat_max*100) if cat_max > 0 else 0
                score_summary.append({"Performance Indicator": cat, "Max Score": cat_max, "Actual Score": cat_actual, "Percentage": f"{pct:.2f}%"})
            
            # --- THE OVERALL SCORE TABLE ---
            st.markdown("### 🏆 Overall Score Summary")
            score_df = pd.DataFrame(score_summary)
            st.dataframe(score_df, use_container_width=True, hide_index=True)
            
            st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
            if st.button("🖨️ Print OVERALL SCORE TABLE for Signature", use_container_width=True):
                html = score_df.to_html(index=False, border=1, justify="center")
                html = html.replace('class="dataframe"', 'style="width: 100%; border-collapse: collapse; text-align: center; font-size: 14px;"')
                html = html.replace('<th>', '<th style="background-color: #064E3B; color: white; padding: 10px; border: 1px solid #333;">')
                html = html.replace('<td>', '<td style="padding: 8px; border: 1px solid #333;">')
                render_modular_print("OVERALL PERFORMANCE SCORE SUMMARY", html)
        else:
            st.error("⚠️ Ensure your sheet has columns exactly named: 'CRITERION', 'Ref. #', and 'QUESTIONS' on Row 1.")

    # --- PART 4: MASTER UPLOAD BOX ---
    st.header("4️⃣ MASTER EVIDENCE UPLOAD")
    st.info("Upload a single ZIP file or provide a link to a Google Drive folder containing all your MOVs (Memo Orders, Photos, Audits) properly labeled.")
    master_link = st.text_input("Paste Google Drive Folder Link Here:", value=str(prev.get("Master_Drive_Link", "")), placeholder="https://drive.google.com/drive/folders/...", disabled=locked)

    # Combine Data for saving
    final_mod3_data = {
        "ABC": final_abc, "Coordinates": final_coords, "Lot_Area": lot_area, "Green_Space": green_space,
        "Soil_Test": soil_test, "Soil_Date": soil_date, "HSI_Test": hsi_test, "HSI_Date": hsi_date,
        "C_Coast": c_coast, "C_Low": c_low, "C_Land": c_land, "C_Mount": c_mount,
        "Dist_Fault": dist_fault, "Dist_Volc": dist_volc, "Dist_Sea": dist_sea,
        "Clin_Staff": clin_staff, "Non_Clin_Staff": non_clin, "Jan_Sec_Staff": jan_sec,
        "Master_Drive_Link": master_link
    }
    final_mod3_data.update(gva_answers)
    final_mod3_data.update(admin_co2e_save) # Saves the math for the Admin

    if not locked:
        if st.button("💾 SAVE ALL PROGRESS TO DATABASE", use_container_width=True, type="primary"):
            if submit_module_data(final_mod3_data, "Mod3"):
                st.session_state.staged_data.update(final_mod3_data)
                st.success("Progress Saved to Google Sheets!")

# --- 7. ADMIN DATA ANALYSIS MODE ---
def admin_dashboard():
    st.markdown("<h2 style='text-align: center;'>👑 Data Analysis Portal (Admin)</h2>", unsafe_allow_html=True)
    st.info("Welcome to the Admin View. Select a module below to view live aggregated statistics.")
    st.markdown('<div class="marker marker-blue"></div>', unsafe_allow_html=True)
    if st.button("📊 Analyze Module 1: Scorecard Data", use_container_width=True): st.session_state.current_module = "Admin_Mod1"; st.rerun()
    st.markdown('<div class="marker marker-red"></div>', unsafe_allow_html=True)
    if st.button("📈 Analyze Module 2: Census Data", use_container_width=True): st.session_state.current_module = "Admin_Mod2"; st.rerun()
    st.markdown('<div class="marker marker-green"></div>', unsafe_allow_html=True)
    if st.button("🌿 Analyze Module 3: Green Viability Dashboard", use_container_width=True): st.session_state.current_module = "Admin_Mod3"; st.rerun()
    st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

def admin_analysis_view(module_name, title):
    st.markdown(f"<h2>{title}</h2>", unsafe_allow_html=True)
    with st.spinner("Fetching live database..."):
        try: df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl="1m")
        except: df = pd.DataFrame()
        
    if df.empty: st.warning("No data has been submitted yet.")
    else:
        st.metric("Total Submissions", len(df))
        
        # --- Mod 3 Specific: The Live Emissions Charts ---
        if module_name == "Mod3":
            st.markdown("### 🌍 Total Aggregated Carbon Footprint (All Hospitals)")
            co2_cols = [col for col in df.columns if col.startswith("CO2e_")]
            if co2_cols:
                yearly_totals = df[co2_cols].sum().reset_index()
                yearly_totals.columns = ["Year", "Total CO2e (kg)"]
                yearly_totals["Year"] = yearly_totals["Year"].str.replace("CO2e_", "")
                yearly_totals.set_index("Year", inplace=True)
                
                col1, col2 = st.columns([1, 2])
                with col1: st.dataframe(yearly_totals.style.format("{:.2f}"), use_container_width=True)
                with col2: st.bar_chart(yearly_totals)
            else: st.info("No CO2e data has been calculated yet.")
            
        st.markdown("### 🗃️ Raw Data Overview")
        st.dataframe(df, use_container_width=True)
        
    if st.button("⬅️ Back to Admin Dashboard"): del st.session_state.current_module; st.rerun()

# --- 8. PRINT ENGINES (MOD 1 & 2) ---
def generate_print_view(d):
    u = st.session_state.user_info
    html = f"""<style>@media print {{ .no-print {{ display: none !important; }} }}</style>
    <div style="font-family: Arial, sans-serif; padding: 40px; background: white; color: black; border: 2px solid #333; max-width: 800px; margin: 0 auto;">
        <center><h1 style="margin:0; color:#111;">2025 DOH HOSPITAL SCORECARD</h1><h3 style="margin:5px 0; color:#444;">{u['hosp']} — {u['dept']} Department</h3><hr style="border:1px solid #111;"></center><br>
        <table style="width: 100%; border-collapse: collapse; text-align: left; margin: 0 auto;">
            <tr style="background-color: #1A365D; color: white;"><th colspan="2" style="padding: 10px; border: 1px solid #333; text-align: center;">I. STRATEGIC PERFORMANCE INDICATORS</th></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">Service Capability Level</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('Level', '')}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 1: Functionality of PHU</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('SI1', '')}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 2: Green Viability Assessment</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('SI2', '')}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 3: Capital Formation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d.get('SI3_Cat', '')} ({d.get('SI3_Stat', '')})</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 4: ISO Accreditation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d.get('SI4_Status', '')}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 5: PGS Accreditation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d.get('SI5_25', '')}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 6: Specialty Centers</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('SI6', 0):.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 7: Zero Co-Payment</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('SI7', 0):.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 8: Paperless EMR</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('SI8', 0):.2f}%</td></tr>
            <tr style="background-color: #7B341E; color: white;"><th colspan="2" style="padding: 10px; border: 1px solid #333; text-align: center;">II. CORE QUALITY INDICATORS</th></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 1: ER TAT (&lt;4h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('CI1', 0):.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 2: Discharge TAT (&lt;6h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('CI2', 0):.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 3: Lab TAT (&lt;5h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('CI3', 0):.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 4: HAI Rate</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('CI4', 0):.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 5: Client Experience Survey</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('CI5', 0):.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 6: Disbursement Rate</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d.get('CI6', 0):.2f}%</td></tr>
        </table><br><br>
        <table style="width:100%; text-align:center;"><tr><td>__________________________<br><b>{u['user']}</b><br>{u['pos']}</td><td>__________________________<br><b>{d.get('Head_Name', '')}</b><br>{d.get('Head_Pos', '')}</td></tr></table><br>
        <center><button class="no-print" onclick="window.print()" style="padding:12px 25px; background:#1A365D; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print to PDF</button></center>
    </div>"""
    st.components.v1.html(html, height=950, scrolling=True)

def generate_print_view_mod2(d):
    u = st.session_state.user_info
    html = f"""<style>@media print {{ .no-print {{ display: none !important; }} }}</style>
    <div style="font-family: Arial, sans-serif; padding: 40px; background: white; color: black; border: 2px solid #333; max-width: 850px; margin: 0 auto;">
        <center><h2 style="margin:0;">HEALTH FACILITY CENSUS & HCPN DATA (2025-2026)</h2><h4 style="margin:5px 0;">{u['hosp']} — {u['dept']} Department</h4><hr style="border:1px solid #111;"></center>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 11px;">
            <tr style="background: #eee;"><th style="border: 1px solid #333; padding: 6px; text-align: left; width: 45%;">Data Parameter</th><th style="border: 1px solid #333; padding: 6px; text-align: center; width: 15%;">Value</th><th style="border: 1px solid #333; padding: 6px; text-align: left; width: 40%;">Remarks</th></tr>
            <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">I. BASIC INFORMATION</td></tr>
            <tr><td style="border: 1px solid #333; padding: 4px;">Service Capability (2026)</td><td style="border: 1px solid #333; padding: 4px; text-align: center;">{d.get('LV_26', '')}</td><td style="border: 1px solid #333; padding: 4px;">{d.get('RM_LV26', '')}</td></tr>
            <tr><td style="border: 1px solid #333; padding: 4px;">ABC by Licensing (2025)</td><td style="border: 1px solid #333; padding: 4px; text-align: center;">{d.get('ABC_25', '')}</td><td style="border: 1px solid #333; padding: 4px;">{d.get('RM_ABC_25', '')}</td></tr>
            <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">II. HOSPITAL CENSUS (2025)</td></tr>
            <tr><td style="border: 1px solid #333; padding: 4px;">Bed Occupancy Rate (BOR)</td><td style="border: 1px solid #333; padding: 4px; text-align: center;">{d.get('BOR_25', '')}</td><td style="border: 1px solid #333; padding: 4px;">{d.get('RM_BOR_25', '')}</td></tr>
            <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">III. HCPN & BUCAS</td></tr>
            <tr><td style="border: 1px solid #333; padding: 4px;">Apex/End-Referral Status</td><td style="border: 1px solid #333; padding: 4px; text-align: center;">{d.get('APEX', '')}</td><td style="border: 1px solid #333; padding: 4px;">{d.get('RM_APEX', '')}</td></tr>
        </table><br><br><br>
        <table style="width:100%; text-align:center; font-size:14px;"><tr><td style="width:50%;">__________________________<br><b>{u['user']}</b><br>{u['pos']}</td><td style="width:50%;">__________________________<br><b>{d.get('Head_Name', '')}</b><br>{d.get('Head_Pos', '')}</td></tr></table>
        <center><br><button class="no-print" onclick="window.print()" style="padding:10px 20px; background:#222; color:white; border:none; border-radius:5px; cursor:pointer;">Print Submission</button></center>
    </div>"""
    st.components.v1.html(html, height=1000, scrolling=True)

# --- 9. ROUTING, LOGIN, & DASHBOARD ---
def get_row_html(title, deadline, is_locked):
    bg_color = "rgba(239, 68, 68, 0.15)" if is_locked else "rgba(34, 197, 94, 0.15)"
    border_color = "#EF4444" if is_locked else "#22C55E"
    status_text = "🔒 CLOSED" if is_locked else "🟢 OPEN"
    return f"""<div style="background-color: {bg_color}; border-left: 5px solid {border_color}; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <div style="flex: 2; font-size: 1.1em; font-weight: bold; color: #E2E8F0;">{title}</div><div style="flex: 1; font-family: monospace; color: #94A3B8;">{deadline}</div><div style="flex: 1; font-weight: bold; color: {border_color}; text-align: right;">{status_text}</div></div>"""

def login_screen():
    st.markdown("<h2 style='text-align: center;'>🏥 HFDB Online Data Reporting and Submission Portal</h2>", unsafe_allow_html=True)
    if "auth_mode" not in st.session_state:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="marker marker-green"></div>', unsafe_allow_html=True)
            if st.button("🆕 NEW USER", use_container_width=True): st.session_state.auth_mode = "new"; st.rerun()
        with c2:
            st.markdown('<div class="marker marker-red"></div>', unsafe_allow_html=True)
            if st.button("🔑 EXISTING USER", use_container_width=True): st.session_state.auth_mode = "existing"; st.rerun()
    else:
        if st.button("⬅️ Back"): del st.session_state.auth_mode; st.rerun()
        
        if st.session_state.auth_mode == "new":
            h_df = get_static_sheet("Facility_List")
            h_list = h_df["Facility_Name"].tolist() if not h_df.empty else []
            h_name = st.selectbox("Hospital Name", [""] + sorted(h_list))
            u_dept = st.text_input("Department/Unit (e.g., ER, PHU, Management)")
            u_name = st.text_input("Encoder Name")
            u_pos = st.text_input("Designation")
            if st.button("Register Profile", type="primary"):
                st.session_state.user_id = generate_custom_id()
                st.session_state.user_info = {"hosp": h_name, "dept": u_dept, "user": u_name, "pos": u_pos, "role": "user", "level": "Level 1"}
                st.success("Registered successfully! Redirecting..."); time.sleep(1); st.rerun()
                        
        elif st.session_state.auth_mode == "existing":
            uid = st.text_input("Enter HFDB-2026 ID Code")
            if st.button("Enter Portal", type="primary"):
                if uid == "ADMIN-2026":
                    st.session_state.user_id = uid
                    st.session_state.user_info = {"hosp": "DOH Central", "dept": "System Admin", "user": "Administrator", "pos": "Admin", "role": "admin", "level": "N/A"}
                    st.rerun()
                else:
                    st.session_state.user_id = uid
                    st.session_state.user_info = {"hosp": "Sample Medical Center", "dept": "Engineering", "user": "John Doe", "pos": "Officer", "role": "user", "level": "Level 2"}
                    st.rerun()

def dashboard():
    u = st.session_state.user_info
    st.markdown("<h2 style='text-align: center;'>🏥 HFDB Online Data Reporting and Submission Portal</h2>", unsafe_allow_html=True)
    st.info(f"Facility: **{u['hosp']}** | Department: **{u['dept']}** | Encoder: **{u['user']}**")
    
    d1_str, d1_locked = get_module_config("Mod1")
    d2_str, d2_locked = get_module_config("Mod2")
    d3_str, d3_locked = get_module_config("Mod3")
    
    modules = [
        {"id": "Mod1", "title": "📊 Hospital Scorecard", "date": d1_str, "locked": d1_locked, "marker": "marker-blue"},
        {"id": "Mod2", "title": "📈 Hospital Census & HCPN", "date": d2_str, "locked": d2_locked, "marker": "marker-red"},
        {"id": "Mod3", "title": "🌿 Green Viability Assessment", "date": d3_str, "locked": d3_locked, "marker": "marker-green"}
    ]
    
    ongoing = [m for m in modules if not m["locked"]]
    lapsed = [m for m in modules if m["locked"]]

    if ongoing:
        st.markdown("### 🟢 Ongoing Data Submission Modules")
        for m in ongoing:
            st.markdown(get_row_html(m["title"], m["date"], m["locked"]), unsafe_allow_html=True)
            st.markdown(f'<div class="marker {m["marker"]}"></div>', unsafe_allow_html=True)
            if st.button(f"OPEN {m['id'].upper()}", use_container_width=True, key=f"btn_on_{m['id']}"):
                st.session_state.current_module = m['id']; st.rerun()
            st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)

    if lapsed:
        st.markdown("### 🔴 Lapsed Data Submission Modules")
        for m in lapsed:
            st.markdown(get_row_html(m["title"], m["date"], m["locked"]), unsafe_allow_html=True)
            st.markdown(f'<div class="marker {m["marker"]}"></div>', unsafe_allow_html=True)
            if st.button(f"VIEW {m['id'].upper()} (READ-ONLY)", use_container_width=True, key=f"btn_lap_{m['id']}"):
                st.session_state.current_module = m['id']; st.rerun()
            st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)
        
    st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

# --- 10. THE TRAFFIC CONTROLLER ---
if "user_id" not in st.session_state: login_screen()
elif "current_module" in st.session_state:
    if not st.session_state.get("isolated_print_html"):
        if st.button("🏠 Return to Dashboard"): 
            if "show_print" in st.session_state: del st.session_state.show_print
            del st.session_state.current_module; st.rerun()
    
    mod = st.session_state.current_module
    if mod == "Mod1": module_scorecard()
    elif mod == "Mod2": module_census_data()
    elif mod == "Mod3": module_gva()
    elif mod == "Admin_Mod1": admin_analysis_view("Mod1", "📊 Scorecard Data Analysis")
    elif mod == "Admin_Mod2": admin_analysis_view("Mod2", "📈 Census Data Analysis")
    elif mod == "Admin_Mod3": admin_analysis_view("Mod3", "🌿 Green Viability Dashboard")
else: 
    if st.session_state.user_info.get("role") == "admin": admin_dashboard()
    else: dashboard()
