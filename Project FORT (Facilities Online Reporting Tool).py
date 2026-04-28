import streamlit as st
import pandas as pd
import time
import string
import random
import uuid
from datetime import datetime, timedelta, timezone
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

# --- 1. CORE CONFIG & COMPACT THEME ---
st.set_page_config(page_title="Project FORT", layout="wide", initial_sidebar_state="expanded")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YSiRzktbwF6Ptwq98xzFkmbY4x61zbz5uD80mTubaqM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. PREMIUM COMPACT CSS ENGINE (SILVER BULLET) ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #0E1117; color: #C9D1D9; }}
    .block-container {{ padding-top: 2.5rem !important; padding-bottom: 2.5rem !important; }}
    .sticky-header {{ position: -webkit-sticky; position: sticky; top: 2.8rem; background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(10px); padding: 8px 15px; border-radius: 8px; border: 1px solid #3B82F6; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); z-index: 9999; margin-bottom: 15px; text-align: center; }}
    .sticky-title {{ margin: 0; color: #F8FAFC; font-size: 1.1rem; font-weight: bold; }}
    .sticky-sub {{ margin: 0; color: #94A3B8; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }}
    
    /* COMPRESSED HEADERS */
    .section-header-strat {{ background-color: #1A365D; padding: 6px; border-radius: 6px 6px 0 0; text-align: center; border-bottom: 3px solid #3B82F6; margin-bottom: 8px; }}
    .section-header-core {{ background-color: #7B341E; padding: 6px; border-radius: 6px 6px 0 0; text-align: center; border-bottom: 3px solid #EF4444; margin-bottom: 8px; }}
    .section-header-green {{ background-color: #064E3B; padding: 6px; border-radius: 6px 6px 0 0; text-align: center; border-bottom: 3px solid #10B981; margin-bottom: 8px; }}
    
    div[data-testid="stExpander"] {{ background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 6px !important; margin-bottom: 6px; transition: 0.3s; }}
    div[data-testid="stExpander"]:hover {{ border-color: #58A6FF !important; }}
    div[data-testid="stExpander"] div[role="region"] {{ background-color: #0D1117 !important; padding: 10px !important; border-top: 1px solid #30363D; }}
    div.element-container:has(.marker) {{ display: none !important; }}
    
    /* COMPRESSED BUTTON HEIGHTS */
    div.element-container:has(.marker-green) + div.element-container button {{ background-color: #15803d !important; color: white !important; border: 1px solid #22c55e !important; font-weight: bold !important; height: 2.2em !important; min-height: 2.2em !important; width: 100% !important; transition: 0.3s !important; }}
    div.element-container:has(.marker-green) + div.element-container button:hover {{ background-color: #166534 !important; border-color: #FFFFFF !important; }}
    div.element-container:has(.marker-blue) + div.element-container button {{ background-color: #1A365D !important; color: white !important; border: 1px solid #3B82F6 !important; font-weight: bold !important; height: 2.2em !important; min-height: 2.2em !important; width: 100% !important; transition: 0.3s !important; }}
    div.element-container:has(.marker-blue) + div.element-container button:hover {{ background-color: #2563EB !important; border-color: #FFFFFF !important; }}
    div.element-container:has(.marker-red) + div.element-container button {{ background-color: #dc2626 !important; color: white !important; border: 1px solid #ef4444 !important; font-weight: bold !important; height: 2.2em !important; min-height: 2.2em !important; width: 100% !important; transition: 0.3s !important; }}
    div.element-container:has(.marker-red) + div.element-container button:hover {{ background-color: #991b1b !important; border-color: #FFFFFF !important; }}
    div.element-container:has(.marker-amber) + div.element-container button {{ background-color: #d97706 !important; color: white !important; border: 1px solid #f59e0b !important; font-weight: bold !important; height: 2.2em !important; min-height: 2.2em !important; width: 100% !important; transition: 0.3s !important; }}
    div.element-container:has(.marker-amber) + div.element-container button:hover {{ background-color: #b45309 !important; border-color: #FFFFFF !important; }}
    
    /* COMPACT ALERT & BANNER CSS */
    div[data-testid="stAlert"] {{ padding: 0.2rem 1rem !important; }}
    div[data-testid="stAlert"] > div {{ align-items: center !important; }}
    div[data-testid="stAlert"] p {{ margin: 0 !important; padding-bottom: 0.1rem !important; line-height: 1.4 !important; font-size: 0.95em; }}
    
    /* COMPACT CHAT CSS */
    div[data-testid="stChatMessage"] {{ padding: 0.5rem 0.5rem !important; }}
    div[data-testid="stChatMessageContent"] {{ gap: 0.1rem !important; }}
    div[data-testid="stChatMessage"] .stMarkdown p {{ margin-bottom: 0.2rem !important; font-size: 0.95em; }}
    div[data-testid="stChatMessage"] [data-testid="stIconNode"] {{ width: 1.5rem !important; height: 1.5rem !important; }}
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE & MATH HELPERS ---
@st.cache_data(ttl=5)
def get_static_sheet(sheet_name):
    try: return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name)
    except: return pd.DataFrame()

def clear_app_memory():
    st.cache_data.clear()

def get_module_config(mod_id):
    df = get_static_sheet("Config")
    if not df.empty and "Module" in df.columns:
        row = df[df["Module"] == mod_id]
        if not row.empty:
            dl = str(row.iloc[0]["Deadline"]).strip()
            status = str(row.iloc[0]["Status"]).strip().upper()
            return dl, (status == "LOCKED")
    return "TBA", False

def get_announcement():
    df = get_static_sheet("Config")
    if not df.empty and "Announcement" in df.iloc[:, 0].values:
        val = str(df[df.iloc[:, 0] == "Announcement"].iloc[0, 1]).strip()
        return val if val.upper() != "NAN" else ""
    return ""

def set_announcement(text):
    df = get_static_sheet("Config")
    if df.empty: df = pd.DataFrame([["Announcement", text]])
    else:
        if "Announcement" in df.iloc[:, 0].values:
            df.loc[df.iloc[:, 0] == "Announcement", df.columns[1]] = text
        else:
            new_row = pd.DataFrame([["Announcement", text] + [""]*(len(df.columns)-2)], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
    conn.update(spreadsheet=SHEET_URL, worksheet="Config", data=df)
    clear_app_memory()

def clean_pct(input_str):
    try: return float(str(input_str).replace('%', '').strip()) if input_str else 0.0
    except: return 0.0

def score_calc(n, d, label):
    val = (n / d * 100) if d > 0 else 0
    st.markdown(f"📈 **Current {label} Performance:** `{val:.2f}%`")
    return val

def get_idx(opts_series, val):
    opts_list = list(opts_series.dropna().unique())
    return opts_list.index(val) if val in opts_list else 0

def get_blank_consumption_grid():
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return pd.DataFrame({"Month": months, "Electricity (kWh)": [0.0]*12, "Fuel (L)": [0.0]*12, "Water (m3)": [0.0]*12, "General Waste (kg)": [0.0]*12, "Haz Waste (kg)": [0.0]*12})

# --- 4. UNIVERSAL PRINT ENGINE (FOR ADMINS ONLY) ---
def generate_universal_print_html(module_title, hosp_name, data_dict):
    exclude_keys = ["Timestamp", "User_ID", "Hospital", "Encoder"]
    rows_html = ""
    for key, val in data_dict.items():
        if key in exclude_keys: continue
        clean_val = "N/A" if pd.isna(val) or str(val).strip() == "" else str(val)
        rows_html += f"<tr><td style='padding: 10px; border: 1px solid #cbd5e1; width: 45%; font-weight: 600; color: #1e293b;'>{key}</td><td style='padding: 10px; border: 1px solid #cbd5e1; color: #334155;'>{clean_val}</td></tr>"
    
    timestamp = data_dict.get("Timestamp", "N/A")
    encoder = data_dict.get("Encoder", "N/A")
        
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #0f172a; background-color: #f8fafc; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 5px solid #1A365D; }}
            .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; }}
            .hosp-title {{ color: #1A365D; margin: 0 0 10px 0; font-size: 24px; text-transform: uppercase; }}
            .module-title {{ color: #475569; margin: 0 0 15px 0; font-size: 18px; }}
            .meta-box {{ background-color: #f1f5f9; padding: 10px; border-radius: 6px; font-size: 14px; color: #64748b; display: flex; justify-content: space-between; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
            th {{ background-color: #1A365D; color: white; padding: 12px; text-align: left; border: 1px solid #1A365D; font-size: 15px; }}
            .footer {{ margin-top: 40px; font-size: 12px; color: #94A3B8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 20px; }}
            @media print {{ .no-print {{ display: none !important; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 class="hosp-title">{hosp_name}</h2>
                <h3 class="module-title">{module_title} - Official Submission Record</h3>
                <div class="meta-box"><span><strong>Encoder:</strong> {encoder}</span><span><strong>Submitted On:</strong> {timestamp}</span></div>
            </div>
            <table><thead><tr><th>Form Field / Question</th><th>Submitted Response</th></tr></thead><tbody>{rows_html}</tbody></table>
            <div class="footer"><p>Generated by Project FORT Automated System • Department of Health - HFDB</p></div>
            <center><button class="no-print" onclick="window.print()" style="margin-top:20px; padding:12px 25px; background:#1A365D; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print to PDF</button></center>
        </div>
    </body>
    </html>
    """

def print_view(hosp, data, module_title):
    st.session_state.isolated_print_html = True
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button("⬅️ Back to Admin Tools", type="primary"): 
            del st.session_state.show_print
            del st.session_state.isolated_print_html
            st.rerun()
            
    html_content = generate_universal_print_html(module_title, hosp, data)
    st.components.v1.html(html_content, height=800, scrolling=True)

# --- 5. AUTHENTICATION & LOGIN ---
def login_screen():
    st.markdown("<h2 style='text-align: center;'>🏥 HFDB Online Data Reporting and Submission Portal</h2>", unsafe_allow_html=True)
    
    if "pending_id" in st.session_state:
        st.warning("⚠️ **IMPORTANT: SAVE YOUR LOGIN CODE**")
        st.markdown(f"""
            <div style="background-color:#F0B216; padding:30px; border-radius:10px; text-align:center; border: 4px solid #000;">
                <h2 style="color:black; margin:0;">YOUR UNIQUE LOGIN ID:</h2>
                <h1 style="color:black; font-family:monospace; background:white; padding:15px; border:2px dashed #000;">{st.session_state.pending_id}</h1>
                <p style="color:black; font-size:18px;"><b>Copy this code now.</b> You will need this to access your data later.</p>
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

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔐 Returning User", "📝 New User"])
        
        with tab1:
            with st.form("login_form"):
                access_code = st.text_input("Enter your Access Code", type="password")
                submitted = st.form_submit_button("Secure Login", use_container_width=True)
                
                if submitted:
                    accounts_df = get_static_sheet("User_Profiles")
                    if not accounts_df.empty and "User_ID" in accounts_df.columns:
                        accounts_df["User_ID"] = accounts_df["User_ID"].astype(str).str.strip()
                        match = accounts_df[accounts_df["User_ID"] == access_code.strip()]
                        
                        if not match.empty:
                            user_data = match.iloc[0]
                            st.session_state.user_id = user_data["User_ID"]
                            access_str = str(user_data.get("Access", "")).strip()
                            st.session_state.user_info = {
                                "user": user_data.get("Encoder_Name", "Unknown"),
                                "role": user_data.get("Role", "user"),
                                "hosp": user_data.get("Hospital_Name", "N/A"),
                                "dept": user_data.get("Department", "General"),
                                "access": [m.strip() for m in access_str.split(",")] if access_str else []
                            }
                            st.rerun()
                        else: st.error("❌ Invalid Access Code.")
                    else: st.error("Database connection error or 'User_ID' column missing.")
                    
        with tab2:
            st.info("First time here? Generate your unique access code below.")
            try:
                hosp_df = get_static_sheet("Facility_List") 
                if not hosp_df.empty and "Facility_Name" in hosp_df.columns:
                    hosp_list = ["-- Select Hospital --"] + hosp_df["Facility_Name"].dropna().unique().tolist()
                elif not hosp_df.empty:
                    hosp_list = ["-- Select Hospital --"] + hosp_df.iloc[:, 0].dropna().unique().tolist()
                else:
                    hosp_list = ["-- Select Hospital --", "List Unavailable - Please Contact Admin"]
            except:
                hosp_list = ["-- Select Hospital --", "Error Loading List"]

            with st.form("register_form"):
                new_hosp = st.selectbox("Hospital Name", hosp_list)
                new_dept = st.text_input("Department / Unit (e.g., HFDB, ER, Pedia)")
                new_encoder = st.text_input("Encoder Name")
                new_designation = st.text_input("Position / Designation")
                
                reg_submit = st.form_submit_button("Generate Login Code", use_container_width=True)
                
                if reg_submit:
                    if new_hosp == "-- Select Hospital --" or not new_dept or not new_encoder or not new_designation:
                        st.error("⚠️ Please fill in all fields and select a valid hospital to register.")
                    else:
                        current_year = datetime.now(timezone(timedelta(hours=8))).strftime("%Y")
                        random_chars = "".join(random.choices(string.ascii_letters + string.digits, k=10))
                        new_code = f"HFDB-{current_year}-{random_chars}"
                        
                        st.session_state.pending_id = new_code
                        st.session_state.pending_info = {
                            "user": new_encoder, "role": "user", "hosp": new_hosp, "dept": new_dept,
                            "designation": new_designation, "access": ["Mod1", "Mod2", "Mod3", "Chat"]
                        }
                        
                        try:
                            accounts_df = get_static_sheet("User_Profiles")
                            new_row = {"User_ID": new_code, "Hospital_Name": new_hosp, "Department": new_dept, "Encoder_Name": new_encoder, "Position": new_designation, "Role": "user", "Access": "Mod1, Mod2, Mod3, Chat"}
                            updated_df = pd.concat([accounts_df, pd.DataFrame([new_row])], ignore_index=True) if not accounts_df.empty else pd.DataFrame([new_row])
                            conn.update(spreadsheet=SHEET_URL, worksheet="User_Profiles", data=updated_df)
                        except Exception as e:
                            st.error(f"Failed to save new user to database. Ensure 'User_Profiles' sheet exists. Error: {e}")
                        st.rerun()

# --- 6. ADMIN VIEWS ---
def admin_analysis_view(mod_id, title):
    if "show_print" in st.session_state:
        df = get_static_sheet(mod_id)
        if not df.empty and "User_ID" in df.columns:
            hosp_data = df[df["User_ID"] == st.session_state.show_print]
            if not hosp_data.empty:
                print_view(hosp_data.iloc[0].get("Hospital", hosp_data.iloc[0].get("H_Type", "Facility Data")), hosp_data.iloc[0].to_dict(), title)
                return
                
    st.markdown(f"<h2>{title}</h2>", unsafe_allow_html=True)
    if st.button("⬅️ Back to Admin Dashboard"): 
        del st.session_state.current_module; st.rerun()
        
    df = get_static_sheet(mod_id)
    if df.empty: st.info("No data submitted yet."); return
        
    st.success(f"✅ Total Submissions: **{len(df)}**")
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown("### Submitted IDs")
        for uid in df["User_ID"].unique():
            with st.expander(f"🏥 ID: {uid}"):
                if st.button("🖨️ View Print Format", key=f"print_{uid}"):
                    st.session_state.show_print = uid
                    st.rerun()
    with c2:
        st.markdown("### Live Database View")
        st.dataframe(df, use_container_width=True)

def admin_chat_view():
    st.markdown("<h2>💬 Admin Support Center</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    with col1:
        if st.button("⬅️ Back to Admin Dashboard"): 
            del st.session_state.current_module
            if "active_chat" in st.session_state: del st.session_state.active_chat
            st.rerun()
    with col2:
        if st.button("🔄 Refresh Inbox", use_container_width=True, type="primary"): st.rerun()
    
    st_autorefresh(interval=15000, limit=None, key="admin_chat_refresh")
    
    try: chat_df = conn.read(spreadsheet=SHEET_URL, worksheet="Support_Logs", ttl="15s")
    except: st.error("Could not load 'Support_Logs' tab from Google Sheets."); return
        
    if chat_df.empty: st.info("No messages from hospitals yet."); return

    inbox_col, chat_col = st.columns([1, 2.5])
    hospitals = chat_df["Hospital"].dropna().unique().tolist()

    with inbox_col:
        st.markdown("### 📥 Inbox")
        inbox_container = st.container(height=500)
        with inbox_container:
            for hosp in hospitals:
                hosp_msgs = chat_df[chat_df["Hospital"] == hosp]
                last_msg = hosp_msgs.iloc[-1]
                raw_msg = str(last_msg["Message"])
                snippet = raw_msg[:20] + "..." if len(raw_msg) > 20 else raw_msg
                indicator = "🔴" if last_msg["Sender"] == "User" else "🟢"
                
                if st.button(f"{indicator} {hosp}", key=f"btn_{hosp}", use_container_width=True):
                    st.session_state.active_chat = hosp
                st.markdown(f"<div style='font-size: 0.85em; color: #94A3B8; margin-top: -10px; margin-bottom: 15px; padding-left: 10px;'>↳ {snippet}</div>", unsafe_allow_html=True)

    with chat_col:
        if st.session_state.get("active_chat"):
            sel_hosp = st.session_state.active_chat
            st.markdown(f"### Chatting with: {sel_hosp}")
            
            hosp_chats = chat_df[chat_df["Hospital"] == sel_hosp]
            chat_container = st.container(height=450)
            
            with chat_container:
                for _, row in hosp_chats.iterrows():
                    is_user = row["Sender"] == "User"
                    with st.chat_message("user" if is_user else "assistant"):
                        raw_name = row.get('Encoder_Name', 'Unknown')
                        clean_name = "Unknown" if pd.isna(raw_name) else raw_name
                        sender_name = f"User - {clean_name}" if is_user else "Admin"
                        st.markdown(f"**{sender_name}** - {row['Timestamp']}\n\n{row['Message']}")
                        
            reply = st.chat_input(f"Reply to {sel_hosp}...")
            if reply:
                u_id = hosp_chats.iloc[0]["User_ID"]
                new_msg = {
                    "Timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"), 
                    "User_ID": u_id, "Hospital": sel_hosp, 
                    "Encoder_Name": "Admin", "Sender": "Admin", "Message": reply
                }
                updated_df = pd.concat([chat_df, pd.DataFrame([new_msg])], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Support_Logs", data=updated_df)
                st.rerun()
        else:
            st.info("👈 Select a hospital from your Inbox to view their chat history and reply.")

def admin_dashboard():
    u = st.session_state.user_info
    allowed_modules = u.get("access", [])
    
    st.markdown(f"<h2 style='text-align: center;'>👑 {u['user']} Portal</h2>", unsafe_allow_html=True)
    
    with st.expander("📢 Manage Global Announcement Banner", expanded=False):
        current_ann = get_announcement()
        new_ann = st.text_area("Announcement Text:", value=current_ann, placeholder="e.g. 🚨 The deadline for Module 1 is approaching!")
        if st.button("💾 Broadcast Announcement", type="primary"):
            set_announcement(new_ann)
            st.success("✅ Announcement broadcasted globally!")
            time.sleep(1); st.rerun()
            
    st.info("Welcome to the Admin View. Select a module below to view live aggregated statistics.")
    
    if "Mod1" in allowed_modules:
        st.markdown('<div class="marker marker-blue"></div>', unsafe_allow_html=True)
        if st.button("📊 Analyze Module 1: Scorecard Data", use_container_width=True): st.session_state.current_module = "Admin_Mod1"; st.rerun()
        
    if "Mod2" in allowed_modules:
        st.markdown('<div class="marker marker-red"></div>', unsafe_allow_html=True)
        if st.button("📈 Analyze Module 2: Census Data", use_container_width=True): st.session_state.current_module = "Admin_Mod2"; st.rerun()
        
    if "Mod3" in allowed_modules:
        st.markdown('<div class="marker marker-green"></div>', unsafe_allow_html=True)
        if st.button("🌿 Analyze Module 3: Green Viability Dashboard", use_container_width=True): st.session_state.current_module = "Admin_Mod3"; st.rerun()
        
    if "Chat" in allowed_modules:
        st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
        if st.button("💬 Open Support Center (Live Chat)", use_container_width=True): st.session_state.current_module = "Admin_Chat"; st.rerun()
        
    st.markdown('<hr>', unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

# --- 7. USER MODULES (DATA ENTRY) ---
def render_mod1():
    deadline_str, locked = get_module_config("Mod1")
    if locked: st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is in READ-ONLY mode.")

    prev = {}
    try:
        mod1_df = get_static_sheet("Mod1")
        if not mod1_df.empty and "User_ID" in mod1_df.columns:
            u_data = mod1_df[mod1_df["User_ID"].astype(str) == str(st.session_state.user_id)]
            if not u_data.empty: prev = u_data.iloc[-1].to_dict()
    except: pass

    try: dd = get_static_sheet("Mod1_DD")
    except: dd = pd.DataFrame()
    
    if dd.empty: 
        st.error("⚠️ Sheet 'Mod1_DD' not found. Please ensure it exists for dropdowns to work.")
        return
    dd.columns = dd.columns.str.strip()

    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button("⬅️ Dashboard", use_container_width=True): 
            del st.session_state.current_module
            if "show_print" in st.session_state: del st.session_state.show_print
            st.rerun()

    st.markdown('<div class="section-header-strat"><h3 style="margin:0; color:white;">📊 STRATEGIC PERFORMANCE INDICATORS</h3></div>', unsafe_allow_html=True)
    
    with st.expander("🔹 Basic Setup: Service Capability", expanded=True):
        lvl_opts = ["Level 1", "Level 2", "Level 3", "Specialty"]
        h_level = st.selectbox("Current Health Facility Service Capability Level:", lvl_opts, index=get_idx(pd.Series(lvl_opts), prev.get("Level")), disabled=locked)
    with st.expander("🔹 SI 1: % Functionality of PHU", expanded=False):
        s1 = clean_pct(st.text_input("Percentage (e.g., 95%)", value=str(prev.get("SI1", "0%")), disabled=locked))
    with st.expander("🔹 SI 2: Green Viability Assessment (GVA)", expanded=False):
        s2 = clean_pct(st.text_input("GVA Score (e.g., 88%)", value=str(prev.get("SI2", "0%")), disabled=locked))
    with st.expander("🔹 SI 3: Capital Formation", expanded=False):
        c1, c2 = st.columns(2)
        cat_opts, src_opts = dd.get("Indicator 3, DD1", pd.Series()), dd.get("Indicator 3, DD2", pd.Series())
        cat = c1.selectbox("Category", cat_opts.dropna().unique(), index=get_idx(cat_opts, prev.get("SI3_Cat")), disabled=locked) if not cat_opts.empty else "N/A"
        src = c2.selectbox("Fund Source", src_opts.dropna().unique(), index=get_idx(src_opts, prev.get("SI3_Src")), disabled=locked) if not src_opts.empty else "N/A"
        stat_opts = dd.get("Indicator 3, DD3.a", pd.Series()) if "Infrastructure" in str(cat) else dd.get("Indicator 3, DD3.b", pd.Series())
        stat = st.selectbox("Status", stat_opts.dropna().unique(), index=get_idx(stat_opts, prev.get("SI3_Stat")), disabled=locked) if not stat_opts.empty else "N/A"
    with st.expander("🔹 SI 4: ISO 9001:2015 Accreditation", expanded=False):
        c1, c2 = st.columns(2)
        iso1 = c1.selectbox("ISO Status", dd.get("Indicator 4, DD1", pd.Series()).dropna().unique(), index=get_idx(dd.get("Indicator 4, DD1", pd.Series()), prev.get("SI4_Status")), disabled=locked)
        iso2 = c2.selectbox("Internal Audit", dd.get("Indicator 4, DD2", pd.Series()).dropna().unique(), index=get_idx(dd.get("Indicator 4, DD2", pd.Series()), prev.get("SI4_Audit")), disabled=locked)
    with st.expander("🔹 SI 5: PGS Accreditation Status", expanded=False):
        c1, c2 = st.columns(2)
        pgs1 = c1.selectbox("2024 PGS Status", dd.get("Indicator 5, DD1", pd.Series()).dropna().unique(), index=get_idx(dd.get("Indicator 5, DD1", pd.Series()), prev.get("SI5_24")), disabled=locked)
        pgs2 = c2.selectbox("2025 PGS Status", dd.get("Indicator 5, DD2", pd.Series()).dropna().unique(), index=get_idx(dd.get("Indicator 5, DD2", pd.Series()), prev.get("SI5_25")), disabled=locked)
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

    st.markdown('<div class="section-header-core"><h3 style="margin:0; color:white;">🎯 CORE QUALITY INDICATORS</h3></div>', unsafe_allow_html=True)
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
    h_name = c1.text_input("Name of Head of Facility:", value=str(prev.get("Head_Name", "")), disabled=locked)
    h_pos = c2.text_input("Designation of Head of Facility:", value=str(prev.get("Head_Pos", "")), disabled=locked)

    res_db = {
        "Timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
        "User_ID": st.session_state.user_id, "Encoder": st.session_state.user_info.get("user", "Unknown"),
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
                try:
                    existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1", ttl=0)
                    if not existing_df.empty and "User_ID" in existing_df.columns: existing_df = existing_df[existing_df["User_ID"].astype(str) != str(st.session_state.user_id)]
                except: existing_df = pd.DataFrame()
                conn.update(spreadsheet=SHEET_URL, worksheet="Mod1", data=pd.concat([existing_df, pd.DataFrame([res_db])], ignore_index=True) if not existing_df.empty else pd.DataFrame([res_db]))
                st.session_state.show_print = True
                st.rerun()
        with btn_col2:
            if st.button("💾 SUBMIT DATA ONLY", use_container_width=True):
                try:
                    existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Mod1", ttl=0)
                    if not existing_df.empty and "User_ID" in existing_df.columns: existing_df = existing_df[existing_df["User_ID"].astype(str) != str(st.session_state.user_id)]
                except: existing_df = pd.DataFrame()
                conn.update(spreadsheet=SHEET_URL, worksheet="Mod1", data=pd.concat([existing_df, pd.DataFrame([res_db])], ignore_index=True) if not existing_df.empty else pd.DataFrame([res_db]))
                st.success("✅ Progress saved!")
    else:
        if st.button("🖨️ PRINT SUBMITTED DATA (READ-ONLY)", type="primary", use_container_width=True):
            st.session_state.show_print = True; st.rerun()

    if st.session_state.get("show_print", False):
        u = st.session_state.user_info
        html = f"""<style>@media print {{ .no-print {{ display: none !important; }} }}</style>
        <div style="font-family: Arial, sans-serif; padding: 40px; background: white; color: black; border: 2px solid #333; max-width: 800px; margin: 0 auto;">
            <center><h1 style="margin:0; color:#111;">2026 DOH HOSPITAL SCORECARD</h1><h3 style="margin:5px 0; color:#444;">{u.get('hosp', 'Unknown')} — {u.get('dept', 'Unknown')} Department</h3><hr style="border:1px solid #111;"></center><br>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin: 0 auto;">
                <tr style="background-color: #1A365D; color: white;"><th colspan="2" style="padding: 10px; border: 1px solid #333; text-align: center;">I. STRATEGIC PERFORMANCE INDICATORS</th></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">Service Capability Level</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('Level', '')}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">SI 1: Functionality of PHU</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('SI1', '')}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">SI 2: Green Viability Assessment</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('SI2', '')}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">SI 3: Capital Formation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{res_print.get('SI3_Cat', '')} ({res_print.get('SI3_Stat', '')})</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">SI 4: ISO Accreditation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{res_print.get('SI4_Status', '')}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">SI 5: PGS Accreditation</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 12px;">{res_print.get('SI5_25', '')}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">SI 6: Specialty Centers</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('SI6', 0):.2f}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">SI 7: Zero Co-Payment</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('SI7', 0):.2f}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">SI 8: Paperless EMR</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('SI8', 0):.2f}%</td></tr>
                <tr style="background-color: #7B341E; color: white;"><th colspan="2" style="padding: 10px; border: 1px solid #333; text-align: center;">II. CORE QUALITY INDICATORS</th></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">CI 1: ER TAT (&lt;4h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('CI1', 0):.2f}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">CI 2: Discharge TAT (&lt;6h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('CI2', 0):.2f}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">CI 3: Lab TAT (&lt;5h)</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('CI3', 0):.2f}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">CI 4: HAI Rate</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('CI4', 0):.2f}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">CI 5: Client Experience Survey</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('CI5', 0):.2f}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #333;">CI 6: Disbursement Rate</td><td style="padding: 8px; border: 1px solid #333; text-align: center; font-size: 13px; font-weight: bold;">{res_print.get('CI6', 0):.2f}%</td></tr>
            </table><br><br>
            <table style="width:100%; text-align:center;"><tr><td>__________________________<br><b>{u.get('user', 'Unknown')}</b><br>{u.get('pos', 'Encoder')}</td><td>__________________________<br><b>{res_print.get('Head_Name', 'Authorized Signatory')}</b><br>{res_print.get('Head_Pos', 'Head of Facility')}</td></tr></table><br>
            <center><button class="no-print" onclick="window.print()" style="padding:12px 25px; background:#1A365D; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print to PDF</button></center>
        </div>"""
        st.components.v1.html(html, height=950, scrolling=True)
        st.info("📂 Please upload your MOVs here: 👉 [HDRT Files Upload](https://bit.ly/HDRTFilesUpload)")

def render_mod2():
    deadline_str, locked = get_module_config("Mod2")
    if locked: st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is in READ-ONLY mode.")

    prev = {}
    try:
        mod2_df = get_static_sheet("Mod2")
        if not mod2_df.empty and "User_ID" in mod2_df.columns:
            u_data = mod2_df[mod2_df["User_ID"].astype(str) == str(st.session_state.user_id)]
            if not u_data.empty: prev = u_data.iloc[-1].to_dict()
    except: pass

    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button("⬅️ Dashboard", use_container_width=True): 
            del st.session_state.current_module
            if "show_print" in st.session_state: del st.session_state.show_print
            st.rerun()

    st.markdown('<div class="section-header-core"><h3 style="margin:0; color:white;">📈 MODULE 2: BASIC INFO, CENSUS & HCPN</h3></div>', unsafe_allow_html=True)
    
    st.header("1️⃣ BASIC INFORMATION")
    with st.expander("Expand to fill out Facility Capability & Bed Capacity", expanded=False):
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
            c_a, c_b, c_c = st.columns([5, 2, 2])
            c_a.markdown(f"**{label}**")
            res_beds[key] = c_b.number_input(label, value=int(float(prev.get(key, 0) or 0)), step=1, disabled=locked, label_visibility="collapsed")
            res_beds[f"RM_{key}"] = c_c.text_input(f"Remarks {key}", value=str(prev.get(f"RM_{key}", "")), disabled=locked, label_visibility="collapsed")

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
            c_a, c_b, c_c = st.columns([5, 2, 2])
            c_a.markdown(f"**{label}**")
            if dtype == "pct": res_census[key] = c_b.text_input(label, value=str(prev.get(key, "0%")), disabled=locked, label_visibility="collapsed")
            elif dtype == "float": res_census[key] = c_b.number_input(label, value=float(prev.get(key, 0.0) or 0.0), step=0.1, disabled=locked, label_visibility="collapsed")
            else: res_census[key] = c_b.number_input(label, value=int(float(prev.get(key, 0) or 0)), step=1, disabled=locked, label_visibility="collapsed")
            res_census[f"RM_{key}"] = c_c.text_input(f"Remarks {key}", value=str(prev.get(f"RM_{key}", "")), disabled=locked, label_visibility="collapsed")

    st.header("3️⃣ HCPN, BUCAS AND COORDINATES")
    with st.expander("Expand to fill out HCPN & BUCAS Data", expanded=False):
        c_a, c_b, c_c = st.columns([5, 2, 2])
        c_a.markdown("**Apex or End-Referral Hospital?**")
        apex = c_b.selectbox("Apex", ["Yes", "No"], index=get_idx(pd.Series(["Yes", "No"]), prev.get("APEX")), disabled=locked, label_visibility="collapsed")
        rm_apex = c_c.text_input("Remarks Apex", value=str(prev.get("RM_APEX", "")), disabled=locked, label_visibility="collapsed")

        c_a, c_b, c_c = st.columns([5, 2, 2])
        c_a.markdown("**How many HCPNs are they linked with?**")
        hcpn_count = c_b.number_input("HCPN Count", value=int(float(prev.get("HCPN_COUNT", 0) or 0)), step=1, disabled=locked, label_visibility="collapsed")
        rm_hcpn = c_c.text_input("Remarks HCPN", value=str(prev.get("RM_HCPN", "")), disabled=locked, label_visibility="collapsed")

        c_a, c_b, c_c = st.columns([5, 2, 2])
        c_a.markdown("**Operates a BUCAS Center/s?**")
        bucas = c_b.selectbox("BUCAS", ["Yes", "No"], index=get_idx(pd.Series(["Yes", "No"]), prev.get("BUCAS")), disabled=locked, label_visibility="collapsed")
        rm_bucas = c_c.text_input("Remarks BUCAS", value=str(prev.get("RM_BUCAS", "")), disabled=locked, label_visibility="collapsed")

        c_a, c_b, c_c = st.columns([5, 2, 2])
        c_a.markdown("**Coordinates of the BUCAS Center (Lat, Long)**")
        coords = c_b.text_input("Coords", value=str(prev.get("COORDS", "")), disabled=locked, label_visibility="collapsed")
        rm_coords = c_c.text_input("Remarks Coords", value=str(prev.get("RM_COORDS", "")), disabled=locked, label_visibility="collapsed")

    st.divider()
    h_col1, h_col2 = st.columns(2)
    h_name = h_col1.text_input("Name of Head of Facility:", value=str(prev.get("Head_Name", "")), disabled=locked)
    h_pos = h_col2.text_input("Designation of Head of Facility:", value=str(prev.get("Head_Pos", "")), disabled=locked)

    final_data = {
        "Timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
        "User_ID": st.session_state.user_id, "Encoder": st.session_state.user_info.get("user", "Unknown"),
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
            try:
                existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Mod2", ttl=0)
                if not existing_df.empty and "User_ID" in existing_df.columns: existing_df = existing_df[existing_df["User_ID"].astype(str) != str(st.session_state.user_id)]
            except: existing_df = pd.DataFrame()
            conn.update(spreadsheet=SHEET_URL, worksheet="Mod2", data=pd.concat([existing_df, pd.DataFrame([final_data])], ignore_index=True) if not existing_df.empty else pd.DataFrame([final_data]))
            st.session_state.show_print = True
            st.rerun()
        if btn2.button("💾 SAVE PROGRESS ONLY", use_container_width=True):
            try:
                existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Mod2", ttl=0)
                if not existing_df.empty and "User_ID" in existing_df.columns: existing_df = existing_df[existing_df["User_ID"].astype(str) != str(st.session_state.user_id)]
            except: existing_df = pd.DataFrame()
            conn.update(spreadsheet=SHEET_URL, worksheet="Mod2", data=pd.concat([existing_df, pd.DataFrame([final_data])], ignore_index=True) if not existing_df.empty else pd.DataFrame([final_data]))
            st.success("✅ Progress saved!")
    else:
        if st.button("🖨️ PRINT SUBMITTED DATA (READ-ONLY)", type="primary", use_container_width=True):
            st.session_state.show_print = True; st.rerun()

    if st.session_state.get("show_print", False):
        u = st.session_state.user_info
        html = f"""<style>@media print {{ .no-print {{ display: none !important; }} }}</style>
        <div style="font-family: Arial, sans-serif; padding: 40px; background: white; color: black; border: 2px solid #333; max-width: 850px; margin: 0 auto;">
            <center><h2 style="margin:0;">HEALTH FACILITY CENSUS & HCPN DATA (2025-2026)</h2><h4 style="margin:5px 0;">{u.get('hosp', 'Unknown')} — {u.get('dept', 'Unknown')} Department</h4><hr style="border:1px solid #111;"></center>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 11px;">
                <tr style="background: #eee;"><th style="border: 1px solid #333; padding: 6px; text-align: left; width: 45%;">Data Parameter</th><th style="border: 1px solid #333; padding: 6px; text-align: center; width: 15%;">Value</th><th style="border: 1px solid #333; padding: 6px; text-align: left; width: 40%;">Remarks</th></tr>
                <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">I. BASIC INFORMATION</td></tr>
                <tr><td style="border: 1px solid #333; padding: 4px;">Service Capability (2026)</td><td style="border: 1px solid #333; padding: 4px; text-align: center;">{final_data.get('LV_26', '')}</td><td style="border: 1px solid #333; padding: 4px;">{final_data.get('RM_LV26', '')}</td></tr>
                <tr><td style="border: 1px solid #333; padding: 4px;">ABC by Licensing (2025)</td><td style="border: 1px solid #333; padding: 4px; text-align: center;">{final_data.get('ABC_25', '')}</td><td style="border: 1px solid #333; padding: 4px;">{final_data.get('RM_ABC_25', '')}</td></tr>
                <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">II. HOSPITAL CENSUS (2025)</td></tr>
                <tr><td style="border: 1px solid #333; padding: 4px;">Bed Occupancy Rate (BOR)</td><td style="border: 1px solid #333; padding: 4px; text-align: center;">{final_data.get('BOR_25', '')}</td><td style="border: 1px solid #333; padding: 4px;">{final_data.get('RM_BOR_25', '')}</td></tr>
                <tr><td colspan="3" style="background:#f9f9f9; font-weight:bold; padding:5px; border: 1px solid #333;">III. HCPN & BUCAS</td></tr>
                <tr><td style="border: 1px solid #333; padding: 4px;">Apex/End-Referral Status</td><td style="border: 1px solid #333; padding: 4px; text-align: center;">{final_data.get('APEX', '')}</td><td style="border: 1px solid #333; padding: 4px;">{final_data.get('RM_APEX', '')}</td></tr>
            </table><br><br><br>
            <table style="width:100%; text-align:center; font-size:14px;"><tr><td style="width:50%;">__________________________<br><b>{u.get('user', 'Unknown')}</b><br>{u.get('pos', 'Encoder')}</td><td style="width:50%;">__________________________<br><b>{final_data.get('Head_Name', '')}</b><br>{final_data.get('Head_Pos', '')}</td></tr></table>
            <center><br><button class="no-print" onclick="window.print()" style="padding:10px 20px; background:#222; color:white; border:none; border-radius:5px; cursor:pointer;">Confirm & Print to PDF</button></center>
        </div>"""
        st.components.v1.html(html, height=1000, scrolling=True)
        st.info("📂 Please upload your MOVs here: 👉 [HDRT Files Upload](https://bit.ly/HDRTFilesUpload)")

def render_mod3():
    if st.session_state.get("isolated_print_html"):
        c1, c2, c3 = st.columns([1, 4, 1])
        with c1:
            if st.button("⬅️ Back to Assessment Form", type="primary"):
                del st.session_state.isolated_print_html; st.rerun()
        st.components.v1.html(st.session_state.isolated_print_html, height=1000, scrolling=True)
        return

    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button("⬅️ Dashboard", use_container_width=True): 
            del st.session_state.current_module; st.rerun()

    deadline_str, locked = get_module_config("Mod3")
    if locked: st.error(f"⚠️ The deadline ({deadline_str}) has passed. This module is READ-ONLY.")

    st.markdown('<div class="section-header-green"><h2 style="margin:0; color:white;">🌿 MODULE 3: GREEN VIABILITY ASSESSMENT</h2></div>', unsafe_allow_html=True)
    
    u = st.session_state.user_info
    mod3_df = get_static_sheet("Mod3")
    prev = {}
    if not mod3_df.empty and "User_ID" in mod3_df.columns:
        u_data = mod3_df[mod3_df["User_ID"].astype(str) == str(st.session_state.user_id)]
        if not u_data.empty: prev = u_data.iloc[-1].to_dict()

    mod2_df = get_static_sheet("Mod2")
    mod2_data = {}
    if not mod2_df.empty and "User_ID" in mod2_df.columns:
        u2_data = mod2_df[mod2_df["User_ID"].astype(str) == str(st.session_state.user_id)]
        if not u2_data.empty: mod2_data = u2_data.iloc[-1].to_dict()

    auto_abc = mod2_data.get("ABC_26", prev.get("LTO_ABC", ""))
    auto_coords = mod2_data.get("COORDS", prev.get("Coordinates", ""))
    parts = [p.strip() for p in str(auto_coords).split(",") if p.strip()]
    auto_lat = parts[0] if len(parts) > 0 else str(prev.get("Lat", ""))
    auto_long = parts[1] if len(parts) > 1 else str(prev.get("Long", ""))
    
    abc_locked = True if str(auto_abc).strip() not in ["", "0", "0.0", "nan"] else False
    lat_locked = True if str(auto_lat).strip() not in ["", "0", "0.0", "nan"] else False
    long_locked = True if str(auto_long).strip() not in ["", "0", "0.0", "nan"] else False

    def subtle_header(title, icon): st.markdown(f"<h4 style='color:#10B981; margin-top:15px; margin-bottom:5px;'>{icon} {title}</h4>", unsafe_allow_html=True)
    
    st.markdown("### 1️⃣ GENERAL INFORMATION")
    with st.expander("Expand to fill General & Geographical Info", expanded=True):
        subtle_header("Facility Overview", "🏥")
        c1, c2, c3 = st.columns(3)
        h_name = c1.text_input("Name of Health Facility:", value=u['hosp'], disabled=True)
        h_type = c2.selectbox("Type of Health Facility:", ["Hospital", "Infirmary", "Clinic", "Others"], index=get_idx(pd.Series(["Hospital", "Infirmary", "Clinic", "Others"]), prev.get("H_Type")), disabled=locked)
        h_level = c3.text_input("Service Capability Level:", value=u.get('level', 'Level 1'), disabled=True)
        
        c4, c5, c6 = st.columns(3)
        h_region = c4.text_input("Region:", value=str(prev.get("H_Region", "")), disabled=locked)
        h_prov = c5.text_input("Province:", value=str(prev.get("H_Prov", "")), disabled=locked)
        h_muni = c6.text_input("Municipality:", value=str(prev.get("H_Muni", "")), disabled=locked)
        
        o1, o2 = st.columns(2)
        h_own = o1.selectbox("Ownership:", ["Government", "Private"], index=get_idx(pd.Series(["Government", "Private"]), prev.get("H_Own")), disabled=locked)
        h_subown = o2.text_input("Sub-ownership:", value=str(prev.get("H_Subown", "")), disabled=locked)
        
        subtle_header("Bed Capacities", "🛏️")
        b1, b2, b3, b4 = st.columns(4)
        lto_abc = b1.text_input("LTO ABC (Beds):", value=auto_abc, disabled=(locked or abc_locked))
        ibc = b2.number_input("Implementing Bed Cap:", value=int(float(prev.get("IBC", 0) or 0)), step=1, disabled=locked)
        icu = b3.number_input("ICU Beds:", value=int(float(prev.get("ICU_Beds", 0) or 0)), step=1, disabled=locked)
        bor = b4.text_input("Bed Occupancy Rate (%):", value=str(prev.get("BOR_Pct", "")), disabled=locked)
        
        subtle_header("Green Initiative Officers", "🌿")
        g1, g2, g3 = st.columns(3)
        eeco_name = g1.text_input("EECO Name:", value=str(prev.get("EECO_Name", "")), disabled=locked)
        eeco_email = g2.text_input("EECO Email:", value=str(prev.get("EECO_Email", "")), disabled=locked)
        eeco_num = g3.text_input("EECO Contact:", value=str(prev.get("EECO_Num", "")), disabled=locked)
        
        g4, g5, g6 = st.columns(3)
        pco_name = g4.text_input("PCO Name:", value=str(prev.get("PCO_Name", "")), disabled=locked)
        pco_email = g5.text_input("PCO Email:", value=str(prev.get("PCO_Email", "")), disabled=locked)
        pco_num = g6.text_input("PCO Contact:", value=str(prev.get("PCO_Num", "")), disabled=locked)
        
        subtle_header("Personnel Profiling", "👥")
        p1, p2, p3 = st.columns(3)
        clin_staff = p1.number_input("Clinical Staff Count:", value=int(float(prev.get("Clin_Staff", 0) or 0)), step=1, disabled=locked)
        non_clin = p2.number_input("Non-Clinical Staff Count:", value=int(float(prev.get("Non_Clin_Staff", 0) or 0)), step=1, disabled=locked)
        admin_staff = p3.number_input("Administrative Personnel:", value=int(float(prev.get("Admin_Staff", 0) or 0)), step=1, disabled=locked)
        
        p4, p5, p6 = st.columns(3)
        jan_sec = p4.number_input("Janitorial Personnel:", value=int(float(prev.get("Jan_Staff", 0) or 0)), step=1, disabled=locked)
        sec_staff = p5.number_input("Security Personnel:", value=int(float(prev.get("Sec_Staff", 0) or 0)), step=1, disabled=locked)
        coterm_staff = p6.number_input("Coterminous Personnel:", value=int(float(prev.get("Coterm_Staff", 0) or 0)), step=1, disabled=locked)

        subtle_header("Physical Distribution", "🏢")
        tgfa = st.number_input("Total Gross Floor Area (TGFA) (sq.m):", value=float(prev.get("TGFA", 0.0) or 0.0), disabled=locked)
        if "bldg_df" not in st.session_state: st.session_state.bldg_df = pd.DataFrame([{"Building Name": "Main Hospital", "Floor Area (sq.m)": 0.0}])
        bldg_res = st.data_editor(st.session_state.bldg_df, num_rows="dynamic", use_container_width=True, disabled=locked, key="bldg_grid")

        subtle_header("Structural & Safety Testing", "🏗️")
        t1, t2 = st.columns(2)
        hammer_test = t1.selectbox("Conducted hammer test/structural analysis?", ["No", "Yes"], index=get_idx(pd.Series(["No", "Yes"]), prev.get("Hammer_Test")), disabled=locked)
        hammer_details = t2.text_input("If yes, when and what date?", value=str(prev.get("Hammer_Details", "")), disabled=locked)
        
        t3, t4 = st.columns(2)
        hsi_test = t3.selectbox("Conducted Hospital Safety Index?", ["No", "Yes"], index=get_idx(pd.Series(["No", "Yes"]), prev.get("HSI_Test")), disabled=locked)
        hsi_details = t4.text_input("If yes, when and what buildings?", value=str(prev.get("HSI_Details", "")), disabled=locked)

        subtle_header("GEOGRAPHICAL DESCRIPTION", "🗺️")
        c_geo1, c_geo2 = st.columns(2)
        final_lat = c_geo1.text_input("Latitude:", value=auto_lat, disabled=(locked or lat_locked))
        final_long = c_geo2.text_input("Longitude:", value=auto_long, disabled=(locked or long_locked))
        
        c_geo3, c_geo4 = st.columns(2)
        lot_area = c_geo3.number_input("Total Lot Area (sq.m):", value=float(prev.get("Lot_Area", 0.0) or 0.0), disabled=locked)
        green_space = c_geo4.number_input("Green Space Area (sq.m):", value=float(prev.get("Green_Space", 0.0) or 0.0), disabled=locked)
        
        c_geo5, c_geo6 = st.columns(2)
        soil_test = c_geo5.selectbox("Conducted soil testing in the hospital premise/s?", ["No", "Yes"], index=get_idx(pd.Series(["No", "Yes"]), prev.get("Soil_Test")), disabled=locked)
        soil_date = c_geo6.text_input("If yes, when:", value=str(prev.get("Soil_Date", "")), disabled=locked)

        subtle_header("Characteristic of Location", "📍")
        col1, col2, col3, col4 = st.columns([3, 2, 3, 2])
        c_coast = col1.checkbox("a. Coastal Area", value=bool(prev.get("C_Coast", False)), disabled=locked)
        d_coast = col2.text_input("Dist a", value=str(prev.get("D_Coast", "")), disabled=(not c_coast or locked), label_visibility="collapsed")
        c_mount = col3.checkbox("d. Mountainous Terrain", value=bool(prev.get("C_Mount", False)), disabled=locked)
        d_mount = col4.text_input("Dist d", value=str(prev.get("D_Mount", "")), disabled=(not c_mount or locked), label_visibility="collapsed")
        
        c_low = col1.checkbox("b. Low Lying Area", value=bool(prev.get("C_Low", False)), disabled=locked)
        d_low = col2.text_input("Dist b", value=str(prev.get("D_Low", "")), disabled=(not c_low or locked), label_visibility="collapsed")
        c_deep = col3.checkbox("e. Others: Deep well source", value=bool(prev.get("C_Deep", False)), disabled=locked)
        d_deep = col4.text_input("Dist e", value=str(prev.get("D_Deep", "")), disabled=(not c_deep or locked), label_visibility="collapsed")
        
        c_land = col1.checkbox("c. Landslide Prone", value=bool(prev.get("C_Land", False)), disabled=locked)
        d_land = col2.text_input("Dist c", value=str(prev.get("D_Land", "")), disabled=(not c_land or locked), label_visibility="collapsed")
        c_flood = col3.checkbox("f. Others: Low Flood Suscep.", value=bool(prev.get("C_Flood", False)), disabled=locked)
        d_flood = col4.text_input("Dist f", value=str(prev.get("D_Flood", "")), disabled=(not c_flood or locked), label_visibility="collapsed")

        subtle_header("Location / Distance in Kilometer/meter", "📏")
        dist1, dist2, dist3, dist4 = st.columns(4)
        dist_fault = dist1.number_input("from the fault line (km):", value=float(prev.get("Dist_Fault", 0.0) or 0.0), disabled=locked)
        dist_volc = dist2.number_input("from volcano (km):", value=float(prev.get("Dist_Volc", 0.0) or 0.0), disabled=locked)
        dist_sea = dist3.number_input("from the sea (km):", value=float(prev.get("Dist_Sea", 0.0) or 0.0), disabled=locked)
        dist_hw = dist4.number_input("from major highway (km):", value=float(prev.get("Dist_HW", 0.0) or 0.0), disabled=locked)
        
        dist5, dist6, dist7, dist8 = st.columns(4)
        dist_rail = dist5.number_input("from the railroad (km):", value=float(prev.get("Dist_Rail", 0.0) or 0.0), disabled=locked)
        dist_haz = dist6.number_input("from hazardous elements (km):", value=float(prev.get("Dist_Haz", 0.0) or 0.0), disabled=locked)
        dist_oil = dist7.number_input("from oil deposit (km):", value=float(prev.get("Dist_Oil", 0.0) or 0.0), disabled=locked)
        dist_ind = dist8.number_input("from industrial est (km):", value=float(prev.get("Dist_Ind", 0.0) or 0.0), disabled=locked)
        
        dist9, dist10, dist11, dist12 = st.columns(4)
        dist_river = dist9.number_input("from the river bank (m):", value=float(prev.get("Dist_River", 0.0) or 0.0), disabled=locked)
        dist_creek = dist10.number_input("from the creeks (m):", value=float(prev.get("Dist_Creek", 0.0) or 0.0), disabled=locked)
        dist_lake = dist11.number_input("from the lake (m):", value=float(prev.get("Dist_Lake", 0.0) or 0.0), disabled=locked)
        
        dist_o1, dist_o2 = st.columns([1, 1])
        dist_other_desc = dist_o1.text_input("other/s:", value=str(prev.get("Dist_Other_Desc", "")), disabled=locked)
        dist_other_val = dist_o2.number_input("other/s distance:", value=float(prev.get("Dist_Other_Val", 0.0) or 0.0), disabled=locked)

        s1, s2 = st.columns(2)
        sign_name = s1.text_input("Signatory Name:", value=str(prev.get("Sign_Name", "")), disabled=locked)
        sign_pos = s2.text_input("Signatory Position:", value=str(prev.get("Sign_Pos", "Head of Facility")), disabled=locked)

        st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
        if st.button("🖨️ Print General Information for Signature", use_container_width=True):
            def fmt_char(checked, dist): return f"Yes ({dist})" if checked and dist else "Yes" if checked else "No"
            html = f"""<style>@media print {{ .no-print {{ display: none !important; }} }}</style>
            <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="text-align:center;">GENERAL INFORMATION</h2>
            <table style="width:100%; border-collapse: collapse; font-size: 14px;">
                <tr><td colspan="2" style="border: 1px solid #333; padding: 8px; background:#e0e0e0;"><b>Facility Overview</b></td></tr>
                <tr><td colspan="2" style="border: 1px solid #333; padding: 8px;"><b>Facility Name:</b> {u['hosp']}</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Type:</b> {h_type}</td><td style="border: 1px solid #333; padding: 8px;"><b>Ownership:</b> {h_own} ({h_subown})</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Region:</b> {h_region}</td><td style="border: 1px solid #333; padding: 8px;"><b>Province/Muni:</b> {h_prov}, {h_muni}</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>LTO ABC:</b> {lto_abc}</td><td style="border: 1px solid #333; padding: 8px;"><b>IBC:</b> {ibc}</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>ICU Beds:</b> {icu}</td><td style="border: 1px solid #333; padding: 8px;"><b>BOR (%):</b> {bor}</td></tr>
                <tr><td colspan="2" style="border: 1px solid #333; padding: 8px; background:#e0e0e0;"><b>Personnel & Officers</b></td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>EECO:</b> {eeco_name} <br>({eeco_num} | {eeco_email})</td><td style="border: 1px solid #333; padding: 8px;"><b>PCO:</b> {pco_name} <br>({pco_num} | {pco_email})</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Clinical / Non-Clinical:</b> {clin_staff} / {non_clin}</td><td style="border: 1px solid #333; padding: 8px;"><b>Admin / Janitorial:</b> {admin_staff} / {jan_sec}</td></tr>
                <tr><td colspan="2" style="border: 1px solid #333; padding: 8px; background:#e0e0e0;"><b>Geographical & Testing</b></td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>TGFA:</b> {tgfa} sq.m</td><td style="border: 1px solid #333; padding: 8px;"><b>Lot Area:</b> {lot_area} sq.m</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Green Space:</b> {green_space} sq.m</td><td style="border: 1px solid #333; padding: 8px;"><b>Coords (Lat, Long):</b> {final_lat}, {final_long}</td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Hammer Test:</b> {hammer_test} <br><i>{hammer_details}</i></td><td style="border: 1px solid #333; padding: 8px;"><b>HSI Test:</b> {hsi_test} <br><i>{hsi_details}</i></td></tr>
                <tr><td style="border: 1px solid #333; padding: 8px;"><b>Soil Test:</b> {soil_test} ({soil_date})</td><td style="border: 1px solid #333; padding: 8px;"></td></tr>
            </table><br><br><table style='width:100%; text-align:center;'><tr><td>__________________________<br><b>{sign_name}</b><br>{sign_pos}</td></tr></table>
            <center><br><button class="no-print" onclick="window.print()" style="padding:12px 25px; background:#064E3B; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print to PDF</button></center></div>"""
            st.session_state.isolated_print_html = html
            st.rerun()
            
    st.markdown("### 2️⃣ MULTI-YEAR CONSUMPTION DATA")
    years = [str(y) for y in range(2022, 2029)]
    tabs = st.tabs(years)
    live_consumption = {}
    
    for i, year in enumerate(years):
        with tabs[i]:
            if f"grid_{year}" not in st.session_state: st.session_state[f"grid_{year}"] = get_blank_consumption_grid()
            grid_result = st.data_editor(st.session_state[f"grid_{year}"], hide_index=True, use_container_width=True, disabled=locked, key=f"editor_{year}")
            live_consumption[year] = grid_result
            
            t_df = grid_result.copy()
            st.markdown(f"""
            <div style="background:#161B22; padding:12px; border-radius:6px; display:flex; justify-content:space-between; font-size:0.95em; border: 1px solid #30363D; margin-bottom: 15px;">
                <div><b>⚡ Elec:</b> {pd.to_numeric(t_df["Electricity (kWh)"], errors='coerce').sum():,.2f} kWh</div>
                <div><b>⛽ Fuel:</b> {pd.to_numeric(t_df["Fuel (L)"], errors='coerce').sum():,.2f} L</div>
                <div><b>💧 Water:</b> {pd.to_numeric(t_df["Water (m3)"], errors='coerce').sum():,.2f} m³</div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
            if st.button(f"🖨️ Print {year} Consumption for Signature", use_container_width=True, key=f"p_cons_{year}"):
                html = grid_result.to_html(index=False, border=1, classes="my-table", justify="center")
                html = html.replace('class="dataframe my-table"', 'style="width: 100%; border-collapse: collapse; text-align: center;"')
                html = html.replace('<th>', '<th style="background-color: #eee; padding: 8px; border: 1px solid #333;">')
                html = html.replace('<td>', '<td style="padding: 6px; border: 1px solid #333;">')
                html = f"""<style>@media print {{ .no-print {{ display: none !important; }} }}</style>
                <div style='font-family: Arial, sans-serif; padding: 20px;'><h2 style='text-align:center;'>{year} CONSUMPTION DATA</h2>{html}<br><br><table style='width:100%; text-align:center;'><tr><td>__________________________<br><b>{sign_name}</b><br>{sign_pos}</td></tr></table>
                <center><br><button class="no-print" onclick="window.print()" style="padding:12px 25px; background:#064E3B; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print to PDF</button></center></div>"""
                st.session_state.isolated_print_html = html
                st.rerun()

    factors = {"Electricity (kWh)": 0.79, "Fuel (L)": 3.28, "Water (m3)": 0.28}
    admin_co2e_save = {}
    for year in years:
        df = live_consumption[year]
        total_co2 = (pd.to_numeric(df["Electricity (kWh)"], errors='coerce').fillna(0).sum() * factors["Electricity (kWh)"]) + \
                    (pd.to_numeric(df["Fuel (L)"], errors='coerce').fillna(0).sum() * factors["Fuel (L)"]) + \
                    (pd.to_numeric(df["Water (m3)"], errors='coerce').fillna(0).sum() * factors["Water (m3)"])
        admin_co2e_save[f"CO2e_{year}"] = total_co2

    st.markdown("### 3️⃣ PERFORMANCE STANDARDS")
    weights_dict = {"GOVERNANCE": 0.10, "ENERGY EFFICIENCY": 0.17, "WATER EFFICIENCY, SANITATION AND HYGIENE": 0.13, "HEALTH CARE WASTE MANAGEMENT": 0.13, "ENVIRONMENTALLY RESILIENT HEALTH FACILITY": 0.12, "MATERIAL SUSTAINABILITY": 0.11, "SITE SUSTAINABILITY": 0.11, "INDOOR ENVIRONMENTAL QUALITY": 0.13}
    gva_answers = {}
    score_summary = []
    total_gva_weighted_score = 0.0  
    
    perf_df = get_static_sheet("Performance Standards")
    if not perf_df.empty:
        perf_df.columns = perf_df.columns.str.strip()
        if 'MAJOR CATEGORY' in perf_df.columns and 'CRITERION' in perf_df.columns and 'Ref. #' in perf_df.columns and 'QUESTIONS' in perf_df.columns:
            perf_df['MAJOR CATEGORY'] = perf_df['MAJOR CATEGORY'].ffill()
            perf_df['CRITERION'] = perf_df['CRITERION'].ffill()
            sub_col = 'SUB- CATEGORY' if 'SUB- CATEGORY' in perf_df.columns else 'SUB-CATEGORY' if 'SUB-CATEGORY' in perf_df.columns else None
            if sub_col: perf_df[sub_col] = perf_df[sub_col].ffill()
            
            questions_only = perf_df.dropna(subset=['Ref. #', 'QUESTIONS'])
            categories = questions_only['MAJOR CATEGORY'].unique()
            
            for cat in categories:
                cat_max = 0
                cat_actual = 0
                cat_questions = questions_only[questions_only['MAJOR CATEGORY'] == cat]
                criterion_desc = cat_questions['CRITERION'].iloc[0] 
                
                with st.expander(f"📌 {cat}", expanded=False):
                    if sub_col:
                        subs = cat_questions[sub_col].unique()
                        for sub in subs:
                            sub_qs = cat_questions[cat_questions[sub_col] == sub]
                            for _, row in sub_qs.iterrows():
                                q_ref, q_text = str(row['Ref. #']).strip(), str(row['QUESTIONS']).strip()
                                st.markdown(f"**{q_ref}:** {q_text}")
                                ans = st.radio("Status", ["Yes (1 pt)", "In Progress (0.5 pt)", "No (0 pt)"], index=get_idx(pd.Series(["Yes (1 pt)", "In Progress (0.5 pt)", "No (0 pt)"]), prev.get(f"GVA_{q_ref}", "No (0 pt)")), horizontal=True, key=f"rad_{q_ref}", disabled=locked, label_visibility="collapsed")
                                gva_answers[f"GVA_{q_ref}"] = ans
                                cat_max += 1.0
                                if "Yes" in ans: cat_actual += 1.0
                                elif "In Progress" in ans: cat_actual += 0.5
                                st.divider()
                    
                    st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
                    if st.button(f"🖨️ Print {cat} for Signature", use_container_width=True, key=f"p_cat_{cat}"):
                        html_lines = [f"<style>@media print {{ .no-print {{ display: none !important; }} }}</style><div style='font-family: Arial, sans-serif; padding: 20px;'><h2 style='text-align:center;'>{cat}</h2><table style='width:100%; border-collapse: collapse;'><tr><th style='border:1px solid #333; padding:8px; background:#eee;'>Ref</th><th style='border:1px solid #333; padding:8px; background:#eee;'>Question</th><th style='border:1px solid #333; padding:8px; background:#eee;'>Answer</th></tr>"]
                        for _, row in cat_questions.iterrows():
                            ref = str(row['Ref. #']).strip()
                            html_lines.append(f"<tr><td style='border:1px solid #333; padding:8px;'>{ref}</td><td style='border:1px solid #333; padding:8px;'>{row['QUESTIONS']}</td><td style='border:1px solid #333; padding:8px; text-align:center;'><b>{gva_answers[f'GVA_{ref}']}</b></td></tr>")
                        html_lines.append(f"</table><br><br><table style='width:100%; text-align:center;'><tr><td>__________________________<br><b>{sign_name}</b><br>{sign_pos}</td></tr></table><center><br><button class='no-print' onclick='window.print()' style='padding:12px 25px; background:#064E3B; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;'>Confirm & Print to PDF</button></center></div>")
                        st.session_state.isolated_print_html = "".join(html_lines)
                        st.rerun()
                
                pct = (cat_actual / cat_max * 100) if cat_max > 0 else 0
                cat_weight = weights_dict.get(str(cat).strip().upper(), 0.0) 
                weighted_score = (pct / 100.0) * cat_weight * 100.0 
                total_gva_weighted_score += weighted_score
                score_summary.append({"Performance Indicator": cat, "Max Score": cat_max, "Actual Score": cat_actual, "Percentage": f"{pct:.2f}%", "Weight": f"{cat_weight*100:.0f}%", "Weighted Score": f"{weighted_score:.2f}%"})
            
            st.markdown("### 🏆 Overall Score Summary")
            score_df = pd.DataFrame(score_summary)
            st.dataframe(score_df, use_container_width=True, hide_index=True)
            
            st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
            if st.button("🖨️ Print OVERALL SCORE TABLE for Signature", use_container_width=True):
                html = score_df.to_html(index=False, border=1, justify="center")
                html = html.replace('class="dataframe"', 'style="width: 100%; border-collapse: collapse; text-align: center; font-size: 14px;"')
                html = html.replace('<th>', '<th style="background-color: #064E3B; color: white; padding: 10px; border: 1px solid #333;">')
                html = html.replace('<td>', '<td style="padding: 8px; border: 1px solid #333;">')
                html = f"""<style>@media print {{ .no-print {{ display: none !important; }} }}</style>
                <div style='font-family: Arial, sans-serif; padding: 20px;'><h2 style='text-align:center;'>OVERALL PERFORMANCE SCORE SUMMARY</h2>{html}<h2 style='text-align:center; color:#064E3B; margin-top:30px;'>FINAL GVA SCORE: {total_gva_weighted_score:.2f}%</h2><br><br><table style='width:100%; text-align:center;'><tr><td>__________________________<br><b>{sign_name}</b><br>{sign_pos}</td></tr></table>
                <center><br><button class="no-print" onclick="window.print()" style="padding:12px 25px; background:#064E3B; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Confirm & Print to PDF</button></center></div>"""
                st.session_state.isolated_print_html = html
                st.rerun()

    st.markdown("### 4️⃣ MASTER EVIDENCE UPLOAD")
    master_link = st.text_input("Paste Google Drive Folder Link Here:", value=str(prev.get("Master_Drive_Link", "")), disabled=locked)

    final_mod3_data = {
        "Timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
        "User_ID": st.session_state.user_id, "Encoder": st.session_state.user_info.get("user", "Unknown"),
        "H_Type": h_type, "H_Region": h_region, "H_Prov": h_prov, "H_Muni": h_muni,
        "H_Own": h_own, "H_Subown": h_subown, "LTO_ABC": lto_abc, "IBC": ibc, "ICU_Beds": icu, "BOR_Pct": bor,
        "EECO_Name": eeco_name, "EECO_Email": eeco_email, "EECO_Num": eeco_num, "PCO_Name": pco_name, "PCO_Email": pco_email, "PCO_Num": pco_num,
        "Clin_Staff": clin_staff, "Non_Clin_Staff": non_clin, "Admin_Staff": admin_staff, "Jan_Staff": jan_sec, "Sec_Staff": sec_staff, "Coterm_Staff": coterm_staff,
        "TGFA": tgfa, "Lot_Area": lot_area, "Green_Space": green_space, "Lat": final_lat, "Long": final_long,
        "Hammer_Test": hammer_test, "Hammer_Details": hammer_details, "Soil_Test": soil_test, "Soil_Date": soil_date, "HSI_Test": hsi_test, "HSI_Details": hsi_details,
        "C_Coast": c_coast, "D_Coast": d_coast, "C_Low": c_low, "D_Low": d_low, "C_Land": c_land, "D_Land": d_land, "C_Mount": c_mount, "D_Mount": d_mount,
        "C_Deep": c_deep, "D_Deep": d_deep, "C_Flood": c_flood, "D_Flood": d_flood,
        "Dist_Fault": dist_fault, "Dist_Volc": dist_volc, "Dist_Sea": dist_sea, "Dist_HW": dist_hw, "Dist_Rail": dist_rail, "Dist_Haz": dist_haz, "Dist_Oil": dist_oil, "Dist_Ind": dist_ind,
        "Dist_River": dist_river, "Dist_Creek": dist_creek, "Dist_Lake": dist_lake, "Dist_Other_Desc": dist_other_desc, "Dist_Other_Val": dist_other_val,
        "Sign_Name": sign_name, "Sign_Pos": sign_pos, "Master_Drive_Link": master_link, "FINAL_GVA_SCORE": total_gva_weighted_score
    }
    final_mod3_data.update(gva_answers); final_mod3_data.update(admin_co2e_save)

    if not locked:
        st.markdown('<div class="marker marker-green"></div>', unsafe_allow_html=True)
        if st.button("💾 SAVE ALL PROGRESS TO DATABASE", use_container_width=True, type="primary"):
            try: 
                existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Mod3", ttl=0)
                if not existing_df.empty and "User_ID" in existing_df.columns: existing_df = existing_df[existing_df["User_ID"].astype(str) != str(st.session_state.user_id)]
            except: existing_df = pd.DataFrame()
            conn.update(spreadsheet=SHEET_URL, worksheet="Mod3", data=pd.concat([existing_df, pd.DataFrame([final_mod3_data])], ignore_index=True) if not existing_df.empty else pd.DataFrame([final_mod3_data]))
            st.success("✅ Module 3 Progress Successfully Saved!")
            st.balloons()

# --- 8. DASHBOARD SYSTEM ---
def get_row_html(title, deadline, is_locked):
    bg_color = "rgba(239, 68, 68, 0.15)" if is_locked else "rgba(34, 197, 94, 0.15)"
    border_color = "#EF4444" if is_locked else "#22C55E"
    status_text = "🔒 CLOSED" if is_locked else "🟢 OPEN"
    return f"""<div style="background-color: {bg_color}; border-left: 5px solid {border_color}; padding: 8px 15px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
        <div style="flex: 1.5; font-size: 1.05em; font-weight: bold; color: #E2E8F0;">{title}</div><div style="flex: 1; font-family: monospace; color: #94A3B8; text-align: center;">{deadline}</div><div style="flex: 1.5; font-weight: bold; color: {border_color}; text-align: right;">{status_text}</div></div>"""

def dashboard():
    u = st.session_state.user_info
    st.markdown("<h2 style='text-align: center;'>🏥 HFDB Online Data Reporting and Submission Portal</h2>", unsafe_allow_html=True)
    st.info(f"Facility: **{u['hosp']}** | Department: **{u.get('dept', 'General')}** | Encoder: **{u['user']}**")
    
    d1_str, d1_locked = get_module_config("Mod1")
    d2_str, d2_locked = get_module_config("Mod2")
    d3_str, d3_locked = get_module_config("Mod3")
    
    modules = [
        {"id": "Mod1", "title": "📊 Hospital Scorecard", "date": d1_str, "locked": d1_locked, "marker": "marker-blue"},
        {"id": "Mod2", "title": "📈 Hospital Census & HCPN", "date": d2_str, "locked": d2_locked, "marker": "marker-red"},
        {"id": "Mod3", "title": "🌿 Green Viability Assessment", "date": d3_str, "locked": d3_locked, "marker": "marker-green"}
    ]
    
    for state, ls in [("🟢 Ongoing", [m for m in modules if not m["locked"] and m["date"].upper() not in ["UPCOMING", "TBA"]]),
                      ("🔴 Lapsed", [m for m in modules if m["locked"] and m["date"].upper() not in ["UPCOMING", "TBA"]])]:
        if ls:
            st.markdown(f"### {state} Data Submission Modules")
            for m in ls:
                st.markdown(get_row_html(m["title"], m["date"], m["locked"]), unsafe_allow_html=True)
                st.markdown(f'<div class="marker {m["marker"]}"></div>', unsafe_allow_html=True)
                if st.button(f"VIEW {m['id'].upper()}" if state.startswith("🔴") else f"OPEN {m['id'].upper()}", use_container_width=True, key=f"btn_{m['id']}"):
                    st.session_state.current_module = m['id']; st.rerun()
                st.markdown("<hr style='margin: 10px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)
            
    upcoming = [m for m in modules if m["date"].upper() in ["UPCOMING", "TBA"]]
    if upcoming:
        st.markdown("### ⏳ Upcoming Modules")
        for m in upcoming:
            st.markdown(f"""<div style="background-color: rgba(100, 116, 139, 0.15); border-left: 5px solid #64748B; padding: 8px 15px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;"><div style="flex: 1.5; font-size: 1.05em; font-weight: bold; color: #94A3B8;">{m["title"]}</div><div style="flex: 1; font-family: monospace; color: #64748B; text-align: center;">{m["date"]}</div><div style="flex: 1.5; font-weight: bold; color: #64748B; text-align: right;">⏳ PENDING</div></div>""", unsafe_allow_html=True)
            st.button(f"🔒 {m['id'].upper()} IS UNAVAILABLE", use_container_width=True, disabled=True, key=f"btn_upc_{m['id']}")
            st.markdown("<hr style='margin: 10px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)
        
    st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

def render_user_sidebar():
    with st.sidebar:
        st.markdown("### 💬 Live Support Chat")
        if st.button("🔄 Press here to refresh chat replies", use_container_width=True): st.rerun()
        
        try: chat_df = conn.read(spreadsheet=SHEET_URL, worksheet="Support_Logs", ttl=1)
        except: chat_df = pd.DataFrame(columns=["Timestamp", "User_ID", "Hospital", "Encoder_Name", "Sender", "Message"])
            
        u_id = str(st.session_state.user_id)
        chat_container = st.container(height=400)
        with chat_container:
            if not chat_df.empty and "User_ID" in chat_df.columns:
                user_chats = chat_df[chat_df["User_ID"].astype(str) == u_id]
                for _, row in user_chats.iterrows():
                    with st.chat_message("user" if row["Sender"] == "User" else "assistant"):
                        sender_label = "Admin" if row["Sender"] == "Admin" else f"User - {row.get('Encoder_Name', 'Unknown')}"
                        st.markdown(f"**{sender_label}**\n\n{row['Message']}")
                        st.caption(row["Timestamp"])
            else: st.info("No messages yet. Ask us anything!")

        prompt = st.chat_input("Type your message to HFDB...")
        if prompt:
            new_msg = {"Timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"), "User_ID": u_id, "Hospital": st.session_state.user_info['hosp'], "Encoder_Name": st.session_state.user_info['user'], "Sender": "User", "Message": prompt}
            conn.update(spreadsheet=SHEET_URL, worksheet="Support_Logs", data=pd.concat([chat_df, pd.DataFrame([new_msg])], ignore_index=True) if not chat_df.empty else pd.DataFrame([new_msg]))
            st.rerun()

# --- 9. THE TRAFFIC CONTROLLER ---
if "user_id" not in st.session_state: 
    with st.sidebar:
        st.markdown("### 💬 Live Support Chat")
        st.info("🔒 Please log in to access the live support chat.")
    login_screen()
else:
    if str(st.session_state.user_info.get("role")).strip().lower() == "user":
        render_user_sidebar()
        
    announcement_text = get_announcement()
    if announcement_text:
        st.warning(f"📢 **ANNOUNCEMENT:** {announcement_text}")
        
    if "current_module" in st.session_state:
        mod = st.session_state.current_module
        if mod == "Mod1": render_mod1()
        elif mod == "Mod2": render_mod2()
        elif mod == "Mod3": render_mod3()
        elif mod == "Admin_Mod1": admin_analysis_view("Mod1", "📊 Scorecard Data Analysis")
        elif mod == "Admin_Mod2": admin_analysis_view("Mod2", "📈 Census Data Analysis")
        elif mod == "Admin_Mod3": admin_analysis_view("Mod3", "🌿 Green Viability Dashboard")
        elif mod == "Admin_Chat": admin_chat_view()
    else: 
        if str(st.session_state.user_info.get("role")).strip().lower() == "admin": admin_dashboard()
        else: dashboard()
