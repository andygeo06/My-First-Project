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
    div[data-testid="stAlert"] {{ padding: 0.2rem 0.5rem !important; }}
    div[data-testid="stAlert"] > div {{ align-items: center !important; }}
    div[data-testid="stAlert"] p {{ margin: 0 !important; padding-bottom: 0.2rem !important; line-height: 1.4 !important; }}
    
    /* COMPACT CHAT CSS */
    div[data-testid="stChatMessage"] {{ padding: 0.5rem 0.5rem !important; }}
    div[data-testid="stChatMessageContent"] {{ gap: 0.1rem !important; }}
    div[data-testid="stChatMessage"] .stMarkdown p {{ margin-bottom: 0.2rem !important; font-size: 0.95em; }}
    div[data-testid="stChatMessage"] [data-testid="stIconNode"] {{ width: 1.5rem !important; height: 1.5rem !important; }}
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE & CONFIG HELPERS ---
@st.cache_data(ttl=5)
def get_static_sheet(sheet_name):
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name)
    except:
        return pd.DataFrame()

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
    if df.empty:
        df = pd.DataFrame([["Announcement", text]])
    else:
        if "Announcement" in df.iloc[:, 0].values:
            df.loc[df.iloc[:, 0] == "Announcement", df.columns[1]] = text
        else:
            new_row = pd.DataFrame([["Announcement", text] + [""]*(len(df.columns)-2)], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
    conn.update(spreadsheet=SHEET_URL, worksheet="Config", data=df)
    clear_app_memory()

# --- 4. UNIVERSAL PRINT ENGINE (FOOLPROOF & DYNAMIC) ---
def generate_universal_print_html(module_title, hosp_name, data_dict):
    # Exclude technical tracking columns from the official printout
    exclude_keys = ["Timestamp", "User_ID", "Hospital", "Encoder"]
    
    rows_html = ""
    for key, val in data_dict.items():
        if key in exclude_keys: continue
        
        # Clean up empty or 'nan' values gracefully
        clean_val = "N/A" if pd.isna(val) or str(val).strip() == "" else str(val)
        
        rows_html += f"""
        <tr>
            <td style='padding: 10px; border: 1px solid #cbd5e1; width: 45%; font-weight: 600; color: #1e293b;'>{key}</td>
            <td style='padding: 10px; border: 1px solid #cbd5e1; color: #334155;'>{clean_val}</td>
        </tr>
        """
        
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 class="hosp-title">{hosp_name}</h2>
                <h3 class="module-title">{module_title} - Official Submission Record</h3>
                <div class="meta-box">
                    <span><strong>Encoder:</strong> {encoder}</span>
                    <span><strong>Submitted On:</strong> {timestamp}</span>
                </div>
            </div>
            <table>
                <thead>
                    <tr><th>Form Field / Question</th><th>Submitted Response</th></tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <div class="footer">
                <p>Generated by Project FORT Automated System • Department of Health - HFDB</p>
                <p><i>This is a system-generated document. No signature is required.</i></p>
            </div>
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
            
    st.success("🖨️ **PRINT MODE:** Use your browser's print function (Ctrl+P or Cmd+P) to save this page as a PDF.")
    
    html_content = generate_universal_print_html(module_title, hosp, data)
    st.components.v1.html(html_content, height=800, scrolling=True)

# --- 5. AUTHENTICATION & LOGIN ---
def login_screen():
    st.markdown("<h2 style='text-align: center;'>🏥 HFDB Online Data Reporting and Submission Portal</h2>", unsafe_allow_html=True)
    
    # --- The "Save Your Password" Screen ---
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

    # --- Dual Login System ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔐 Returning User", "📝 New User"])
        
        with tab1:
            with st.form("login_form"):
                access_code = st.text_input("Enter your Access Code", type="password")
                submitted = st.form_submit_button("Secure Login", use_container_width=True)
                
                if submitted:
                    accounts_df = get_static_sheet("Accounts")
                    if not accounts_df.empty:
                        accounts_df["Username"] = accounts_df["Username"].astype(str).str.strip()
                        match = accounts_df[accounts_df["Username"] == access_code.strip()]
                        
                        if not match.empty:
                            user_data = match.iloc[0]
                            st.session_state.user_id = str(uuid.uuid4())
                            access_str = str(user_data.get("Access", "")).strip()
                            st.session_state.user_info = {
                                "user": user_data["Username"],
                                "role": user_data.get("Role", "user"),
                                "hosp": user_data.get("Hospital_Name", "N/A"),
                                "dept": user_data.get("Department", "General"),
                                "access": [m.strip() for m in access_str.split(",")] if access_str else []
                            }
                            st.rerun()
                        else: st.error("❌ Invalid Access Code.")
                    else: st.error("Database connection error.")
                    
        with tab2:
            st.info("First time here? Generate your unique access code below.")
            with st.form("register_form"):
                new_hosp = st.text_input("Hospital Name")
                new_encoder = st.text_input("Encoder Name")
                reg_submit = st.form_submit_button("Generate Login Code", use_container_width=True)
                
                if reg_submit and new_hosp and new_encoder:
                    # Generates a random secure code
                    new_code = "HFDB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    
                    # Store pending data for the warning screen
                    st.session_state.pending_id = new_code
                    st.session_state.pending_info = {
                        "user": new_encoder,
                        "role": "user",
                        "hosp": new_hosp,
                        "dept": "General",
                        "access": ["Mod1", "Mod2", "Mod3", "Chat"]
                    }
                    
                    # Append new user logic to Google Sheets
                    try:
                        accounts_df = get_static_sheet("Accounts")
                        new_row = {"Username": new_code, "Password": "", "Role": "user", "Hospital_Name": new_hosp, "Department": "General", "Access": "Mod1, Mod2, Mod3, Chat"}
                        updated_df = pd.concat([accounts_df, pd.DataFrame([new_row])], ignore_index=True) if not accounts_df.empty else pd.DataFrame([new_row])
                        conn.update(spreadsheet=SHEET_URL, worksheet="Accounts", data=updated_df)
                    except Exception as e:
                        st.error("Failed to save new user to database.")
                        
                    st.rerun()
                    
# --- 6. ADMIN VIEWS ---
def admin_analysis_view(mod_id, title):
    if "show_print" in st.session_state:
        # We need the hospital data to print it
        df = get_static_sheet(mod_id)
        if not df.empty and "Hospital" in df.columns:
            hosp_data = df[df["Hospital"] == st.session_state.show_print]
            if not hosp_data.empty:
                print_view(st.session_state.show_print, hosp_data.iloc[0].to_dict(), title)
                return
                
    st.markdown(f"<h2>{title}</h2>", unsafe_allow_html=True)
    if st.button("⬅️ Back to Admin Dashboard"): 
        del st.session_state.current_module; st.rerun()
        
    df = get_static_sheet(mod_id)
    if df.empty: st.info("No data submitted yet."); return
        
    st.success(f"✅ Total Submissions: **{len(df)}** Hospitals")
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown("### Submitted Hospitals")
        for hosp in df["Hospital"].unique():
            with st.expander(f"🏥 {hosp}"):
                if st.button("🖨️ View Print Format", key=f"print_{hosp}"):
                    st.session_state.show_print = hosp
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
                        # Fixes the 'nan' bug for the Admin screen
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
        st.markdown("Set a banner to display at the top of every hospital's screen. Supports Markdown Links. Leave blank to remove the banner.")
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
    # TEMPORARY PLACEHOLDER FOR MOD 1
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button("⬅️ Dashboard", use_container_width=True): 
            del st.session_state.current_module; st.rerun()
            
    st.markdown("<div class='section-header-strat'><h2 style='margin:0; color:white;'>📊 Module 1: Hospital Scorecard Placeholder</h2></div>", unsafe_allow_html=True)
    st.info("Module 1 exact text layout is pending. This is a placeholder.")

def render_mod2():
    # THE TRUE WORD-FOR-WORD MODULE 2
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        if st.button("⬅️ Dashboard", use_container_width=True): 
            del st.session_state.current_module; st.rerun()
            
    # Red Theme for Module 2
    st.markdown("<div class='section-header-core'><h2 style='margin:0; color:white;'>📈 Module 2: Hospital Data Reporting Form 2025</h2></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8;'>Please ensure all data is accurate as of December 31, 2025.</p>", unsafe_allow_html=True)

    cap_levels = ["Level 1", "Level 2", "Level 3", "Infirmary", "Not Applicable"]

    with st.form("mod2_form"):
        # --- SECTION 1: GENERAL INFO ---
        st.markdown("### 🏥 I. General Information")
        hosp_name = st.text_input("Name of Hospital:", value=st.session_state.user_info.get('hosp', ''))
        
        c_cap1, c_cap2, c_cap3 = st.columns(3)
        with c_cap1:
            cap_2025 = st.selectbox("Health Facility Service Capability Level (2025):", cap_levels)
        with c_cap2:
            cap_2026 = st.selectbox("Health Facility Service Capability Level (2026):", cap_levels)
        with c_cap3:
            st.caption("(If the same with 2025/2026, please input the level in the cell)")
            cap_2027 = st.selectbox("Target Health Facility Service Capability Level in 2027:", cap_levels)
            
        st.info("📂 Please upload your LTO (2025) and LTO (2026) on the link provided\n\n**Note:** Please make sure you FOLLOW the proper naming of the file provided:\n`HOSPITAL ACRONYM_LTO_2025_2026` (e.g. SOGHMC_LTO_2025_2026)\nFailing to comply will make your submission INVALID\n\n👉 [https://bit.ly/HDRTFilesUpload](https://bit.ly/HDRTFilesUpload)")

        st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)

        # --- SECTION 2: BED CAPACITY ---
        st.markdown("### 🛏️ II. Bed Capacity")
        
        bc1, bc2 = st.columns(2)
        with bc1:
            abc_lic_2025 = st.number_input("Authorized Bed Capacity (ABC) by Licensing as of December 31, 2025:", min_value=0, step=1)
            abc_law_2025 = st.number_input("Authorized Bed Capacity (ABC) by Law (2025):", min_value=0, step=1)
            ibc_2025 = st.number_input("Implementing Bed Capacity (IBC) (2025):", min_value=0, step=1)
        with bc2:
            abc_lic_2026 = st.number_input("Target Authorized Bed Capacity (ABC) by Licensing by the end of 2026:", min_value=0, step=1)
            abc_law_2026 = st.number_input("Authorized Bed Capacity (ABC) by Law (2026):", min_value=0, step=1)
            
            st.caption("(If the same with 2025/2026, please input the same ABC in the cell. If the ABC would increase in 2026, kindly indicate in the cell the target ABC and the target quarter for which it will be implemented in the REMARKS column)")
            abc_lic_2027 = st.number_input("Target Authorized Bed Capacity (ABC) by Licensing in 2027:", min_value=0, step=1)

        st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)

        # --- SECTION 3: HOSPITAL PERFORMANCE ---
        st.markdown("### 📈 III. Hospital Performance")
        
        hp1, hp2, hp3 = st.columns(3)
        with hp1:
            bor_2025 = st.number_input("Bed Occupancy Rate (BOR) based on ABC by licensing (2025):", min_value=0.0, step=0.1, format="%.2f")
            inpatients_2025 = st.number_input("Total Number of Inpatients (2025):", min_value=0, step=1)
        with hp2:
            alos_2025 = st.number_input("Average Length of Stay (ALOS) (2025):", min_value=0.0, step=0.1, format="%.2f")
            outpatients_2025 = st.number_input("Total Number of Outpatient Visits (2025):", min_value=0, step=1)
        with hp3:
            tids_2025 = st.number_input("Total Inpatient Days Served (2025):", min_value=0, step=1)
            er_2025 = st.number_input("Total Number of Emergency Room (ER) visits (2025):", min_value=0, step=1)

        st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)

        # --- SECTION 4: APEX & MOA ---
        st.markdown("### 🤝 IV. Apex/End-Referral & HCPN Linkages")
        
        st.caption("Reference: [DC 2025-0554 \"2024 List of Eligible Apex or End-Referral Hospitals\"](https://bit.ly/2025ApexHospitals)")
        is_apex = st.radio("Based on DC No. 2025-0554, is the hospital identified as Apex or End-Referral Hospital?", ["No", "Yes"])
        
        st.info("📂 For those who already have a signed or on-going review MOA/MOU with a HCPN or province (not with other hospitals and other health facilities), kindly upload a scanned copy or picture of the signed or on-going review MOA/MOU on the link provided\n\n**Note:** Please make sure you FOLLOW the proper naming of the file provided:\n`HOSPITAL ACRONYM_MOA` (e.g. SOGHMC_MOA)\nFailing to comply will make your submission INVALID\n\n👉 [https://bit.ly/HDRTFilesUpload](https://bit.ly/HDRTFilesUpload)")
        
        hcpn_links = st.number_input("If the hospital already has MOA/MOU with a HCPN/province, how many HCPNs or provinces are they linked with?", min_value=0, step=1)

        st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)

        # --- SECTION 5: BUCAS CENTER ---
        st.markdown("### 🏢 V. BUCAS Center Information")
        has_bucas = st.radio("Does the hospital operate a BUCAS Center/s?", ["No", "Yes"])
        
        bucas_coords = ""
        if has_bucas == "Yes":
            st.warning("⚠️ If yes, kindly update the data in the UHC HSC BUCAS Tracker (DM 2025-0026): [https://bit.ly/BUCAStrack](https://bit.ly/BUCAStrack)")
            
            st.caption("Kindly provide the exact coordinates of the BUCAS Center using the format Latitude, Longitude (e.g. 14.6156280516298, 120.982498127343)\n(Can be acquired via Google Maps)")
            bucas_coords = st.text_input("Exact coordinates of the BUCAS Center:")
            
            st.info("📂 If applicable, please provide a copy of the BUCAS Center's license to operate.\n\n**Note:** Please make sure you FOLLOW the proper naming of the file provided:\n`HOSPITAL ACRONYM_BUCAS` (e.g. SOGHMC_BUCAS)\nFailing to comply will make your submission INVALID\n\n👉 [https://bit.ly/HDRTFilesUpload](https://bit.ly/HDRTFilesUpload)")

        st.markdown("<hr style='margin: 15px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)

        # --- SECTION 6: REMARKS & SIGNATORIES ---
        st.markdown("### 📝 VI. Remarks & Signatories")
        
        st.caption("REMARKS (Breakdown of Bed Capacity, Queries, Explanations of data, etc., kindly put on this field)")
        remarks = st.text_area("Remarks Field:")
        
        sig1, sig2 = st.columns(2)
        with sig1:
            st.markdown("**Prepared by:**")
            prep_name = st.text_input("Name (Prepared By):")
            prep_desig = st.text_input("Designation (Prepared By):")
            prep_date = st.date_input("Date Prepared:")
        with sig2:
            st.markdown("**Noted by:**")
            note_name = st.text_input("Name (Noted By):")
            st.text_input("Designation (Noted By):", value="Medical Center Chief / Chief of Hospital", disabled=True)
            note_date = st.date_input("Date Noted:")

        # --- SUBMISSION LOGIC ---
        submit_btn = st.form_submit_button("📤 Submit Module 2", use_container_width=True, type="primary")
        
        if submit_btn:
            new_data = {
                "Timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                "User_ID": st.session_state.user_id,
                "Hospital": hosp_name,
                "Encoder": st.session_state.user_info.get("user", "Unknown"),
                "Capability Level (2025)": cap_2025,
                "Capability Level (2026)": cap_2026,
                "Target Capability Level (2027)": cap_2027,
                "ABC by Licensing (2025)": abc_lic_2025,
                "ABC by Law (2025)": abc_law_2025,
                "IBC (2025)": ibc_2025,
                "Target ABC by Licensing (2026)": abc_lic_2026,
                "ABC by Law (2026)": abc_law_2026,
                "Target ABC by Licensing (2027)": abc_lic_2027,
                "Bed Occupancy Rate (BOR) %": bor_2025,
                "Total Inpatients": inpatients_2025,
                "Average Length of Stay (ALOS)": alos_2025,
                "Total Outpatient Visits": outpatients_2025,
                "Total Inpatient Days Served": tids_2025,
                "Total ER Visits": er_2025,
                "Apex/End-Referral Hospital?": is_apex,
                "HCPN/Province MOA Links": hcpn_links,
                "Operates BUCAS Center?": has_bucas,
                "BUCAS Coordinates": bucas_coords,
                "Remarks": remarks,
                "Prepared By (Name)": prep_name,
                "Prepared By (Designation)": prep_desig,
                "Date Prepared": str(prep_date),
                "Noted By (Name)": note_name,
                "Noted By (Designation)": "Medical Center Chief / Chief of Hospital",
                "Date Noted": str(note_date)
            }
            
            try: existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Mod2", ttl=0)
            except: existing_df = pd.DataFrame()
            
            updated_df = pd.concat([existing_df, pd.DataFrame([new_data])], ignore_index=True) if not existing_df.empty else pd.DataFrame([new_data])
            conn.update(spreadsheet=SHEET_URL, worksheet="Mod2", data=updated_df)
            
            st.success("✅ Module 2 Data Successfully Saved!")
            st.balloons()

def render_mod3():
    st.markdown("<h2 style='text-align: center;'>🌿 Module 3: Green Viability Assessment</h2>", unsafe_allow_html=True)
    if st.button("⬅️ Dashboard", use_container_width=True): del st.session_state.current_module; st.rerun()

# --- 8. DASHBOARD SYSTEM ---
def get_row_html(title, deadline, is_locked):
    bg_color = "rgba(239, 68, 68, 0.15)" if is_locked else "rgba(34, 197, 94, 0.15)"
    border_color = "#EF4444" if is_locked else "#22C55E"
    status_text = "🔒 CLOSED" if is_locked else "🟢 OPEN"
    # Perfect Symmetry for Left/Middle/Right flex
    return f"""<div style="background-color: {bg_color}; border-left: 5px solid {border_color}; padding: 8px 15px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
        <div style="flex: 1.5; font-size: 1.05em; font-weight: bold; color: #E2E8F0;">{title}</div><div style="flex: 1; font-family: monospace; color: #94A3B8; text-align: center;">{deadline}</div><div style="flex: 1.5; font-weight: bold; color: {border_color}; text-align: right;">{status_text}</div></div>"""

def dashboard():
    u = st.session_state.user_info
    st.markdown("<h2 style='text-align: center;'>🏥 HFDB Online Data Reporting and Submission Portal</h2>", unsafe_allow_html=True)
    
    clean_dept = "General" if pd.isna(u.get('dept')) else u.get('dept', 'General')
    st.info(f"Facility: **{u['hosp']}** | Department: **{clean_dept}** | Encoder: **{u['user']}**")
    
    d1_str, d1_locked = get_module_config("Mod1")
    d2_str, d2_locked = get_module_config("Mod2")
    d3_str, d3_locked = get_module_config("Mod3")
    
    modules = [
        {"id": "Mod1", "title": "📊 Hospital Scorecard", "date": d1_str, "locked": d1_locked, "marker": "marker-blue"},
        {"id": "Mod2", "title": "📈 Hospital Census & HCPN", "date": d2_str, "locked": d2_locked, "marker": "marker-red"},
        {"id": "Mod3", "title": "🌿 Green Viability Assessment", "date": d3_str, "locked": d3_locked, "marker": "marker-green"}
    ]
    
    ongoing = [m for m in modules if not m["locked"] and str(m["date"]).strip().upper() not in ["UPCOMING", "TBA"]]
    lapsed = [m for m in modules if m["locked"] and str(m["date"]).strip().upper() not in ["UPCOMING", "TBA"]]
    upcoming = [m for m in modules if str(m["date"]).strip().upper() in ["UPCOMING", "TBA"]]

    if ongoing:
        st.markdown("### 🟢 Ongoing Data Submission Modules")
        for m in ongoing:
            st.markdown(get_row_html(m["title"], m["date"], m["locked"]), unsafe_allow_html=True)
            st.markdown(f'<div class="marker {m["marker"]}"></div>', unsafe_allow_html=True)
            if st.button(f"OPEN {m['id'].upper()}", use_container_width=True, key=f"btn_on_{m['id']}"):
                st.session_state.current_module = m['id']; st.rerun()
            st.markdown("<hr style='margin: 10px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)

    if lapsed:
        st.markdown("### 🔴 Lapsed Data Submission Modules")
        for m in lapsed:
            st.markdown(get_row_html(m["title"], m["date"], m["locked"]), unsafe_allow_html=True)
            st.markdown(f'<div class="marker {m["marker"]}"></div>', unsafe_allow_html=True)
            if st.button(f"VIEW {m['id'].upper()} (READ-ONLY)", use_container_width=True, key=f"btn_lap_{m['id']}"):
                st.session_state.current_module = m['id']; st.rerun()
            st.markdown("<hr style='margin: 10px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)
            
    if upcoming:
        st.markdown("### ⏳ Upcoming Modules")
        for m in upcoming:
            st.markdown(f"""
            <div style="background-color: rgba(100, 116, 139, 0.15); border-left: 5px solid #64748B; padding: 8px 15px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <div style="flex: 1.5; font-size: 1.05em; font-weight: bold; color: #94A3B8;">{m["title"]}</div>
                <div style="flex: 1; font-family: monospace; color: #64748B; text-align: center;">{m["date"]}</div>
                <div style="flex: 1.5; font-weight: bold; color: #64748B; text-align: right;">⏳ PENDING</div>
            </div>""", unsafe_allow_html=True)
            st.button(f"🔒 {m['id'].upper()} IS UNAVAILABLE", use_container_width=True, disabled=True, key=f"btn_upc_{m['id']}")
            st.markdown("<hr style='margin: 10px 0; border: 1px solid #30363D;'>", unsafe_allow_html=True)
        
    st.markdown('<div class="marker marker-amber"></div>', unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

def render_user_sidebar():
    with st.sidebar:
        st.markdown("### 💬 Live Support Chat")
        
        with st.expander("📚 Frequently Asked Questions", expanded=False):
            st.markdown("**Q: When is the deadline?**\nA: Check your dashboard for specific module deadlines.")
            st.markdown("**Q: Can I edit after submitting?**\nA: Once the deadline passes, modules are locked to Read-Only.")
            st.markdown("**Q: Where do I upload MOVs?**\nA: Use the Google Drive link at the bottom of the Module 3 screen.")
            st.markdown("**Q: Who do I contact for technical issues?**\nA: Use the chat below! We will respond ASAP.")
            
        st.caption("⏳ *Note: Messages may take up to 15 seconds to sync across devices.*")
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
                        raw_name = row.get('Encoder_Name', 'Unknown')
                        clean_name = "Unknown" if pd.isna(raw_name) else raw_name
                        sender_label = "Admin" if row["Sender"] == "Admin" else f"User - {clean_name}"
                        st.markdown(f"**{sender_label}**\n\n{row['Message']}")
                        st.caption(row["Timestamp"])
            else:
                st.info("No messages yet. Ask us anything!")

        prompt = st.chat_input("Type your message to HFDB...")
        if prompt:
            new_msg = {
                "Timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"), 
                "User_ID": u_id, "Hospital": st.session_state.user_info['hosp'], 
                "Encoder_Name": st.session_state.user_info['user'], 
                "Sender": "User", "Message": prompt
            }
            if chat_df.empty: updated_df = pd.DataFrame([new_msg])
            else: updated_df = pd.concat([chat_df, pd.DataFrame([new_msg])], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Support_Logs", data=updated_df)
            st.rerun()

# --- 10. THE TRAFFIC CONTROLLER ---
if "user_id" not in st.session_state: 
    with st.sidebar:
        st.markdown("### 💬 Live Support Chat")
        st.info("🔒 Please log in to access the live support chat.")
    login_screen()
else:
    if st.session_state.user_info.get("role") == "user":
        render_user_sidebar()
        
    # --- NEW: Global Persistent Announcement Banner (NO CLOSE BUTTON) ---
    announcement_text = get_announcement()
    if announcement_text:
        st.warning(f"📢 **ANNOUNCEMENT:** {announcement_text}")
        
    if "current_module" in st.session_state:
        if not st.session_state.get("isolated_print_html"):
            if st.button("🏠 Return to Dashboard"): 
                if "show_print" in st.session_state: del st.session_state.show_print
                del st.session_state.current_module; st.rerun()
        
        mod = st.session_state.current_module
        if mod == "Mod1": render_mod1()
        elif mod == "Mod2": render_mod2()
        elif mod == "Mod3": render_mod3()
        elif mod == "Admin_Mod1": admin_analysis_view("Mod1", "📊 Scorecard Data Analysis")
        elif mod == "Admin_Mod2": admin_analysis_view("Mod2", "📈 Census Data Analysis")
        elif mod == "Admin_Mod3": admin_analysis_view("Mod3", "🌿 Green Viability Dashboard")
        elif mod == "Admin_Chat": admin_chat_view()
    else: 
        if st.session_state.user_info.get("role") == "admin": admin_dashboard()
        else: dashboard()
