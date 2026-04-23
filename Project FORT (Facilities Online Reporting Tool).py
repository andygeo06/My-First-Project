import streamlit as st
import uuid
import pandas as pd
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. THE PAINT PALETTE ---
COLORS = {
    "main_background": "#0E1117",
    "card_background": "#21262D",
    "card_text": "#C9D1D9",
    "card_hover": "#30363D",
    "new_user_btn": "#1F6FEB",
    "existing_user_btn": "#238636",
    "border_color": "#30363D"
}

# --- 2. CONFIG & CONNECTION ---
st.set_page_config(page_title="Project FORT", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. DATABASE FUNCTIONS ---

def get_all_profiles():
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet="User_Profiles", ttl=0)
    except:
        return pd.DataFrame(columns=["User_ID", "Hospital_Name", "Service_Capability", "Encoder_Name", "Position", "Year", "Created_At"])

def get_facility_list():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Facility_List", ttl=0)
        return sorted(df["Facility_Name"].dropna().unique().tolist())
    except:
        return []

def get_all_deadlines():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Config", ttl=0)
        return pd.Series(df.Deadline_Date.values, index=df.Module_Key).to_dict()
    except:
        return {}

def save_new_profile(user_id, h_name, h_level, u_name, pos):
    try:
        existing = get_all_profiles()
        new_row = pd.DataFrame([{
            "User_ID": str(user_id),
            "Hospital_Name": str(h_name),
            "Service_Capability": str(h_level),
            "Encoder_Name": str(u_name),
            "Position": str(pos),
            "Year": 2026,
            "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        updated_df = pd.concat([existing, new_row], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=updated_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return False

# --- 4. UI: LOGIN & REGISTRATION ---

def login_screen():
    st.title("🏥 HFDB Online Data Submission Portal")
    st.divider()

    if "auth_mode" not in st.session_state:
        st.subheader("Please choose an option to begin:")
        c1, c2 = st.columns(2)
        if c1.button("🆕\n\nNEW USER\n\nCreate a Profile", use_container_width=True):
            st.session_state.auth_mode = "new"
            st.rerun()
        if c2.button("🔑\n\nEXISTING USER\n\nContinue Work", use_container_width=True, type="primary"):
            st.session_state.auth_mode = "existing"
            st.rerun()
    else:
        if st.button("⬅️ Back"):
            del st.session_state.auth_mode
            st.rerun()

        if st.session_state.auth_mode == "new":
            st.subheader("📝 Register New Submitter Profile")
            facility_list = get_facility_list()
            h_name = st.selectbox("Select Your Hospital:", options=[""] + facility_list)
            h_level = st.selectbox("Service Capability (Hospital Level):", options=["", "Level 1", "Level 2", "Level 3"])
            u_name = st.text_input("Name of Encoder:")
            pos = st.text_input("Official Designation/Position:")
            
            if st.button("🚀 Register & Generate Code", type="primary"):
                if not h_name or not h_level or not u_name or not pos:
                    st.error("All fields are required.")
                else:
                    profiles = get_all_profiles()
                    if h_name.upper() in profiles["Hospital_Name"].str.upper().tolist():
                        st.error(f"🛑 Error: {h_name} already has an account.")
                        time.sleep(2)
                        st.session_state.auth_mode = "existing"
                        st.rerun()
                    else:
                        new_id = f"HFDB-2026-{uuid.uuid4().hex[:8].upper()}"
                        if save_new_profile(new_id, h_name, h_level, u_name, pos):
                            st.session_state.generated_id = new_id
                            st.session_state.reg_success = True
                            st.session_state.temp_info = {"hosp": h_name, "level": h_level, "user": u_name, "pos": pos}
                            st.rerun()

            if st.session_state.get("reg_success"):
                st.success("✅ Profile Registered! SAVE THIS CODE:")
                st.code(st.session_state.generated_id)
                if st.button("Enter Dashboard"):
                    st.session_state.user_id = st.session_state.generated_id
                    st.session_state.user_info = st.session_state.temp_info
                    st.rerun()

        elif st.session_state.auth_mode == "existing":
            st.subheader("🔓 Access Your Profile")
            input_id = st.text_input("Enter Identification Code:")
            if st.button("Verify & Enter Portal", type="primary"):
                profiles = get_all_profiles()
                if input_id in profiles["User_ID"].astype(str).tolist():
                    row = profiles[profiles["User_ID"] == input_id].iloc[0]
                    st.session_state.user_id = input_id
                    st.session_state.user_info = {
                        "hosp": row["Hospital_Name"], 
                        "level": row["Service_Capability"],
                        "user": row["Encoder_Name"],
                        "pos": row["Position"]
                    }
                    st.rerun()
                else:
                    st.error("Invalid Code.")

# --- 5. MODULE 1: SCORECARD ENGINE ---

def module_scorecard():
    try:
        dd = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1_DD", ttl=0)
    except:
        st.error("Error loading Dropdown sources.")
        return

    # Real-time Percent Calc Helper
    def score_calc(n, d, label):
        val = (n / d * 100) if d > 0 else 0
        st.markdown(f"**Result {label}: `{val:.2f}%`**")
        return val

    st.markdown("### 📋 STRATEGIC INDICATORS")
    
    with st.expander("1-2: Functionality & Green Viability", expanded=True):
        si1 = st.number_input("SI 1: % Functionality of PHU", 0.0, 100.0)
        si2 = st.number_input("SI 2: Green Rating (%)", 0.0, 100.0)

    with st.expander("3: Capital Formation"):
        c1, c2 = st.columns(2)
        cat = c1.selectbox("Category", dd["Infrastructure, Equipment"].dropna().unique())
        src = c2.selectbox("Fund Source", dd["Fund Source"].dropna().unique())
        if "Infrastructure" in cat:
            stat = st.selectbox("State of Completion", dd["State of Completion (Infra)"].dropna().unique())
        else:
            stat = st.selectbox("State of Completion", dd["State of Completion (Equip)"].dropna().unique())

    with st.expander("4-5: ISO & PGS Accreditation"):
        c1, c2 = st.columns(2)
        iso_acc = c1.selectbox("ISO 9001:2015 Status", dd["ISO Accreditation"].dropna().unique())
        iso_aud = c2.selectbox("Internal Quality Audit", dd["Internal Quality Audit"].dropna().unique())
        pgs24 = c1.selectbox("2024 PGS Status", dd["PGS 2024"].dropna().unique())
        pgs25 = c2.selectbox("2025 PGS Status", dd["PGS 2025"].dropna().unique())

    with st.expander("6-8: Specialty Centers, Zero Co-Pay, Paperless EMR"):
        st.info("Input Numerator and Denominator for auto-calculation.")
        s6_n = st.number_input("SI 6: Functional Specialty Centers", 0)
        s6_d = st.number_input("SI 6: Target Specialty Centers", 1)
        si6_val = score_calc(s6_n, s6_d, "(Specialty)")
        
        st.divider()
        s7_n = st.number_input("SI 7: Patients with Zero Co-Pay", 0)
        s7_d = st.number_input("SI 7: Total Basic Accommodation Patients", 1)
        si7_val = score_calc(s7_n, s7_d, "(Zero Co-Pay)")

        st.divider()
        s8_n = st.number_input("SI 8: Areas with Paperless EMR", 0)
        s8_d = st.number_input("SI 8: Expected Paperless Areas", 1)
        si8_val = score_calc(s8_n, s8_d, "(Paperless EMR)")

    st.markdown("### 🎯 CORE INDICATORS")
    
    with st.expander("1-3: Turnaround Times (ER, Discharge, Lab)"):
        c1, c2, c3 = st.columns(3)
        ci1_n = c1.number_input("CI 1: ER <4hrs Patients", 0)
        ci1_d = c1.number_input("CI 1: Total ER Patients", 1)
        ci1_val = score_calc(ci1_n, ci1_d, "(ER TAT)")
        
        ci2_n = c2.number_input("CI 2: Discharge <6hrs", 0)
        ci2_d = c2.number_input("CI 2: Total Discharged", 1)
        ci2_val = score_calc(ci2_n, ci2_d, "(Discharge TAT)")

        ci3_n = c3.number_input("CI 3: Lab Result <5hrs", 0)
        ci3_d = c3.number_input("CI 3: Total Lab Tests", 1)
        ci3_val = score_calc(ci3_n, ci3_d, "(Lab TAT)")

    with st.expander("4-6: HAI, Experience, & Disbursement"):
        ci4_n = st.number_input("CI 4: Inpatients with HAI", 0)
        ci4_d = st.number_input("CI 4: Total Discharges/Deaths (>48hrs)", 1)
        ci4_val = score_calc(ci4_n, ci4_d, "(HAI Rate)")

        ci5_n = st.number_input("CI 5: Outstanding Ratings", 0)
        ci5_d = st.number_input("CI 5: Total Respondents", 1)
        ci5_val = score_calc(ci5_n, ci5_d, "(Experience Score)")

        ci6_n = st.number_input("CI 6: Total Disbursement", 0.0)
        ci6_d = st.number_input("CI 6: Total Allocation (NCA+NTCA)", 1.0)
        ci6_val = score_calc(ci6_n, ci6_d, "(Disbursement Rate)")

    st.markdown("### ✍️ SIGNATURE & EXPORT")
    c1, c2 = st.columns(2)
    h_head = c1.text_input("Name of Head of Facility:")
    h_pos = c2.text_input("Designation of Head of Facility:")

    if st.button("🖨️ Generate Professional Report", type="primary"):
        # Packaging all data for the print function
        report_data = {
            "si1": si1, "si2": si2, "cat": cat, "stat": stat, "src": src,
            "ci1": ci1_val, "ci2": ci2_val, "ci3": ci3_val, "ci4": ci4_val,
            "ci5": ci5_val, "ci6": ci6_val, "h_head": h_head, "h_pos": h_pos
        }
        generate_print_view(report_data)

# --- 6. PRINT ENGINE ---

def generate_print_view(data):
    user = st.session_state.user_info
    html = f"""
    <div style="font-family: 'Segoe UI', Arial; padding: 30px; color: black; background: white; border: 2px solid #333;">
        <center>
            <h1 style="margin:0; color: #1a4d2e;">2025 DOH HOSPITAL SCORECARD</h1>
            <h3 style="margin:5px 0;">{user['hosp']} ({user['level']})</h3>
            <p>Official Submission Report</p>
            <hr>
        </center>
        <h4>I. STRATEGIC PERFORMANCE</h4>
        <p><b>SI 1 (PHU):</b> {data['si1']}% | <b>SI 2 (Green):</b> {data['si2']}%</p>
        <p><b>SI 3 (CapForm):</b> {data['cat']} - {data['stat']} (Fund: {data['src']})</p>
        
        <h4>II. CORE PERFORMANCE INDICATORS</h4>
        <table style="width:100%; border-collapse: collapse; border: 1px solid #ddd;">
            <tr style="background: #f2f2f2;"><th>Indicator</th><th>Performance Score</th></tr>
            <tr><td>ER Turnaround Time (<4hrs)</td><td align="center">{data['ci1']:.2f}%</td></tr>
            <tr><td>Discharge Process (<6hrs)</td><td align="center">{data['ci2']:.2f}%</td></tr>
            <tr><td>Lab Result TAT (<5hrs)</td><td align="center">{data['ci3']:.2f}%</td></tr>
            <tr><td>HAI Rate</td><td align="center">{data['ci4']:.2f}%</td></tr>
            <tr><td>Client Experience Score</td><td align="center">{data['ci5']:.2f}%</td></tr>
            <tr><td>Disbursement Rate</td><td align="center">{data['ci6']:.2f}%</td></tr>
        </table>
        <br><br><br>
        <table style="width:100%;">
            <tr>
                <td align="center">__________________________<br><b>{user['user']}</b><br>{user['pos']}</td>
                <td align="center">__________________________<br><b>{data['h_head']}</b><br>{data['h_pos']}</td>
            </tr>
            <tr>
                <td align="center"><small>(Signature over Printed Name)</small></td>
                <td align="center"><small>(Signature over Printed Name)</small></td>
            </tr>
        </table>
    </div>
    <br>
    <button onclick="window.print()" style="padding: 10px 20px; background: #238636; color: white; border: none; cursor: pointer;">
        Confirm & Print to PDF
    </button>
    """
    st.components.v1.html(html, height=1000, scrolling=True)

# --- 7. DASHBOARD & ROUTER ---

def dashboard():
    st.title("🏥 Module Selection")
    user = st.session_state.user_info
    st.info(f"Facility: **{user['hosp']}** ({user['level']}) | User: **{user['user']}**")
    
    deadlines = get_all_deadlines()
    modules = [
        {"key": "Mod1", "name": "Hospital Scorecard", "icon": "📊"},
        {"key": "Mod2", "name": "Financial Data", "icon": "💰"},
        {"key": "Mod3", "name": "Hospital MOOE", "icon": "🏥"}
    ]
    
    cols = st.columns(3)
    for i, mod in enumerate(modules):
        d_date = deadlines.get(mod['key'], "TBD")
        with cols[i]:
            if st.button(f"{mod['icon']} {mod['name']}\n\n📅 Due: {d_date}\nStatus: ⚪ Pending", key=mod['key'], use_container_width=True):
                st.session_state.current_module = mod
                st.rerun()

if "user_id" not in st.session_state:
    login_screen()
elif "current_module" in st.session_state:
    if st.button("🏠 Home"):
        del st.session_state.current_module
        st.rerun()
    st.divider()
    if st.session_state.current_module['key'] == "Mod1":
        module_scorecard()
    else:
        st.write("Module under construction.")
else:
    dashboard()

# --- 8. CSS ENGINE ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {COLORS['main_background']}; color: {COLORS['card_text']}; }}
    div.stButton > button {{
        height: auto; padding: 20px 10px !important; border-radius: 12px;
        background-color: {COLORS['card_background']}; color: {COLORS['card_text']};
        border: 1px solid {COLORS['border_color']}; transition: 0.3s;
    }}
    div.stButton > button:hover {{ background-color: {COLORS['card_hover']} !important; border-color: {COLORS['new_user_btn']} !important; }}
</style>
""", unsafe_allow_html=True)
