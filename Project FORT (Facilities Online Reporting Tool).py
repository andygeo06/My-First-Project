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

# --- 2. CSS ENGINE (Strictly Individualized Spacing) ---
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

    /* Individual Expander Styling */
    div[data-testid="stExpander"] {{
        background-color: #161B22 !important; 
        border: 1px solid #30363D !important;
        border-radius: 8px !important; 
        margin-bottom: 15px; /* Added breathing room between boxes */
    }}
    
    div[data-testid="stExpander"] div[role="region"] {{
        background-color: #0D1117 !important; 
        padding: 30px !important;
    }}

    /* Action Button: Emerald Green (Print/Submit) */
    button[kind="primary"] {{
        background-color: #059669 !important; 
        color: white !important;
        border: none !important; 
        font-weight: bold !important; 
        height: 3.8em;
    }}
    
    /* Action Button: Amber Orange (Submit Only) */
    button[kind="secondary"] {{
        background-color: #D97706 !important; 
        color: white !important;
        border: none !important; 
        font-weight: bold !important; 
        height: 3.8em;
    }}

    button:hover {{ opacity: 0.9; transition: 0.3s; }}
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
    st.markdown(f"📈 **{label} Performance:** `{val:.2f}%`")
    return val

def submit_module_data(res_data, module_name="Mod1"):
    try:
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
        except:
            df = pd.DataFrame(columns=["User_ID", "Timestamp", "Hospital", "Encoder"])
            
        u = st.session_state.user_info
        new_record = {
            "User_ID": st.session_state.user_id,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Hospital": u["hosp"],
            "Encoder": u["user"]
        }
        new_record.update(res_data)
        
        # Remove existing entry for this user ID to prevent duplicates
        if "User_ID" in df.columns:
            df = df[df["User_ID"].astype(str) != str(st.session_state.user_id)]
            
        updated_df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet=module_name, data=updated_df)
        
        # COLLAPSE TRIGGER: Minimize all expanders after action
        st.session_state.expand_all = False
        st.toast(f"Data saved and expanders minimized.", icon="✅")
        return True
    except Exception as e:
        st.error(f"Sync error: {e}")
        return False

# --- 4. THE INDIVIDUALIZED SCORECARD ---

