import streamlit as st
import pandas as pd
import time
import string
import random
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CORE CONFIG & UPGRADED AESTHETICS ---
st.set_page_config(
    page_title="Project FORT", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. PREMIUM CSS ENGINE ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #0E1117; color: #C9D1D9; }}
    
    .section-header-strat {{
        background-color: #1A365D; padding: 15px; border-radius: 10px 10px 0 0;
        text-align: center; border-bottom: 3px solid #3B82F6;
    }}
    .section-header-core {{
        background-color: #7B341E; padding: 15px; border-radius: 10px 10px 0 0;
        text-align: center; border-bottom: 3px solid #EF4444;
    }}

    div[data-testid="stExpander"] {{
        background-color: #161B22 !important; border: 1px solid #30363D !important;
        border-radius: 8px !important; margin-bottom: 12px; transition: 0.3s;
    }}
    div[data-testid="stExpander"]:hover {{ border-color: #58A6FF !important; }}
    
    div[data-testid="stExpander"] div[role="region"] {{
        background-color: #0D1117 !important; padding: 25px !important;
        border-top: 1px solid #30363D;
    }}

    /* Modern Primary Buttons (Blue Gradient) */
    button[kind="primary"] {{
        background: linear-gradient(135deg, #1d4ed8, #3b82f6) !important;
        color: white !important; border: none !important; border-radius: 8px !important;
        font-weight: bold !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
        transition: all 0.3s ease !important; height: 3.2em !important;
    }}
    button[kind="primary"]:hover {{
        transform: translateY(-2px) !important; box-shadow: 0 6px 12px rgba(0,0,0,0.4) !important;
        background: linear-gradient(135deg, #2563eb, #60a5fa) !important;
    }}

    /* Modern Secondary Buttons (Sleek Dark) */
    button[kind="secondary"] {{
        background-color: #21262D !important; color: white !important;
        border: 1px solid #30363D !important; border-radius: 8px !important;
        transition: all 0.3s ease !important; height: 3.2em !important;
    }}
    button[kind="secondary"]:hover {{
        border-color: #8B949E !important; background-color: #30363D !important;
        transform: translateY(-1px) !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- 3. CACHED & OPTIMIZED DATA FETCHING ---

@st.cache_data(ttl="1h")
def get_dropdown_data():
    """Caches dropdown options so we don't spam Google Sheets every rerun."""
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

# --- 4. HELPER FUNCTIONS ---

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

def submit_module_data(res_data, module_name="Mod1"):
    with st.spinner("Syncing to Cloud Database..."):
        try:
            try: df = conn.read(spreadsheet=SHEET_URL, worksheet=module_name, ttl=0)
            except: df = pd.DataFrame(columns=["User_ID", "Timestamp", "Hospital", "Encoder", "Scanned_PDF"])
                
            u = st.session_state.user_info
            new_record = {"User_ID": st.session_state.user_id, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Hospital": u["hosp"], "Encoder": u["user"]}
            
            # ONLY sync the raw data (res_data) to the database
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

# --- 5. THE SCORECARD (LOCAL STAGING ENGINE) ---

def module_scorecard():
    dd = get_dropdown_data()
    if dd is None:
        st.error("Sheet 'Mod1_DD' not found. Please check your Google Sheet tabs.")
        return

    # Use the locally staged data instead of fetching every rerun
    prev = st.session_state.staged_data 
    deadline_str, locked = get_module_config("Mod1")

    if locked:
        st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is in READ-ONLY mode.")

    st.markdown('<div class="section-header-strat"><h2>📊 STRATEGIC PERFORMANCE INDICATORS</h2></div>', unsafe_allow_html=True)
    
    # expanded=False forces ALL expanders to snap shut upon ANY rerun (like clicking Submit)
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

    st.markdown('<div class="section-header-core"><h2>🎯 CORE QUALITY INDICATORS</h2></div>', unsafe_allow_html=True)

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

    # --- ISOLATING RAW DATA FOR DATABASE ---
    # We DO NOT include the calculated percentages (SI6, SI7, CI1 etc.) here. 
    res_db = {
        "SI1": s1, "SI2": s2, "SI3_Cat": cat, "SI3_Src": src, "SI3_Stat": stat,
        "SI4_Status": iso1, "SI4_Audit": iso2, "SI5_24": pgs1, "SI5_25": pgs2,
        "SI6_N": s6n, "SI6_D": s6d, "SI7_N": s7n, "SI7_D": s7d, "SI8_N": s8n, "SI8_D": s8d,
        "CI1_N": ci1n, "CI1_D": ci1d, "CI2_N": ci2n, "CI2_D": ci2d, "CI3_N": ci3n, "CI3_D": ci3d,
        "CI4_N": ci4n, "CI4_D": ci4d, "CI5_N": ci5n, "CI5_D": ci5d, "CI6_N": ci6n, "CI6_D": ci6d,
        "Head_Name": h_name, "Head_Pos": h_pos
    }

    # --- COMPILED DATA FOR PRINT VIEW ONLY ---
    res_print = res_db.copy()
    res_print.update({
        "SI6": s6v, "SI7": s7v, "SI8": s8v,
        "CI1": ci1v, "CI2": ci2v, "CI3": ci3v,
        "CI4": ci4v, "CI5": ci5v, "CI6": ci6v
    })

    if not locked:
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🖨️ GENERATE REPORT & AUTO-SUBMIT", type="primary", use_container_width=True):
                if submit_module_data(res_db, "Mod1"): # Submits ONLY raw data
                    st.session_state.staged_data.update(res_db) # Keep local memory updated
                    st.session_state.show_print = True
                    st.rerun() # Rerunning instantly snaps all expanders shut
                
        with btn_col2:
            if st.button("💾 SUBMIT DATA ONLY", use_container_width=True):
                if submit_module_data(res_db, "Mod1"): # Submits ONLY raw data
                    st.session_state.staged_data.update(res_db) # Keep local memory updated
                    st.session_state.show_print = False
                    st.rerun() # Rerunning instantly snaps all expanders shut

    # --- PDF ATTACHMENT SECTION & PRINT VIEW ---
    if st.session_state.get("show_print", False):
        generate_print_view(res_print)
        st.divider()
        
        # --- NEW UPLOAD GATEWAY BUTTON ---
        st.markdown("### 📤 Step 1: Upload to Google Drive")
        st.info("Click the button below to open the official HFDB Drive Folder in a new tab. Upload your printed, signed, and scanned PDF report there.")
        st.link_button("📂 OPEN HFDB GOOGLE DRIVE FOLDER", "https://drive.google.com/drive/folders/15_dWyeXPxKXfGXekKgiLOaJ-9rIwthti?usp=drive_link", type="primary")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("### 🔗 Step 2: Attach Link to Submission")
        st.info("Once your file is uploaded to the Drive, copy the shareable link of your specific file and paste it below.")
        pdf_link = st.text_input("Paste Google Drive Link Here:")
        
        if st.button("💾 Encode Link", type="secondary"):
            if pdf_link:
                with st.spinner("Encoding link to database..."):
                    try:
                        df = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1", ttl=0)
                        mask = df["User_ID"].astype(str) == str(st.session_state.user_id)
                        if mask.any():
                            df.loc[mask, "Scanned_PDF"] = pdf_link
                            conn.update(spreadsheet=SHEET_URL, worksheet="Mod1", data=df)
                            st.success("✅ PDF Link successfully encoded to your module database!")
                        else:
                            st.error("Submission record not found. Please submit data first.")
                    except Exception as e:
                        st.error(f"Failed to attach link: {e}")
            else:
                st.warning("Please paste a link first before encoding.")

# --- 6. PRINT ENGINE ---
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
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 1: Functionality of PHU</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI1']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 2: Green Viability Assessment</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI2']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 3: Capital Formation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d['SI3_Cat']} ({d['SI3_Stat']})</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 4: ISO Accreditation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d['SI4_Status']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 5: PGS Accreditation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{d['SI5_25']}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 6: Specialty Centers</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI6']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 7: Zero Co-Payment</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI7']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">SI 8: Paperless EMR</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['SI8']:.2f}%</td></tr>
            
            <tr style="background-color: #7B341E; color: white;">
                <th colspan="2" style="padding: 10px; border: 1px solid #333; text-align: center;">II. CORE QUALITY INDICATORS</th>
            </tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 1: ER TAT (<4h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI1']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 2: Discharge TAT (<6h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI2']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 3: Lab TAT (<5h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI3']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 4: HAI Rate</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI4']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 5: Client Experience Survey</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI5']:.2f}%</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #333;">CI 6: Disbursement Rate</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{d['CI6']:.2f}%</td></tr>
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
    st.components.v1.html(html, height=950, scrolling=True)

# --- 7. ROUTING & LOGIN ---

def login_screen():
    st.title("🏥 HFDB Reporting Portal")
    
    if "pending_id" in st.session_state:
        st.warning("⚠️ **IMPORTANT: SAVE YOUR LOGIN CODE**")
        st.markdown(f"""
            <div style="background-color:#F0B216; padding:30px; border-radius:10px; text-align:center; border: 4px solid #000;">
                <h2 style="color:black; margin:0;">YOUR UNIQUE LOGIN ID:</h2>
                <h1 style="color:black; font-family:monospace; background:white; padding:15px; border:2px dashed #000;">{st.session_state.pending_id}</h1>
                <p style="color:black; font-size:18px;"><b>Copy this code now.</b> You will need this to access your data later. 
                We do not store passwords, and the system will not show this again.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("")
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
        if c1.button("🆕 NEW USER", use_container_width=True): st.session_state.auth_mode = "new"; st.rerun()
        if c2.button("🔑 EXISTING USER", use_container_width=True, type="primary"): st.session_state.auth_mode = "existing"; st.rerun()
    else:
        if st.button("⬅️ Back"): del st.session_state.auth_mode; st.rerun()
        
        if st.session_state.auth_mode == "new":
            h_list = conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List", ttl=0)["Facility_Name"].tolist()
            h_name = st.selectbox("Hospital Name", [""] + sorted(h_list))
            h_level = st.selectbox("Level", ["", "Level 1", "Level 2", "Level 3", "Specialty"])
            u_name = st.text_input("Your Name")
            u_pos = st.text_input("Your Designation")
            
            if st.button("Register Profile", type="primary"):
                if not h_name or not u_name:
                    st.error("Please fill in all fields.")
                else:
                    new_id = generate_custom_id()
                    try:
                        p_df = conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
                        new_profile = pd.DataFrame([{"User_ID": new_id, "Hospital_Name": h_name, "Service_Capability": h_level, "Encoder_Name": u_name, "Position": u_pos, "Year": 2026}])
                        conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=pd.concat([p_df, new_profile], ignore_index=True))
                        
                        st.session_state.pending_id = new_id
                        st.session_state.pending_info = {"hosp": h_name, "level": h_level, "user": u_name, "pos": u_pos}
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not save to database. {e}")
                        
        elif st.session_state.auth_mode == "existing":
            uid = st.text_input("Enter HFDB-2026 ID Code")
            if st.button("Enter Portal", type="primary"):
                p = conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
                if uid in p["User_ID"].astype(str).values:
                    r = p[p["User_ID"].astype(str) == uid].iloc[0]
                    st.session_state.user_id = uid
                    st.session_state.user_info = {"hosp": r["Hospital_Name"], "level": r["Service_Capability"], "user": r["Encoder_Name"], "pos": r["Position"]}
                    st.rerun()
                else:
                    st.error("User ID not found in database. Check for typos.")

def dashboard():
    u = st.session_state.user_info
    st.title("🏥 Project FORT Dashboard")
    st.info(f"Facility: **{u['hosp']}** ({u['level']}) | Encoder: **{u['user']}**")
    
    deadline_str, locked = get_module_config("Mod1")
    status = "🔒 CLOSED" if locked else "🟢 OPEN"
    
    st.markdown("---")
    st.markdown("### 📋 Available Modules")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1: st.markdown("**Module**")
    with col2: st.markdown("**Deadline**")
    with col3: st.markdown("**Status**")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1: st.markdown("Hospital Scorecard (Mod1)")
    with col2: st.markdown(f"`{deadline_str}`")
    with col3: st.markdown(f"**{status}**")
    
    if st.button("📊 Open Scorecard", use_container_width=True, type="primary"):
        with st.spinner("Loading your data into memory..."):
            st.session_state.staged_data = get_previous_entry("Mod1")
            st.session_state.current_module = "Mod1"
        st.rerun()
        
    st.markdown("---")
    if st.button("Logout"): st.session_state.clear(); st.rerun()

if "user_id" not in st.session_state: login_screen()
elif "current_module" in st.session_state:
    if st.button("🏠 Return to Dashboard"): 
        if "show_print" in st.session_state: del st.session_state.show_print
        if "staged_data" in st.session_state: del st.session_state.staged_data
        del st.session_state.current_module
        st.rerun()
    module_scorecard()
else: dashboard()
