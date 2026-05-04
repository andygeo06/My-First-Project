import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import re

# --- 1. PAGE CONFIG, THEME & SESSION STATE ---
st.set_page_config(page_title="HFDB Document Searching Tool", layout="wide")

# UPGRADE: Session State is now a dictionary for instant inline matching
if "linked_pmrs" not in st.session_state:
    st.session_state.linked_pmrs = {}

st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0% !important; }
    [data-testid="stDecoration"] { display: none; }
    .block-container { padding-top: 2rem !important; margin-top: -3.8rem !important; padding-bottom: 8rem !important; }
    [data-testid="stVerticalBlock"] > div:first-child { margin-top: 0px !important; padding-top: 0px !important; }
    
    .sentinel-line {
        border: 0; height: 1px;
        background: linear-gradient(to right, rgba(0, 255, 204, 0), rgba(0, 255, 204, 0.8), rgba(0, 255, 204, 0));
        margin: 5px 0 15px 0; box-shadow: 0 0 8px rgba(0, 255, 204, 0.4);
    }
    html, body, [class*="st-"], .stMarkdown, h1, h2, h3, p, label {
        color: #ffffff !important;
        text-shadow: 0 0 5px rgba(0, 255, 204, 0.8), 0 0 10px rgba(0, 255, 204, 0.3) !important;
    }
    .stTextInput > div > div > input { 
        border-radius: 10px; border: 1px solid #00ffcc !important; 
        background-color: transparent !important; color: #ffffff !important;
        box-shadow: 0 0 5px rgba(0, 255, 204, 0.2) !important;
    }
    .action-panel { 
        padding: 20px; border-radius: 15px; border: 1px solid #00ffcc;
        background-color: rgba(0, 255, 204, 0.03);
    }
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab"] { padding-left: 10px !important; padding-right: 10px !important; }
        .stTabs [data-baseweb="tab"] p { font-size: 13px !important; }
    }
    @media (prefers-color-scheme: light) {
        [data-testid="stAppViewContainer"] { background-color: #f0f2f6 !important; }
        html, body, [class*="st-"], .stMarkdown, h1, h2, h3, p, label {
            color: #1f2937 !important; text-shadow: 0 0 3px rgba(0, 138, 123, 0.2) !important;
        }
        .stTextInput > div > div > input { border: 1px solid #008a7b !important; color: #1f2937 !important; }
    }
    .stButton > button { 
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); 
        color: #000000 !important; text-shadow: none !important; font-weight: bold; 
        border-radius: 12px; height: 50px; width: 100%; border: none;
    }
    .mobile-hint {
        background: #007bff; color: #ffffff !important; 
        text-shadow: 0 0 5px rgba(255, 255, 255, 0.5) !important;
        padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; 
        margin-bottom: 15px; animation: pulse 1.5s infinite; display: block; 
    }
    @media (min-width: 768px) { .mobile-hint { display: none !important; } }
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 5px rgba(0, 123, 255, 0.4); }
        50% { transform: scale(0.98); box-shadow: 0 0 15px rgba(0, 123, 255, 0.7); }
        100% { transform: scale(1); box-shadow: 0 0 5px rgba(0, 123, 255, 0.4); }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING & VIRTUAL FILTERING ---
def load_sheet_data(url, sheet_name):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if not match: return pd.DataFrame()
    doc_id = match.group(1)
    safe_name = sheet_name.replace(" ", "%20")
    csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&sheet={safe_name}"
    try: return pd.read_csv(csv_url)
    except: return pd.DataFrame()

try:
    SHEET_URL = st.secrets["gsheets_url"]
    
    df_in_raw = load_sheet_data(SHEET_URL, "INCOMING SEARCH")
    df_out_raw = load_sheet_data(SHEET_URL, "OUTGOING SEARCH")
    user_df = load_sheet_data(SHEET_URL, "USER")
    
    # 1. Load the true MASTER IN sheet
    df_master_in = load_sheet_data(SHEET_URL, "IN")
    
    # THE "GHOST COLUMN" FIX: Bruteforce pad the table to guarantee Index 16 exists
    while len(df_master_in.columns) < 17:
        df_master_in[f"BlankCol_{len(df_master_in.columns)}"] = ""
    
    df_in = df_in_raw.iloc[:, :14].fillna("")
    df_out = df_out_raw.iloc[:, :14].fillna("")
    
    # 2. VIRTUAL NOM
    nom_mask = df_master_in.iloc[:, 5].astype(str).str.contains('Notice of Meeting', case=False, na=False)
    df_nom = df_master_in[nom_mask].iloc[:, [0, 2, 3, 4, 6, 10, 11, 13, 16]].fillna("").reset_index(drop=True)
    
    # Explicitly name the columns so Streamlit knows exactly what to render
    df_nom.columns = ["Date Received", "DTRAK No.", "Control No.", "Subject", "Origin", "Division", "Staff Assigned", "Admin Notes", "Staff Notes"]
    
    # THE "INLINE MERGE": Dynamically add session data to the end of the dataframe
    df_nom["Linked PMR DTRAK"] = df_nom["DTRAK No."].apply(lambda x: st.session_state.linked_pmrs.get(x, {}).get("dtrak", ""))
    df_nom["Linked PMR Subject"] = df_nom["DTRAK No."].apply(lambda x: st.session_state.linked_pmrs.get(x, {}).get("subject", ""))
    
    # 3. VIRTUAL PMR
    pmr_mask = df_master_in.iloc[:, 4].astype(str).str.contains('PMR|MOM', case=False, regex=True, na=False)
    df_pmr = df_master_in[pmr_mask].iloc[:, [0, 2, 3, 4]].fillna("").reset_index(drop=True) 
    df_pmr.columns = ["Date", "DTRAK", "Control", "Subject"]