def module_scorecard():
    # Track UI State
    if "expand_all" not in st.session_state:
        st.session_state.expand_all = True
    
    is_exp = st.session_state.expand_all

    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
        dd.columns = dd.columns.str.strip()
    except:
        st.error("Missing Data Dictionary.")
        return

    # --- STRATEGIC INDICATORS (1-8) ---
    st.markdown('<div class="section-header-strat"><h2>📊 STRATEGIC PERFORMANCE INDICATORS</h2></div>', unsafe_allow_html=True)
    
    with st.expander("🔹 SI 1: % Functionality of PHU", expanded=is_exp):
        s1 = clean_pct(st.text_input("Enter Percentage", value="0%", key="si1"))
        
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)", expanded=is_exp):
        s2 = clean_pct(st.text_input("Enter GVA Score", value="0%", key="si2"))

    with st.expander("🔹 SI 3: Capital Formation", expanded=is_exp):
        si3_cat = st.selectbox("Category", dd["Indicator 3, DD1"].dropna().unique(), key="s3c")
        si3_src = st.selectbox("Fund Source", dd["Indicator 3, DD2"].dropna().unique(), key="s3f")
        si3_stat_col = "Indicator 3, DD3.a" if "Infrastructure" in str(si3_cat) else "Indicator 3, DD3.b"
        si3_stat = st.selectbox("Status", dd[si3_stat_col].dropna().unique(), key="s3s")

    with st.expander("🔹 SI 4: ISO 9001:2015 Accreditation", expanded=is_exp):
        s4 = st.selectbox("Current ISO Status", dd["Indicator 4, DD1"].dropna().unique(), key="s4")

    with st.expander("🔹 SI 5: PGS Accreditation Status", expanded=is_exp):
        s5 = st.selectbox("2025 PGS Target Status", dd["Indicator 5, DD2"].dropna().unique(), key="s5")

    with st.expander("🔹 SI 6: Functional Specialty Centers", expanded=is_exp):
        s6n = st.number_input("Number of Functional Centers", 0, key="s6n")
        s6d = st.number_input("Total Target Centers", 1, key="s6d")
        s6v = score_calc(s6n, s6d, "SI 6")

    with st.expander("🔹 SI 7: Zero Co-Payment Patients", expanded=is_exp):
        s7n = st.number_input("Count of Zero Co-Pay Patients", 0, key="s7n")
        s7d = st.number_input("Total Basic Patients", 1, key="s7d")
        s7v = score_calc(s7n, s7d, "SI 7")

    with st.expander("🔹 SI 8: Paperless EMR Areas", expanded=is_exp):
        s8n = st.number_input("Count of Paperless Clinical Areas", 0, key="s8n")
        s8d = st.number_input("Total Expected Areas", 1, key="s8d")
        s8v = score_calc(s8n, s8d, "SI 8")

    # --- CORE INDICATORS (1-6) ---
    st.markdown('<div class="section-header-core"><h2>🎯 CORE QUALITY INDICATORS</h2></div>', unsafe_allow_html=True)

    with st.expander("🔸 CI 1: ER Turnaround Time (<4 hrs)", expanded=is_exp):
        ci1n = st.number_input("ER Pts Seen <4h", 0, key="c1n")
        ci1d = st.number_input("Total ER Patients Seen", 1, key="c1d")
        ci1v = score_calc(ci1n, ci1d, "ER TAT")

    with st.expander("🔸 CI 2: Discharge Turnaround (<6 hrs)", expanded=is_exp):
        ci2n = st.number_input("Discharges within 6h", 0, key="c2n")
        ci2d = st.number_input("Total Discharges", 1, key="c2d")
        ci2v = score_calc(ci2n, ci2d, "Discharge TAT")

    with st.expander("🔸 CI 3: Lab Result Turnaround (<5 hrs)", expanded=is_exp):
        ci3n = st.number_input("Lab Results within 5h", 0, key="c3n")
        ci3d = st.number_input("Total Lab Tests Conducted", 1, key="c3d")
        ci3v = score_calc(ci3n, ci3d, "Lab TAT")

    with st.expander("🔸 CI 4: Healthcare Associated Infection Rate", expanded=is_exp):
        ci4n = st.number_input("Confirmed HAI Cases", 0, key="c4n")
        ci4d = st.number_input("Total Discharges & Deaths >48h", 1, key="c4d")
        ci4v = score_calc(ci4n, ci4d, "HAI Rate")

    with st.expander("🔸 CI 5: Client Experience Survey", expanded=is_exp):
        ci5n = st.number_input("Count of Outstanding Ratings", 0, key="c5n")
        ci5d = st.number_input("Total Survey Respondents", 1, key="c5d")
        ci5v = score_calc(ci5n, ci5d, "CES")

    with st.expander("🔸 CI 6: Disbursement Rate", expanded=is_exp):
        ci6n = st.number_input("Actual Disbursement", 0.0, key="c6n")
        ci6d = st.number_input("Total Final Allocation", 1.0, key="c6d")
        ci6v = score_calc(ci6n, ci6d, "Disbursement")

    st.divider()
    h_name = st.text_input("Name of Head of Facility (for Report)")
    h_pos = st.text_input("Designation of Head of Facility")

    # Result Dictionary
    res = {
        "SI1": s1, "SI2": s2, "SI3_Cat": si3_cat, "SI3_Stat": si3_stat,
        "SI4": s4, "SI5": s5, "SI6": s6v, "SI7": s7v, "SI8": s8v,
        "CI1": ci1v, "CI2": ci2v, "CI3": ci3v, "CI4": ci4v, "CI5": ci5v, "CI6": ci6v,
        "Head_Name": h_name, "Head_Pos": h_pos
    }

    # --- ACTION BUTTONS (The Contrast Pair) ---
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🖨️ GENERATE REPORT & AUTO-SUBMIT", type="primary", use_container_width=True):
            if submit_module_data(res, "Mod1"):
                st.session_state.show_print = True
                st.rerun()
    with btn_col2:
        if st.button("💾 SUBMIT DATA ONLY", type="secondary", use_container_width=True):
            if submit_module_data(res, "Mod1"):
                st.rerun()

    # Post-Submission View
    if st.session_state.get("show_print", False):
        if st.button("🏠 RETURN TO DASHBOARD", use_container_width=True):
            st.session_state.expand_all = True
            del st.session_state.show_print
            del st.session_state.current_module
            st.rerun()
        generate_print_view(res)

# --- 5. SYSTEM LOGIC (Login, Dashboard, Print) ---

