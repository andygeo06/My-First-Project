import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="HFDB Document Searching Tool", layout="wide")

st.markdown("""
    <style>
    /* Hide default Streamlit headers and footers for a clean app feel */
    header[data-testid="stHeader"] { visibility: hidden; height: 0% !important; }
    [data-testid="stDecoration"] { display: none; }
    .block-container { padding-top: 2rem !important; margin-top: -3.8rem !important; padding-bottom: 8rem !important; }
    [data-testid="stVerticalBlock"] > div:first-child { margin-top: 0px !important; padding-top: 0px !important; }
    
    /* Search Bar Styling - Adaptive borders with no forced text color */
    .stTextArea > div > div > textarea { 
        border-radius: 10px; 
        border: 2px solid rgba(0, 150, 255, 0.4) !important; 
        background-color: transparent !important; 
        box-shadow: 0 0 8px rgba(0, 150, 255, 0.1) !important;
    }
    
    /* Action Panel - Uses semi-transparent colors so it looks soft in light mode and sleek in dark mode */
    .action-panel { 
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid rgba(0, 150, 255, 0.3); 
        background-color: rgba(0, 150, 255, 0.05); 
    }
    
    /* Responsive Tabs for Mobile */
    @media (max-width: 768px) { 
        .stTabs [data-baseweb="tab"] { padding-left: 10px !important; padding-right: 10px !important; } 
        .stTabs [data-baseweb="tab"] p { font-size: 13px !important; } 
    }
    
    /* Global Primary Button Gradient - White text always looks good on this blue gradient */
    .stButton > button { 
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); 
        color: #ffffff !important; 
        font-weight: bold; 
        border-radius: 12px; 
        height: 50px; 
        width: 100%; 
        border: none; 
    }
    
    /* Mobile Hint Animation */
    .mobile-hint { 
        background: #007bff; color: #ffffff !important; padding: 10px; 
        border-radius: 10px; text-align: center; font-weight: bold; 
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

# --- 2. GSPREAD AUTHENTICATION & CACHED LOADING ---
@st.cache_resource
def get_gspread_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

# Cache the data fetching for 30 seconds to prevent API Quota Limits!
@st.cache_data(ttl=30, show_spinner=False)
def fetch_sheet_data():
    c = get_gspread_client()
    d = c.open_by_url(st.secrets["GSHEETS_URL"])
    return (
        d.worksheet("IN").get_all_values(),
        d.worksheet("OUT").get_all_values(),
        d.worksheet("USER").get_all_values(),
        d.worksheet("LINK_DB").get_all_values()
    )

try:
    client = get_gspread_client()
    SHEET_URL = st.secrets["GSHEETS_URL"] 
    doc = client.open_by_url(SHEET_URL)
    
    # We define this here so the "Confirm Link" button has permission to write data later
    ws_link = doc.worksheet("LINK_DB")
    
    # Load data using the new cached function
    data_in, data_out, data_user, data_link = fetch_sheet_data()
    
    MIN_COLS = 20
    pad_in = [r + [""] * (MIN_COLS - len(r)) for r in data_in[3:]]
    pad_out = [r + [""] * (MIN_COLS - len(r)) for r in data_out[2:]]
    pad_user = [r + [""] * (MIN_COLS - len(r)) for r in data_user[1:]]
    
    df_in_raw = pd.DataFrame(pad_in)
    df_out_raw = pd.DataFrame(pad_out)
    user_df = pd.DataFrame(pad_user)
    
    df_in = df_in_raw.iloc[:, :14].fillna("")
    df_in.columns = [str(i) for i in range(14)]
    df_out = df_out_raw.iloc[:, :14].fillna("")
    df_out.columns = [str(i) for i in range(14)]
    
    link_dict = {}
    if len(data_link) > 1:
        for row in data_link[1:]:
            if len(row) >= 3:
                link_dict[row[0]] = {"dtrak": row[1], "subject": row[2]}

    nom_mask = df_in_raw[5].astype(str).str.contains('Notice of Meeting', case=False, na=False)
    df_nom = df_in_raw[nom_mask][[0, 2, 3, 4, 6, 10, 11, 13, 16]].fillna("").reset_index()
    
    df_nom["Linked PMR DTRAK"] = df_nom[2].astype(str).apply(lambda x: link_dict.get(x, {}).get("dtrak", ""))
    df_nom["Linked PMR Subject"] = df_nom[2].astype(str).apply(lambda x: link_dict.get(x, {}).get("subject", ""))
    
    df_nom_ui = df_nom.copy()
    df_nom_ui.columns = ["Original_Row", "Date Received", "DTRAK No.", "Control No.", "Subject", "Origin", "Division", "Staff Assigned", "Admin Notes", "Staff Notes", "🔗 Linked PMR", "🔗 PMR Subject"]
    
    pmr_mask = df_in_raw[4].astype(str).str.contains('PMR|MOM', case=False, regex=True, na=False)
    df_pmr = df_in_raw[pmr_mask][[0, 2, 3, 4]].fillna("").reset_index(drop=True)
    df_pmr.columns = ["Date", "DTRAK", "Control", "Subject"]

except Exception as e:
    st.error(f"⚠️ App Error: \n\n {e}")
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
        if user_email and str(user_email) != 'nan': msg['Reply-To'] = user_email
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(bot_email, bot_pw)
                server.send_message(msg)
        except: return False
    return True

# --- NEW: MASS SEARCH HELPER FUNCTION ---
def mass_search_filter(df, query):
    if not query:
        return df
        
    search_terms = [term.strip() for term in re.split(r'[\n\t,]+', query) if term.strip()]
    
    if not search_terms:
        return df
        
    pattern = '|'.join([re.escape(term) for term in search_terms])
    
    return df[df.astype(str).apply(lambda x: x.str.contains(pattern, case=False, regex=True)).any(axis=1)]

# --- 4. THE UI LAYOUT ---
col_main, col_action = st.columns([3.5, 1], gap="small")

with col_main:
    st.title("HFDB Documents")
    tab_in, tab_out, tab_nom = st.tabs(["📥 INCOMING", "📤 OUTGOING", "🤝 MEETINGS"])
    
    config_in = { df_in.columns[i]: st.column_config.TextColumn(list(["Received","Time","DTRAK No.","Control No.","Subject","Doc Type","Origin","Acted","Time","Sent","Division","Staff","Tag","Action Taken"])[i]) for i in range(14) }
    config_out = { df_out.columns[i]: st.column_config.TextColumn(list(["Date","Time","Control No.","Subject","Former DTRAK","Current DTRAK","Doc Type","Staff","Action Taken","Date Acted","Time","Status","Admin Date","Admin Time"])[i]) for i in range(14) }

    config_nom = {
        "Original_Row": None, 
        "Date Received": st.column_config.TextColumn("Date Received", width="small"),
        "DTRAK No.": st.column_config.TextColumn("DTRAK No.", width=110),
        "Control No.": st.column_config.TextColumn("Control No.", width=110),
        "Subject": st.column_config.TextColumn("Subject", width="large"),
        "Origin": st.column_config.TextColumn("Origin", width="small"),
        "Division": st.column_config.TextColumn("Division", width="small"),
        "Staff Assigned": st.column_config.TextColumn("Staff Assigned", width="small"),
        "Admin Notes": st.column_config.TextColumn("Admin Notes", width="medium"),
        "Staff Notes": st.column_config.TextColumn("Staff Notes", width="medium"),
        "🔗 Linked PMR": st.column_config.TextColumn("🔗 Linked PMR", width=110),
        "🔗 PMR Subject": st.column_config.TextColumn("🔗 PMR Subject", width="large"),
    }

    with tab_in:
        col_search_in, col_btn_in = st.columns([5, 1])
        with col_search_in:
            q_in = st.text_area("Search Incoming Documents", placeholder="🔍 Paste multiple DTRAK or Control Nos. from Google Sheets here...", key="in_search", height=68)
        with col_btn_in:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.button("🔍 SEARCH", key="btn_search_in")
            
        filtered_in = mass_search_filter(df_in, q_in)
        selection_in = st.dataframe(filtered_in, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", column_config=config_in, key="in_grid")

    with tab_out:
        col_search_out, col_btn_out = st.columns([5, 1])
        with col_search_out:
            q_out = st.text_area("Search Outgoing Documents", placeholder="🔍 Paste multiple DTRAK or Control Nos. from Google Sheets here...", key="out_search", height=68)
        with col_btn_out:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.button("🔍 SEARCH", key="btn_search_out")
            
        filtered_out = mass_search_filter(df_out, q_out)
        selection_out = st.dataframe(filtered_out, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", column_config=config_out, key="out_grid")
        
    with tab_nom:
        col_search_nom, col_btn_nom = st.columns([5, 1])
        with col_search_nom:
            q_nom = st.text_area("Search Notice of Meetings (NOM)", placeholder="🔍 Search Title, Date, or Paste multiple Codes...", key="nom_search", height=68)
        with col_btn_nom:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.button("🔍 SEARCH", key="btn_search_nom")
            
        filtered_nom = mass_search_filter(df_nom_ui, q_nom)
        
        sub_col_nom, sub_col_link = st.columns([2.5, 1], gap="medium")
        
        with sub_col_nom:
            st.markdown("##### 📅 Meetings Log")
            selection_nom = st.dataframe(filtered_nom, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", column_config=config_nom, key="nom_grid")
            
        with sub_col_link:
            st.markdown("##### 🔗 Link Report")
            st.markdown('<div class="action-panel" style="padding:15px; margin-top:0px;">', unsafe_allow_html=True)
            
            sel_nom_rows = selection_nom.selection.rows
            
            if len(sel_nom_rows) > 0:
                selected_idx = sel_nom_rows[0]
                current_nom = filtered_nom.iloc[selected_idx]
                
                nom_dtrak = current_nom["DTRAK No."]
                nom_subj = current_nom["Subject"]
                actual_sheet_row = int(current_nom["Original_Row"]) + 4 

                st.info(f"**Selected NOM:**\n{nom_dtrak}\n{nom_subj}")

                pmr_options = ["--- Select PMR to Assign ---"] + (
                    df_pmr["DTRAK"].astype(str) + " | " + df_pmr["Subject"].astype(str)
                ).tolist()
                
                selected_pmr = st.selectbox("Assign PMR:", pmr_options, label_visibility="collapsed")
                
                if st.button("CONFIRM LINK", key="link_btn"):
                    if selected_pmr != pmr_options[0]:
                        pmr_parts = selected_pmr.split(" | ", 1)
                        pmr_dtrak = pmr_parts[0]
                        pmr_subj = pmr_parts[1] if len(pmr_parts) > 1 else ""
                        
                        with st.spinner("Saving to Link Database..."):
                            try:
                                try:
                                    cell = ws_link.find(nom_dtrak)
                                    ws_link.update_cell(cell.row, 2, pmr_dtrak)
                                    ws_link.update_cell(cell.row, 3, pmr_subj)
                                except:
                                    ws_link.append_row([nom_dtrak, pmr_dtrak, pmr_subj])
                                
                                st.balloons()
                                st.success("✅ Safely Saved to Link DB!")
                                st.rerun() 
                            except Exception as write_err:
                                st.error(f"Database write failed: {write_err}")
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
