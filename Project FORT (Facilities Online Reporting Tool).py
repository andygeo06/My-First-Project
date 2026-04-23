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

# --- 2. PREMIUM COMPACT CSS ENGINE ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #0E1117; color: #C9D1D9; }}
    
    /* Fixed Top Header Space (Not too aggressive now!) */
    .block-container {{ padding-top: 3rem !important; padding-bottom: 3rem !important; }}
    
    .section-header-strat {{
        background-color: #1A365D; padding: 10px; border-radius: 8px 8px 0 0;
        text-align: center; border-bottom: 3px solid #3B82F6; margin-bottom: 10px;
    }}
    .section-header-core {{
        background-color: #7B341E; padding: 10px; border-radius: 8px 8px 0 0;
        text-align: center; border-bottom: 3px solid #EF4444; margin-bottom: 10px;
    }}

    div[data-testid="stExpander"] {{
        background-color: #161B22 !important; border: 1px solid #30363D !important;
        border-radius: 6px !important; margin-bottom: 8px; transition: 0.3s;
    }}
    div[data-testid="stExpander"]:hover {{ border-color: #58A6FF !important; }}
    
    div[data-testid="stExpander"] div[role="region"] {{
        background-color: #0D1117 !important; padding: 15px !important;
        border-top: 1px solid #30363D;
    }}

    /* === BUTTON COLOR OVERRIDES (COMPACT HEIGHTS) === */
    /* Module 1 - Strategic Blue */
    div.mod1-btn button {{
        background-color: #1A365D !important; color: white !important;
        border: 1px solid #3B82F6 !important; font-weight: bold !important;
        height: 3em !important; width: 100% !important; transition: 0.3s !important;
    }}
    div.mod1-btn button:hover {{ background-color: #2563EB !important; border-color: #FFFFFF !important; }}

    /* Module 2 - Core Red/Rust */
    div.mod2-btn button {{
        background-color: #7B341E !important; color: white !important;
        border: 1px solid #EF4444 !important; font-weight: bold !important;
        height: 3em !important; width: 100% !important; transition: 0.3s !important;
    }}
    div.mod2-btn button:hover {{ background-color: #991B1B !important; border-color: #FFFFFF !important; }}
    
    /* New User - Green */
    div.new-user-btn button {{
        background-color: #15803d !important; color: white !important;
        border: 1px solid #22c55e !important; font-weight: bold !important;
    }}
    div.new-user-btn button:hover {{ background-color: #166534 !important; border-color: #FFFFFF !important; }}

    /* Logout - Red */
    div.logout-btn button {{
        background-color: #dc2626 !important; color: white !important;
        border: 1px solid #ef4444 !important; font-weight: bold !important;
    }}
    div.logout-btn button:hover {{ background-color: #991b1b !important; border-color: #FFFFFF !important; }}
</style>
""", unsafe_allow_html=True)

# --- 3. HELPER FUNCTIONS & DATA FETCHING ---

def generate_custom_id():
    year = 2026
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return f"HFDB-{year}-{random_str}"

def clean_pct(input_str):
    try:
        if not input_str: return 0.0
        return float(str(input_str).replace('%', '').strip())
    except ValueError: return 0.0

def score_calc(n, d, label):
    val = (n / d * 100) if d > 0 else 0
    st.markdown(f"📈 **Current {label} Performance:** `{val:.2f}%`")
    return val

def get_idx(opts_series, val):
    opts_list = list(opts_series.dropna().unique())
    return opts_list.index(val) if val in opts_list else 0

@st.cache_data(ttl="1h")
def get_dropdown_data():
    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
        dd.columns = dd.columns.str.strip()
        return dd
    except: return None

@st.cache_data(ttl="10m")
def get_module_config(module_name="Mod1"):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Config", ttl=0)
        row = df[df.iloc[:, 0] == module_name]
        if not row.empty:
            deadline_str = str(row.iloc[0, 1]).strip()
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d")
            return deadline_str, datetime.now() > deadline_date
    except: pass
    return "Not Set", False

def get_previous_entry(module_name="Mod1"):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
        if df is not None and "User_ID" in df.columns:
            user_data = df[df["User_ID"].astype(str) == str(st.session_state.user_id)]
            if not user_data.empty: return user_data.iloc[-1].to_dict()
    except: pass
    return {}

def submit_module_data(res_data, module_name="Mod1"):
    with st.spinner(f"Syncing data to {module_name}..."):
        try:
            try: df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
            except: df = pd.DataFrame(columns=["User_ID", "Timestamp", "Hospital", "Encoder", "Scanned_PDF"])
                
            u = st.session_state.user_info
            new_record = {"User_ID": st.session_state.user_id, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Hospital": u["hosp"], "Encoder": u["user"]}
            new_record.update(res_data)
            
            if "User_ID" in df.columns:
                df = df[df["User_ID"].astype(str) != str(st.session_state.user_id)]
                
            updated_df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet=module_name, data=updated_df)
            st.toast(f"Data successfully synced to {module_name}!", icon="✅")
            return True
        except Exception as e:
            st.error(f"Submission failed: {e}")
            return False

# --- 4. MODULE 1: HOSPITAL SCORECARD ---

def module_scorecard():
    dd = get_dropdown_data()
    if dd is None:
        st.error("Sheet 'Mod1_DD' not found. Please check your Google Sheet tabs.")
        return

    if "staged_data" not in st.session_state or st.session_state.staged_data is None:
        st.session_state.staged_data = get_previous_entry("Mod1")

    prev = st.session_state.staged_data 
    deadline_str, locked = get_module_config("Mod1")

    if locked:
        st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is in READ-ONLY mode.")

    st.markdown('<div class="section-header-strat"><h3 style="margin:0;">📊 STRATEGIC PERFORMANCE INDICATORS</h3></div>', unsafe_allow_html=True)
    
    with st.expander("🔹 SI 1: % Functionality of PHU", expanded=False):
        s1 = clean_pct(st.text_input("Percentage (e.g., 95%)", value=str(prev.get("SI1", "0%")), disabled=locked, key="si1_in"))
        st.caption(f"Captured: **{s1}%**")
        
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)", expanded=False):
        s2 = clean_pct(st.text_input("GVA Score (e.g., 88%)", value=str(prev.get("SI2", "0%")), disabled=locked, key="si2_in"))
        st.caption(f"Captured: **{s2}%**")

    with st.expander("🔹 SI 3: Capital Formation", expanded=False):
        c1, c2 = st.columns(2)
        cat_opts = dd["Indicator 3, DD1"]
        src_opts = dd["Indicator 3, DD2"]
        cat = c1.selectbox("Category", cat_opts.dropna().unique(), index=get_idx(cat_opts, prev.get("SI3_Cat")), disabled=locked)
        src = c2.selectbox("Fund Source", src_opts.dropna().unique(), index=get_idx(src_opts, prev.get("SI3_Src")), disabled=locked)
        stat_opts = dd["Indicator 3, DD3.a"] if "Infrastructure" in str(cat) else dd["Indicator 3, DD3.b"]
        stat = st.selectbox("Status", stat_opts.dropna().unique(), index=get_idx(stat_opts, prev.get("SI3_Stat")), disabled=locked)

    with st.expander("🔹 SI 4: ISO 9001:2015 Accreditation", expanded=False):
        c1, c2 = st.columns(2)
        iso1_opts = dd["Indicator 4, DD1"]
        iso2_opts = dd["Indicator 4, DD2"]
        iso1 = c1.selectbox("ISO Status", iso1_opts.dropna().unique(), index=get_idx(iso1_opts, prev.get("SI4_Status")), disabled=locked)
        iso2 = c2.selectbox("Internal Audit", iso2_opts.dropna().unique(), index=get_idx(iso2_opts, prev.get("SI4_Audit")), disabled=locked)

    with st.expander("🔹 SI 5: PGS Accreditation Status", expanded=False):
        c1, c2 = st.columns(2)
        pgs1_opts = dd["Indicator 5, DD1"]
        pgs2_opts = dd["Indicator 5, DD2"]
        pgs1 = c1.selectbox("2024 PGS Status", pgs1_opts.dropna().unique(), index=get_idx(pgs1_opts, prev.get("SI5_24")), disabled=locked)
        pgs2 = c2.selectbox("2025 PGS Status", pgs2_opts.dropna().unique(), index=get_idx(pgs2_opts, prev.get("SI5_25")), disabled=locked)

    with st.expander("🔹 SI 6: Functional Specialty Centers", expanded=False):
        c1, c2 = st.columns(2)
        s6n = c1.number_input("Functional Centers", value=int(float(prev.get("SI6_N", 0))), disabled=locked, key="s6n")
        s6d = c2.number_input("Target Centers", value=int(float(prev.get("SI6_D", 1))), disabled=locked, key="s6d")
        s6v = score_calc(s6n, s6d, "SI 6")

    with st.expander("🔹 SI 7: Zero Co-Payment Patients", expanded=False):
        c1, c2 = st.columns(2)
        s7n = c1.number_input("Zero Co-Pay Patients", value=int(float(prev.get("SI7_N", 0))), disabled=locked, key="s7n")
        s7d = c2.number_input("Total Basic Patients", value=int(float(prev.get("SI7_D", 1))), disabled=locked, key="s7d")
        s7v = score_calc(s7n, s7d, "SI 7")

    with st.expander("🔹 SI 8: Paperless EMR Areas", expanded=False):
        c1, c2 = st.columns(2)
        s8n = c1.number_input("Paperless Areas", value=int(float(prev.get("SI8_N", 0))), disabled=locked, key="s8n")
        s8d = c2.number_input("Expected Areas", value=int(float(prev.get("SI8_D", 1))), disabled=locked, key="s8d")
        s8v = score_calc(s8n, s8d, "SI 8")

    st.markdown('<div class="section-header-core"><h3 style="margin:0;">🎯 CORE QUALITY INDICATORS</h3></div>', unsafe_allow_html=True)

    with st.expander("🔸 CI 1: ER Turnaround Time (<4 hrs)", expanded=False):
        c1, c2 = st.columns(2)
        ci1n = c1.number_input("ER <4h Count", value=int(float(prev.get("CI1_N", 0))), disabled=locked, key="ci1n")
        ci1d = c2.number_input("Total ER Patients", value=int(float(prev.get("CI1_D", 1))), disabled=locked, key="ci1d")
        ci1v = score_calc(ci1n, ci1d, "ER TAT")

    with st.expander("🔸 CI 2: Discharge Turnaround (<6 hrs)", expanded=False):
        c1, c2 = st.columns(2)
        ci2n = c1.number_input("Discharge <6h Count", value=int(float(prev.get("CI2_N", 0))), disabled=locked, key="ci2n")
        ci2d = c2.number_input("Total Discharges", value=int(float(prev.get("CI2_D", 1))), disabled=locked, key="ci2d")
        ci2v = score_calc(ci2n, ci2d, "Discharge TAT")

    with st.expander("🔸 CI 3: Lab Result Turnaround (<5 hrs)", expanded=False):
        c1, c2 = st.columns(2)
        ci3n = c1.number_input("Results <5h Count", value=int(float(prev.get("CI3_N", 0))), disabled=locked, key="ci3n")
        ci3d = c2.number_input("Total Lab Tests", value=int(float(prev.get("CI3_D", 1))), disabled=locked, key="ci3d")
        ci3v = score_calc(ci3n, ci3d, "Lab TAT")

    with st.expander("🔸 CI 4: Healthcare Associated Infection Rate", expanded=False):
        c1, c2 = st.columns(2)
        ci4n = c1.number_input("Total HAI Cases", value=int(float(prev.get("CI4_N", 0))), disabled=locked, key="ci4n")
        ci4d = c2.number_input("Discharges/Deaths >48h", value=int(float(prev.get("CI4_D", 1))), disabled=locked, key="ci4d")
        ci4v = score_calc(ci4n, ci4d, "HAI Rate")

    with st.expander("🔸 CI 5: Client Experience Survey", expanded=False):
        c1, c2 = st.columns(2)
        ci5n = c1.number_input("Outstanding Ratings", value=int(float(prev.get("CI5_N", 0))), disabled=locked, key="ci5n")
        ci5d = c2.number_input("Total Respondents", value=int(float(prev.get("CI5_D", 1))), disabled=locked, key="ci5d")
        ci5v = score_calc(ci5n, ci5d, "Survey")

    with st.expander("🔸 CI 6: Disbursement Rate", expanded=False):
        c1, c2 = st.columns(2)
        ci6n = c1.number_input("Total Disbursement", value=float(prev.get("CI6_N", 0.0)), disabled=locked, key="ci6n")
        ci6d = c2.number_input("Total Allocation", value=float(prev.get("CI6_D", 1.0)), disabled=locked, key="ci6d")
        ci6v = score_calc(ci6n, ci6d, "Disbursement")

    st.divider()
    c1, c2 = st.columns(2)
    h_name = c1.text_input("Name of Head of Facility:", value=prev.get("Head_Name", ""), disabled=locked)
    h_pos = c2.text_input("Designation of Head of Facility:", value=prev.get("Head_Pos", ""), disabled=locked)

    res_db = {
        "SI1": s1, "SI2": s2, "SI3_Cat": cat, "SI3_Src": src, "SI3_Stat": stat,
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
            st.session_state.show_print = True
            st.rerun()

    if st.session_state.get("show_print", False):
        generate_print_view(res_print)
        if not locked:
            st.divider()
            st.markdown("### 📤 Step 1: Upload to Google Drive")
            st.link_button("📂 OPEN HFDB GOOGLE DRIVE FOLDER", "https://drive.google.com/drive/folders/15_dWyeXPxKXfGXekKgiLOaJ-9rIwthti?usp=drive_link", type="primary")
            st.markdown("### 🔗 Step 2: Attach Link to Submission")
            pdf_link = st.text_input("Paste Google Drive Link Here:")
            if st.button("💾 Encode Link", type="secondary"):
                if pdf_link:
                    try:
                        df = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1", ttl=0)
                        mask = df["User_ID"].astype(str) == str(st.session_state.user_id)
                        if mask.any():
                            df.loc[mask, "Scanned_PDF"] = pdf_link
                            conn.update(spreadsheet=SHEET_URL, worksheet="Mod1", data=df)
                            st.success("✅ PDF Link successfully encoded!")
                    except Exception as e: st.error(f"Failed to attach link: {e}")

# --- 5. MODULE 2: HOSPITAL CENSUS & HCPN ---

def module_census_data():
    if "staged_data" not in st.session_state or st.session_state.staged_data is None:
        st.session_state.staged_data = get_previous_entry("Mod2")
        
    prev = st.session_state.staged_data
    deadline_str, locked = get_module_config("Mod2")
    DRIVE_LINK = "https://drive.google.com/drive/folders/15_dWyeXPxKXfGXekKgiLOaJ-9rIwthti?usp=drive_link"
    
    if locked: st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is in READ-ONLY mode.")

    st.markdown('<div class="section-header-core"><h3 style="margin:0;">📈 MODULE 2: BASIC INFO, CENSUS & HCPN</h3></div>', unsafe_allow_html=True)
    
    st.header("1️⃣ BASIC INFORMATION")
    with st.expander("Expand to fill out Facility Capability & Bed Capacity", expanded=False):
        h1, h2, h3 = st.columns([5, 2, 2])
        h1.caption("Data Request"); h2.caption("Input Field"); h3.caption("Remarks")

        lv_opts = ["Level 1", "Level 2", "Level 3"]
        
        r1_1, r1_2, r1_3 = st.columns([5, 2, 2])
        r1_1.markdown("**Health Facility Service Capability Level (2026, Current Year):**")
        lv_26 = r1_2.selectbox("Level 26", lv_opts, index=get_idx(pd.Series(lv_opts), prev.get("LV_26")), disabled=locked, label_visibility="collapsed")
        rm_lv26 = r1_3.text_input("Remarks LV26", value=prev.get("RM_LV26", ""), disabled=locked, label_visibility="collapsed")

        r2_1, r2_2, r2_3 = st.columns([5, 2, 2])
        r2_1.markdown("**Target Health Facility Service Capability Level in 2027 (Next Year):**")
        lv_27 = r2_2.selectbox("Level 27", lv_opts, index=get_idx(pd.Series(lv_opts), prev.get("LV_27")), disabled=locked, label_visibility="collapsed")
        rm_lv27 = r2_3.text_input("Remarks LV27", value=prev.get("RM_LV27", ""), disabled=locked, label_visibility="collapsed")

        r3_1, r3_2, r3_3 = st.columns([5, 2, 2])
        r3_1.markdown("""
        **Please upload the LTO (2025) and LTO (2026) using this link:**<br>
        <small><i>Note: Please make sure you FOLLOW the proper naming of the file provided:<br>
        <b>HOSPITAL ACRONYM_LTO_2025_2026 (e.g. SOGHMC_LTO_2025_2026)</b><br>
        Failing to comply will make your submission INVALID</i></small>
        """, unsafe_allow_html=True)
        r3_2.link_button("📂 OPEN GOOGLE DRIVE FOLDER", DRIVE_LINK, use_container_width=True)
        rm_lto = r3_3.text_input("Remarks LTO", value=prev.get("RM_LTO", ""), disabled=locked, label_visibility="collapsed")

        st.divider()
        
        labels = [
            ("Authorized Bed Capacity (ABC) by Licensing as of December 31, 2025:", "ABC_25"), 
            ("Target Authorized Bed Capacity (ABC) by Licensing by the end of 2026:", "ABC_26"), 
            ("Authorized Bed Capacity (ABC) by Law (2025):", "LAW_25"), 
            ("Authorized Bed Capacity (ABC) by Law (2026):", "LAW_26")
        ]
        res_beds = {}
        for label, key in labels:
            c1, c2, c3 = st.columns([5, 2, 2])
            c1.markdown(f"**{label}**")
            res_beds[key] = c2.number_input(label, value=int(float(prev.get(key, 0))), step=1, disabled=locked, label_visibility="collapsed")
            res_beds[f"RM_{key}"] = c3.text_input(f"Remarks {key}", value=prev.get(f"RM_{key}", ""), disabled=locked, label_visibility="collapsed")

        r8_1, r8_2, r8_3 = st.columns([5, 2, 2])
        r8_1.markdown("""
        **Target Authorized Bed Capacity (ABC) by Licensing in 2027:**<br>
        <small><i>(If the same with 2025/2026, please input the same ABC in the cell. If the ABC would increase in 2026, kindly indicate in the cell the target ABC and the target quarter for which it will be implemented in the REMARKS column)</i></small>
        """, unsafe_allow_html=True)
        abc_27 = r8_2.number_input("ABC 27", value=int(float(prev.get("ABC_27", 0))), step=1, disabled=locked, label_visibility="collapsed")
        rm_abc27 = r8_3.text_input("Remarks ABC27", value=prev.get("RM_ABC27", ""), disabled=locked, label_visibility="collapsed")

        r9_1, r9_2, r9_3 = st.columns([5, 2, 2])
        r9_1.markdown("**Implementing Bed Capacity (IBC) (2025):**")
        ibc_25 = r9_2.number_input("IBC 25", value=int(float(prev.get("IBC_25", 0))), step=1, disabled=locked, label_visibility="collapsed")
        rm_ibc25 = r9_3.text_input("Remarks IBC25", value=prev.get("RM_IBC25", ""), disabled=locked, label_visibility="collapsed")

    st.header("2️⃣ HOSPITAL CENSUS DATA")
    with st.expander("Expand to fill out Census Data", expanded=False):
        census_data = [
            ("Bed Occupancy Rate (BOR) (2025):", "BOR_25", "pct"),
            ("Average Length of Stay (ALOS) (2025):", "ALOS_25", "float"),
            ("Total Inpatient Days Served (TIDS) (2025):", "TIDS_25", "int"),
            ("Total Number of Inpatients (2025):", "INP_25", "int"),
            ("Total Number of Outpatient Visits (2025):", "OUT_25", "int"),
            ("Total Number of Emergency Room (ER) Visits (2025):", "ERV_25", "int")
        ]
        res_census = {}
        for label, key, dtype in census_data:
            c1, c2, c3 = st.columns([5, 2, 2])
            c1.markdown(f"**{label}**")
            if dtype == "pct": res_census[key] = c2.text_input(label, value=str(prev.get(key, "0%")), disabled=locked, label_visibility="collapsed")
            elif dtype == "float": res_census[key] = c2.number_input(label, value=float(prev.get(key, 0.0)), step=0.1, disabled=locked, label_visibility="collapsed")
            else: res_census[key] = c2.number_input(label, value=int(float(prev.get(key, 0))), step=1, disabled=locked, label_visibility="collapsed")
            res_census[f"RM_{key}"] = c3.text_input(f"Remarks {key}", value=prev.get(f"RM_{key}", ""), disabled=locked, label_visibility="collapsed")

    st.header("3️⃣ HCPN, BUCAS AND COORDINATES")
    with st.expander("Expand to fill out HCPN & BUCAS Data", expanded=False):
        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("**Based on DC No. 2025-0554, is the hospital identified as Apex or End-Referral Hospital?**")
        apex = c2.selectbox("Apex", ["Yes", "No"], index=get_idx(pd.Series(["Yes", "No"]), prev.get("APEX")), disabled=locked, label_visibility="collapsed")
        rm_apex = c3.text_input("Remarks Apex", value=prev.get("RM_APEX", ""), disabled=locked, label_visibility="collapsed")

        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("""
        **For those who already have a signed or on-going review MOA/MOU with a HCPN or province (not with other hospitals and other health facilities), kindly upload a scanned copy or picture of the signed or on-going review MOA/MOU on the link provided**<br>
        <small><i>Note: Please make sure you FOLLOW the proper naming of the file provided:<br>
        <b>HOSPITAL ACRONYM_MOA (e.g. SOGHMC_MOA)</b><br>
        Failing to comply will make your submission INVALID</i></small>
        """, unsafe_allow_html=True)
        c2.link_button("📂 OPEN GOOGLE DRIVE FOLDER", DRIVE_LINK, use_container_width=True)
        rm_moa = c3.text_input("Remarks MOA", value=prev.get("RM_MOA", ""), disabled=locked, label_visibility="collapsed")

        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("**If the hospital already has MOA/MOU with a HCPN/province, how many HCPNs or provinces are they linked with?**")
        hcpn_count = c2.number_input("HCPN Count", value=int(float(prev.get("HCPN_COUNT", 0))), step=1, disabled=locked, label_visibility="collapsed")
        rm_hcpn = c3.text_input("Remarks HCPN", value=prev.get("RM_HCPN", ""), disabled=locked, label_visibility="collapsed")

        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("**Does the hospital operate a BUCAS Center/s?**")
        bucas = c2.selectbox("BUCAS", ["Yes", "No"], index=get_idx(pd.Series(["Yes", "No"]), prev.get("BUCAS")), disabled=locked, label_visibility="collapsed")
        rm_bucas = c3.text_input("Remarks BUCAS", value=prev.get("RM_BUCAS", ""), disabled=locked, label_visibility="collapsed")
        if bucas == "Yes":
            st.warning("**If yes, kindly update the data in the UHC HSC BUCAS Tracker:**")
            st.link_button("🔗 OPEN BUCAS DASHBOARD", "https://bit.ly/BUCASdashboard", type="primary")

        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("**Kindly provide the exact coordinates of the BUCAS Center using the format Latitude, Longitude (e.g. 14.6156280516298, 120.982498127343) (Can be acquired via Google Maps)**")
        coords = c2.text_input("Coords", value=prev.get("COORDS", ""), disabled=locked, label_visibility="collapsed")
        rm_coords = c3.text_input("Remarks Coords", value=prev.get("RM_COORDS", ""), disabled=locked, label_visibility="collapsed")

        c1, c2, c3 = st.columns([5, 2, 2])
        c1.markdown("""
        **If applicable, please provide a copy of the BUCAS Center's license to operate in this folder**<br>
        <small><i>Note: Please make sure you FOLLOW the proper naming of the file provided:<br>
        <b>HOSPITAL ACRONYM_BUCAS (e.g. SOGHMC_BUCAS)</b><br>
        Failing to comply will make your submission INVALID</i></small>
        """, unsafe_allow_html=True)
        c2.link_button("📂 OPEN GOOGLE DRIVE FOLDER", DRIVE_LINK, use_container_width=True)
        rm_bucas_lto = c3.text_input("Remarks BUCAS LTO", value=prev.get("RM_BUCAS_LTO", ""), disabled=locked, label_visibility="collapsed")

    st.divider()
    h_col1, h_col2 = st.columns(2)
    h_name = h_col1.text_input("Name of Head of Facility:", value=prev.get("Head_Name", ""), disabled=locked)
    h_pos = h_col2.text_input("Designation of Head of Facility:", value=prev.get("Head_Pos", ""), disabled=locked)

    final_data = {
        "LV_26": lv_26, "RM_LV26": rm_lv26, "LV_27": lv_27, "RM_LV27": rm_lv27, "RM_LTO": rm_lto,
        "ABC_25": res_beds["ABC_25"], "RM_ABC_25": res_beds["RM_ABC_25"], "ABC_26": res_beds["ABC_26"], "RM_ABC_26": res_beds["RM_ABC_26"],
        "LAW_25": res_beds["LAW_25"], "RM_LAW_25": res_beds["RM_LAW_25"], "LAW_26": res_beds["LAW_26"], "RM_LAW_26": res_beds["RM_LAW_26"],
        "ABC_27": abc_27, "RM_ABC27": rm_abc27, "IBC_25": ibc_25, "RM_IBC25": rm_ibc25,
        "APEX": apex, "RM_APEX": rm_apex, "RM_MOA": rm_moa, "HCPN_COUNT": hcpn_count, "RM_HCPN": rm_hcpn,
        "BUCAS": bucas, "RM_BUCAS": rm_bucas, "COORDS": coords, "RM_COORDS": rm_coords, "RM_BUCAS_LTO": rm_bucas_lto,
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
            st.session_state.show_print = True
            st.rerun()

    if st.session_state.get("show_print", False):
        generate_print_view_mod2(final_data)

# --- 6. PRINT ENGINES ---
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
        <table style="width: 100%; border-collapse: collapse; text-align: left; margin: 0 auto;">
            <tr style="background-color: #1A365D; color: white;">
                <th colspan="2" style="padding: 10px; border: 1px solid #333; text-align: center;">I. STRATEGIC PERFORMANCE INDICATORS</th>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 8px; border: 1px solid #333; width: 65%;">Indicator</th>
                <th style="padding: 8px; border: 1px solid #333; width: 35%; text-align: center;">Performance / Status</th>
            </tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 1: Functionality of PHU</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI1']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 2: Green Viability Assessment</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI2']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 3: Capital Formation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d['SI3_Cat']} ({d['SI3_Stat']})</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 4: ISO Accreditation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d['SI4_Status']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 5: PGS Accreditation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d['SI5_25']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 6: Specialty Centers</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI6']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 7: Zero Co-Payment</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI7']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 8: Paperless EMR</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI8']:.2f}%</td></tr>
            
            <tr style="background-color: #7B341E; color: white;">
                <th colspan="2" style="padding: 10px; border: 1px solid #333; text-align: center;">II. CORE QUALITY INDICATORS</th>
            </tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 1: ER TAT (&lt;4h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI1']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 2: Discharge TAT (&lt;6h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI2']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 3: Lab TAT (&lt;5h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI3']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 4: HAI Rate</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI4']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 5: Client Experience Survey</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI5']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 6: Disbursement Rate</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI6']:.2f}%</td></tr>
        </table>
        <br><br>
        <table style="width:100%; text-align:center;">
            <tr>
                <td>__________________________<br><b>{u['user']}</b><br>{u['pos']}</td>
                <td>__________________________<br><b>{d['Head_Name']}</b><br>{d['Head_Pos']}</td>
            </tr>
        </table>
        <br>
        <center><button onclick="window.print()" style="padding:12px 25px; background:#1A365D; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print to PDF</button></center>
    </div>"""
    st.components.v1.html(html, height=950, scrolling=True)

def generate_print_view_mod2(d):
    u = st.session_state.user_info
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 40px; background: white; color: black; border: 2px solid #333; max-width: 850px; margin: 0 auto;">
        <center>
            <h2 style="margin:0;">HEALTH FACILITY CENSUS & HCPN DATA (2025-2026)</h2>
            <h4 style="margin:5px 0;">{u['hosp']}</h4>
            <hr style="border:1px solid #111;">
        </center>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px;">
            <tr style="background: #eee;">
                <th style="border: 1px solid #333; padding: 8px; text-align: left; width: 40%;">Data Parameter</th>
                <th style="border: 1px solid #333; padding: 8px; text-align: center; width: 20%;">Value</th>
                <th style="border: 1px solid #333; padding: 8px; text-align: left; width: 40%;">Remarks</th>
            </tr>
            <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">I. BASIC INFORMATION</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">Service Capability (2026)</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['LV_26']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_LV26']}</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">ABC by Licensing (2025)</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['ABC_25']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_ABC_25']}</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">IBC (2025)</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['IBC_25']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_IBC25']}</td></tr>
            
            <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">II. HOSPITAL CENSUS (2025)</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">Bed Occupancy Rate (BOR)</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['BOR_25']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_BOR_25']}</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">Average Length of Stay (ALOS)</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['ALOS_25']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_ALOS_25']}</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">Total Outpatient Visits</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['OUT_25']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_OUT_25']}</td></tr>
            
            <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">III. HCPN & BUCAS</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">Apex/End-Referral Status</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['APEX']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_APEX']}</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">Operates BUCAS Center</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['BUCAS']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_BUCAS']}</td></tr>
            <tr><td style="border: 1px solid #333; padding: 5px;">BUCAS Coordinates</td><td style="border: 1px solid #333; padding: 5px; text-align: center;">{d['COORDS']}</td><td style="border: 1px solid #333; padding: 5px;">{d['RM_COORDS']}</td></tr>
        </table>
        <br><br><br>
        <table style="width:100%; text-align:center; font-size:14px;">
            <tr>
                <td style="width:50%;">__________________________<br><b>{u['user']}</b><br>{u['pos']}</td>
                <td style="width:50%;">__________________________<br><b>{d['Head_Name']}</b><br>{d['Head_Pos']}</td>
            </tr>
            <tr>
                <td style="padding-top:5px; color:#666;">(Signature Over Printed Name)</td>
                <td style="padding-top:5px; color:#666;">(Signature Over Printed Name)</td>
            </tr>
        </table>
        <center><br><button onclick="window.print()" style="padding:10px 20px; background:#222; color:white; border:none; border-radius:5px; cursor:pointer;">Print Submission</button></center>
    </div>"""
    st.components.v1.html(html, height=800, scrolling=True)

# --- 7. ROUTING, LOGIN, & DASHBOARD ---

def get_row_html(title, deadline, is_locked):
    """Generates a dynamic HTML row that changes color based on lock status."""
    bg_color = "rgba(239, 68, 68, 0.15)" if is_locked else "rgba(34, 197, 94, 0.15)"
    border_color = "#EF4444" if is_locked else "#22C55E"
    status_text = "🔒 CLOSED" if is_locked else "🟢 OPEN"
    
    return f"""
    <div style="background-color: {bg_color}; border-left: 5px solid {border_color}; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <div style="flex: 2; font-size: 1.1em; font-weight: bold; color: #E2E8F0;">{title}</div>
        <div style="flex: 1; font-family: monospace; color: #94A3B8;">{deadline}</div>
        <div style="flex: 1; font-weight: bold; color: {border_color}; text-align: right;">{status_text}</div>
    </div>
    """

def login_screen():
    st.markdown("<h2 style='text-align: center;'>🏥 HFDB Online Data Reporting and Submission Portal</h2>", unsafe_allow_html=True)
    if "pending_id" in st.session_state:
        st.warning("⚠️ **IMPORTANT: SAVE YOUR LOGIN CODE**")
        st.markdown(f"""
            <div style="background-color:#F0B216; padding:30px; border-radius:10px; text-align:center; border: 4px solid #000;">
                <h2 style="color:black; margin:0;">YOUR UNIQUE LOGIN ID:</h2>
                <h1 style="color:black; font-family:monospace; background:white; padding:15px; border:2px dashed #000;">{st.session_state.pending_id}</h1>
                <p style="color:black; font-size:18px;"><b>Copy this code now.</b> You will need this to access your data later. We do not store passwords, and the system will not show this again.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("✅ I HAVE COPIED AND SAVED MY CODE", use_container_width=True, type="primary"):
            st.session_state.user_id = st.session_state.pending_id
            st.session_state.user_info = st.session_state.pending_info
            del st.session_state.pending_id
            del st.session_state.pending_info
            st.success("Access Granted. Redirecting to Dashboard...")
            time.sleep(1)
            st.rerun()
        st.stop() 

    if "auth_mode" not in st.session_state:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="new-user-btn">', unsafe_allow_html=True)
            if st.button("🆕 NEW USER", use_container_width=True): st.session_state.auth_mode = "new"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            if st.button("🔑 EXISTING USER", use_container_width=True, type="primary"): st.session_state.auth_mode = "existing"; st.rerun()
    else:
        if st.button("⬅️ Back"): del st.session_state.auth_mode; st.rerun()
        
        if st.session_state.auth_mode == "new":
            try:
                h_list = conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List", ttl=0)["Facility_Name"].tolist()
            except: h_list = []
            h_name = st.selectbox("Hospital Name", [""] + sorted(h_list))
            h_level = st.selectbox("Level", ["", "Level 1", "Level 2", "Level 3", "Specialty"])
            u_name = st.text_input("Your Name")
            u_pos = st.text_input("Your Designation")
            
            if st.button("Register Profile", type="primary"):
                if not h_name or not u_name: st.error("Please fill in all fields.")
                else:
                    new_id = generate_custom_id()
                    try:
                        p_df = conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
                        new_profile = pd.DataFrame([{"User_ID": new_id, "Hospital_Name": h_name, "Service_Capability": h_level, "Encoder_Name": u_name, "Position": u_pos, "Year": 2026}])
                        conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=pd.concat([p_df, new_profile], ignore_index=True))
                        st.session_state.pending_id = new_id
                        st.session_state.pending_info = {"hosp": h_name, "level": h_level, "user": u_name, "pos": u_pos}
                        st.rerun()
                    except Exception as e: st.error(f"Could not save to database. {e}")
                        
        elif st.session_state.auth_mode == "existing":
            uid = st.text_input("Enter HFDB-2026 ID Code")
            if st.button("Enter Portal", type="primary"):
                p = conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
                if uid in p["User_ID"].astype(str).values:
                    r = p[p["User_ID"].astype(str) == uid].iloc[0]
                    st.session_state.user_id = uid
                    st.session_state.user_info = {"hosp": r["Hospital_Name"], "level": r["Service_Capability"], "user": r["Encoder_Name"], "pos": r["Position"]}
                    st.rerun()
                else: st.error("User ID not found in database. Check for typos.")

def dashboard():
    u = st.session_state.user_info
    st.markdown("<h2 style='text-align: center;'>🏥 HFDB Online Data Reporting and Submission Portal</h2>", unsafe_allow_html=True)
    st.info(f"Facility: **{u['hosp']}** ({u['level']}) | Encoder: **{u['user']}**")
    
    d1_str, d1_locked = get_module_config("Mod1")
    d2_str, d2_locked = get_module_config("Mod2")
    
    modules = [
        {"id": "Mod1", "title": "📊 Hospital Scorecard", "date": d1_str, "locked": d1_locked, "btn_class": "mod1-btn"},
        {"id": "Mod2", "title": "📈 Hospital Census & HCPN", "date": d2_str, "locked": d2_locked, "btn_class": "mod2-btn"}
    ]
    
    ongoing = [m for m in modules if not m["locked"]]
    lapsed = [m for m in modules if m["locked"]]

    # --- ONGOING MODULES ---
    if ongoing:
        st.markdown("### 🟢 Ongoing Data Submission Modules")
        for m in ongoing:
            st.markdown(get_row_html(m["title"], m["date"], m["locked"]), unsafe_allow_html=True)
            st.markdown(f'<div class="{m["btn_class"]}">', unsafe_allow_html=True)
            if st.button(f"OPEN {m['id'].upper()}", use_container_width=True, key=f"btn_on_{m['id']}"):
                st.session_state.current_module = m['id']
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)

    # --- LAPSED MODULES ---
    if lapsed:
        st.markdown("### 🔴 Lapsed Data Submission Modules")
        for m in lapsed:
            st.markdown(get_row_html(m["title"], m["date"], m["locked"]), unsafe_allow_html=True)
            st.markdown(f'<div class="{m["btn_class"]}">', unsafe_allow_html=True)
            if st.button(f"VIEW {m['id'].upper()} (READ-ONLY)", use_container_width=True, key=f"btn_lap_{m['id']}"):
                st.session_state.current_module = m['id']
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)
        
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True): 
        st.session_state.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 8. TRAFFIC CONTROLLER ---
if "user_id" not in st.session_state: 
    login_screen()
    
elif "current_module" in st.session_state:
    if st.button("🏠 Return to Dashboard"): 
        if "show_print" in st.session_state: del st.session_state.show_print
        if "expand_all" in st.session_state: del st.session_state.expand_all
        if "staged_data" in st.session_state: del st.session_state.staged_data
        del st.session_state.current_module
        st.rerun()
    
    if st.session_state.current_module == "Mod1":
        module_scorecard()
    elif st.session_state.current_module == "Mod2":
        module_census_data()
        
else: 
    dashboard()