def generate_print_view(d):
    u = st.session_state.user_info
    html = f"""
    <div style="font-family: Arial; padding: 40px; background: white; color: black; border: 2px solid #333; max-width: 800px; margin: 0 auto; text-align: center;">
        <h2 style="margin-bottom:5px;">2025 DOH HOSPITAL SCORECARD</h2>
        <h3 style="margin-top:0;">{u['hosp']}</h3><hr>
        <table style="width:100%; border-collapse: collapse; margin-top: 20px;">
            <tr style="background:#f2f2f2;"><th style="padding:10px; border:1px solid #ddd;">Indicator</th><th style="padding:10px; border:1px solid #ddd;">Result</th></tr>
            <tr><td style="padding:10px; border:1px solid #ddd; text-align:left;">PHU Functionality</td><td style="padding:10px; border:1px solid #ddd;">{d['SI1']:.2f}%</td></tr>
            <tr><td style="padding:10px; border:1px solid #ddd; text-align:left;">Green Viability</td><td style="padding:10px; border:1px solid #ddd;">{d['SI2']:.2f}%</td></tr>
            <tr><td style="padding:10px; border:1px solid #ddd; text-align:left;">ER TAT (<4h)</td><td style="padding:10px; border:1px solid #ddd;">{d['CI1']:.2f}%</td></tr>
            <tr><td style="padding:10px; border:1px solid #ddd; text-align:left;">Client Experience</td><td style="padding:10px; border:1px solid #ddd;">{d['CI5']:.2f}%</td></tr>
            <tr><td style="padding:10px; border:1px solid #ddd; text-align:left;">Budget Disbursement</td><td style="padding:10px; border:1px solid #ddd;">{d['CI6']:.2f}%</td></tr>
        </table>
        <br><br>
        <div style="display: flex; justify-content: space-around;">
            <div>____________________<br><b>{u['user']}</b><br>Encoder</div>
            <div>____________________<br><b>{d['Head_Name']}</b><br>{d['Head_Pos']}</div>
        </div>
        <br><br><button onclick="window.print()" style="padding:12px 25px; background:#059669; color:white; border:none; border-radius:5px; cursor:pointer;">Confirm & Print to PDF</button>
    </div>"""
    st.components.v1.html(html, height=800, scrolling=True)

def login_screen():
    st.title("🏥 HFDB Reporting Portal")
    if "auth_mode" not in st.session_state:
        c1, c2 = st.columns(2)
        if c1.button("🆕 REGISTER NEW PROFILE", use_container_width=True): 
            st.session_state.auth_mode = "new"
            st.rerun()
        if c2.button("🔑 LOGIN EXISTING ID", use_container_width=True, type="primary"): 
            st.session_state.auth_mode = "existing"
            st.rerun()
    else:
        if st.button("⬅️ Back"): del st.session_state.auth_mode; st.rerun()
        if st.session_state.auth_mode == "new":
            facilities = conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List")["Facility_Name"].tolist()
            h_name = st.selectbox("Select Hospital Name", [""] + sorted(facilities))
            h_level = st.selectbox("Facility Level", ["", "Level 1", "Level 2", "Level 3", "Specialty"])
            u_name = st.text_input("Full Name of Encoder")
            u_pos = st.text_input("Position/Designation")
            if st.button("Create Profile"):
                new_id = f"FORT-{uuid.uuid4().hex[:6].upper()}"
                st.session_state.user_id = new_id
                st.session_state.user_info = {"hosp": h_name, "level": h_level, "user": u_name, "pos": u_pos}
                st.success(f"Registered! Your ID is: {new_id}")
                time.sleep(1.5); st.rerun()
        elif st.session_state.auth_mode == "existing":
            uid = st.text_input("Enter your Portal ID Code")
            if st.button("Access Dashboard"):
                p = conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
                if uid in p["User_ID"].astype(str).values:
                    r = p[p["User_ID"].astype(str) == uid].iloc[0]
                    st.session_state.user_id = uid
                    st.session_state.user_info = {"hosp": r["Hospital_Name"], "level": r["Service_Capability"], "user": r["Encoder_Name"], "pos": r["Position"]}
                    st.rerun()
                else: st.error("ID not found.")

def dashboard():
    u = st.session_state.user_info
    st.title("🏥 Project FORT Dashboard")
    st.info(f"Connected: **{u['hosp']}** | User: **{u['user']}**")
    if st.button("📊 Hospital Scorecard", use_container_width=True):
        st.session_state.current_module = "Mod1"
        st.session_state.expand_all = True
        st.rerun()
    if st.button("Logout"): st.session_state.clear(); st.rerun()

# --- APP ROUTING ---
if "user_id" not in st.session_state: login_screen()
elif "current_module" in st.session_state:
    if st.button("🏠 Home"): 
        if "show_print" in st.session_state: del st.session_state.show_print
        del st.session_state.current_module; st.rerun()
    module_scorecard()
else: dashboard()