except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 3. SIGNAL FUNCTION ---
def send_signal(user_name, user_email, dtrak_list):
    bot_email = st.secrets["BOT_EMAIL"]
    bot_pw = st.secrets["BOT_PASSWORD"]
    for dtrak in dtrak_list:
        msg = MIMEText(f"SENTINEL REQUEST: {dtrak} for {user_name}")
        msg['Subject'] = str(dtrak)
        msg['From'] = f"Sentinel Cloud <{bot_email}>"
        msg['To'] = bot_email
        if user_email and str(user_email) != 'nan':
            msg['Reply-To'] = user_email
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(bot_email, bot_pw)
                server.send_message(msg)
        except: return False
    return True

# --- 4. THE UI LAYOUT ---
col_main, col_action = st.columns([3.5, 1], gap="small")

with col_main:
    st.title("HFDB Documents")
    
    tab_in, tab_out, tab_nom = st.tabs(["📥 INCOMING", "📤 OUTGOING", "🤝 MEETINGS"])
    
    config_in = {
        df_in.columns[0]: st.column_config.TextColumn("Received", width="small"),
        df_in.columns[1]: st.column_config.TextColumn("Time", width=45),
        df_in.columns[2]: st.column_config.TextColumn("DTRAK No.", width=110),
        df_in.columns[3]: st.column_config.TextColumn("Control No.", width=110),
        df_in.columns[4]: st.column_config.TextColumn("Subject", width="large"),
        df_in.columns[5]: st.column_config.TextColumn("Doc Type", width="small"),
        df_in.columns[6]: st.column_config.TextColumn("Origin", width="small"),
        df_in.columns[7]: st.column_config.TextColumn("Acted", width="small"),
        df_in.columns[8]: st.column_config.TextColumn("Time", width=45),
        df_in.columns[9]: st.column_config.TextColumn("Sent", width="small"),
        df_in.columns[10]: st.column_config.TextColumn("Division", width="small"),
        df_in.columns[11]: st.column_config.TextColumn("Staff", width="small"),
        df_in.columns[12]: st.column_config.TextColumn("Tag", width="small"),
        df_in.columns[13]: st.column_config.TextColumn("Action Taken", width="large"),
    }

    config_out = {
        df_out.columns[0]: st.column_config.TextColumn("Date", width="small"),
        df_out.columns[1]: st.column_config.TextColumn("Time", width=45),
        df_out.columns[2]: st.column_config.TextColumn("Control No.", width=110),
        df_out.columns[3]: st.column_config.TextColumn("Subject", width="large"),
        df_out.columns[4]: st.column_config.TextColumn("Former DTRAK", width=110),
        df_out.columns[5]: st.column_config.TextColumn("Current DTRAK", width=110),
        df_out.columns[6]: st.column_config.TextColumn("Doc Type", width="small"),
        df_out.columns[7]: st.column_config.TextColumn("Staff", width="small"),
        df_out.columns[8]: st.column_config.TextColumn("Action Taken", width="large"),
        df_out.columns[9]: st.column_config.TextColumn("Date Acted", width="small"),
        df_out.columns[10]: st.column_config.TextColumn("Time", width=45),
        df_out.columns[11]: st.column_config.TextColumn("Status", width="small"),
        df_out.columns[12]: st.column_config.TextColumn("Admin Date", width="small"),
        df_out.columns[13]: st.column_config.TextColumn("Admin Time", width=45),
    }

    # Because we explicitly named the columns, this configuration is now bulletproof
    config_nom = {
        "Date Received": st.column_config.TextColumn("Date Received", width="small"),
        "DTRAK No.": st.column_config.TextColumn("DTRAK No.", width=110),
        "Control No.": st.column_config.TextColumn("Control No.", width=110),
        "Subject": st.column_config.TextColumn("Subject", width="large"),
        "Origin": st.column_config.TextColumn("Origin", width="small"),
        "Division": st.column_config.TextColumn("Division", width="small"),
        "Staff Assigned": st.column_config.TextColumn("Staff Assigned", width="small"),
        "Admin Notes": st.column_config.TextColumn("Admin Notes", width="medium"),
        "Staff Notes": st.column_config.TextColumn("Staff Notes", width="medium"),
        # The new inline Linked PMR columns!
        "Linked PMR DTRAK": st.column_config.TextColumn("🔗 Linked PMR", width=110),
        "Linked PMR Subject": st.column_config.TextColumn("🔗 PMR Subject", width="large"),
    }

    with tab_in:
        q_in = st.text_input("Search Incoming Documents", placeholder="🔍 Search...", key="in_search")
        filtered_in = df_in[df_in.astype(str).apply(lambda x: x.str.contains(q_in, case=False)).any(axis=1)] if q_in else df_in
        selection_in = st.dataframe(filtered_in, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", column_config=config_in, key="in_grid")

    with tab_out:
        q_out = st.text_input("Search Outgoing Documents", placeholder="🔍 Search...", key="out_search")
        filtered_out = df_out[df_out.astype(str).apply(lambda x: x.str.contains(q_out, case=False)).any(axis=1)] if q_out else df_out
        selection_out = st.dataframe(filtered_out, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", column_config=config_out, key="out_grid")
        
    with tab_nom:
        q_nom = st.text_input("Search Notice of Meetings (NOM)", placeholder="🔍 Search Title or Date...", key="nom_search")
        filtered_nom = df_nom[df_nom.astype(str).apply(lambda x: x.str.contains(q_nom, case=False)).any(axis=1)] if q_nom else df_nom
        
        sub_col_nom, sub_col_link = st.columns([2.5, 1], gap="medium")
        
        with sub_col_nom:
            st.markdown("##### 📅 Meetings Log")
            # The table now automatically includes the Linked PMR columns at the end!
            selection_nom = st.dataframe(filtered_nom, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", column_config=config_nom, key="nom_grid")
            
        with sub_col_link:
            st.markdown("##### 🔗 Link Report")
            st.markdown('<div class="action-panel" style="padding:15px; margin-top:0px;">', unsafe_allow_html=True)
            
            sel_nom_rows = selection_nom.selection.rows
            
            if len(sel_nom_rows) > 0:
                selected_idx = sel_nom_rows[0]
                current_nom = filtered_nom.iloc[selected_idx]
                
                # Using our explicit names instead of blind indices
                nom_dtrak = current_nom["DTRAK No."]
                nom_subj = current_nom["Subject"]

                st.info(f"**Selected NOM:**\n{nom_dtrak}\n{nom_subj}")

                # Populate Dropdown using explicit column names
                pmr_options = ["--- Select PMR to Assign ---"] + (
                    df_pmr["DTRAK"].astype(str) + " | " + df_pmr["Subject"].astype(str)
                ).tolist()
                
                selected_pmr = st.selectbox("Assign PMR:", pmr_options, label_visibility="collapsed")
                
                if st.button("CONFIRM LINK", key="link_btn"):
                    if selected_pmr != pmr_options[0]:
                        pmr_parts = selected_pmr.split(" | ", 1)
                        pmr_dtrak = pmr_parts[0]
                        pmr_subj = pmr_parts[1] if len(pmr_parts) > 1 else ""
                        
                        # Save linkage to Session State (Triggers a rerun and updates the table instantly)
                        st.session_state.linked_pmrs[nom_dtrak] = {"dtrak": pmr_dtrak, "subject": pmr_subj}
                        
                        st.balloons()
                        st.rerun() # Forces the UI to refresh immediately so the new column populates
                    else:
                        st.warning("Please choose a valid PMR.")
            else:
                st.info("Tap a row in the Meetings Log to link a PMR.")
            st.markdown('</div>', unsafe_allow_html=True)

with col_action:
    sel_in = selection_in.selection.rows
    sel_out = selection_out.selection.rows
    if len(sel_in) > 0 or len(sel_out) > 0:
        st.markdown('<div class="mobile-hint">👇 SCROLL DOWN TO FINISH REQUEST</div>', unsafe_allow_html=True)

    st.markdown('<div class="action-panel">', unsafe_allow_html=True)
    st.header("📤 File Request")
    
    names_list = [""] + user_df.iloc[:, 0].dropna().tolist()
    user_name = st.selectbox("Select Your Name in the Dropdown", names_list, label_visibility="collapsed")
    st.divider()
    
    if len(sel_in) > 0 or len(sel_out) > 0:
        total_selected = len(sel_in) + len(sel_out)
        st.write(f"**Selected:** {total_selected}")
        
        selected_dtraks = []
        if sel_in: selected_dtraks.extend(filtered_in.iloc[sel_in, 2].tolist())
        if sel_out: selected_dtraks.extend(filtered_out.iloc[sel_out, 5].tolist())
        for d in selected_dtraks: st.info(f"📄 {d}")
        
        if st.button("SEND TO MY EMAIL"):
            if not user_name: st.error("Select name!")
            else:
                with st.spinner("Processing..."):
                    try: user_email = user_df[user_df.iloc[:, 0] == user_name].iloc[0, 1]
                    except: user_email = None
                    if send_signal(user_name, user_email, selected_dtraks):
                        st.snow()
                        st.success("Done!")
    else:
        st.warning("Kindly select which item(s) to request.")
    st.markdown('</div>', unsafe_allow_html=True)
