import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="HFDB Document Searching Tool", layout="wide")

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
        color: #ffffff !important; text-shadow: 0 0 5px rgba(0, 255, 204, 0.8), 0 0 10px rgba(0, 255, 204, 0.3) !important;
    }
    .stTextInput > div > div > input { 
        border-radius: 10px; border: 1px solid #00ffcc !important; background-color: transparent !important; color: #ffffff !important; box-shadow: 0 0 5px rgba(0, 255, 204, 0.2) !important;
    }
    .action-panel { padding: 20px; border-radius: 15px; border: 1px solid #00ffcc; background-color: rgba(0, 255, 204, 0.03); }
    @media (max-width: 768px) { .stTabs [data-baseweb="tab"] { padding-left: 10px !important; padding-right: 10px !important; } .stTabs [data-baseweb="tab"] p { font-size: 13px !important; } }
    .stButton > button { background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: #000000 !important; font-weight: bold; border-radius: 12px; height: 50px; width: 100%; border: none; }
    .mobile-hint { background: #007bff; color: #ffffff !important; padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 15px; animation: pulse 1.5s infinite; display: block; }
    @media (min-width: 768px) { .mobile-hint { display: none !important; } }
    @keyframes pulse { 0% { transform: scale(1); box-shadow: 0 0 5px rgba(0, 123, 255, 0.4); } 50% { transform: scale(0.98); box-shadow: 0 0 15px rgba(0, 123, 255, 0.7); } 100% { transform: scale(1); box-shadow: 0 0 5px rgba(0, 123, 255, 0.4); } }
    </style>
""", unsafe_allow_html=True)

# --- 2. GSPREAD AUTHENTICATION & LOADING ---
# We use st.cache_resource for the client so we don't authenticate on every single click
@st.cache_resource
def get_gspread_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

try:
    client = get_gspread_client()
    
    # Replace this with the exact name of your Google Sheet document
    SHEET_NAME = "2026 Receiving/Releasing" 
    doc = client.open(SHEET_NAME)
    
    # Load Worksheets
    ws_in = doc.worksheet("IN")
    ws_out = doc.worksheet("OUT")
    ws_user = doc.worksheet("USER")
    
    # Convert to Pandas Dataframes for the UI (gspread gets ALL columns automatically, fixing the Staff Notes issue!)
    df_in_raw = pd.DataFrame(ws_in.get_all_records())
    df_out_raw = pd.DataFrame(ws_out.get_all_records())
    user_df = pd.DataFrame(ws_user.get_all_records())
    
    # 1. Format main Search Grids
    df_in = df_in_raw.iloc[:, :14].fillna("")
    df_out = df_out_raw.iloc[:, :14].fillna("")
    
    # 2. VIRTUAL NOM (From the raw IN sheet)
    nom_mask = df_in_raw['DOCUMENT TYPE'].astype(str).str.contains('Notice of Meeting', case=False, na=False)
    # We grab exactly the named columns to avoid any index shifting issues
    nom_cols = ['DATE RECEIVED', 'DTRAK NO.', 'OFFICE CONTROL NO.', 'SUBJECT', 'ORIGINATING OFFICE', 'DIVISION/ UNIT/ COMMITTEE', 'TECHNICAL STAFF ASSIGNED', 'ADMIN NOTES', 'STAFF NOTES', 'LINKED PMR DTRAK', 'LINKED PMR SUBJECT']
    
    # Ensure the linked columns exist in the dataframe before slicing
    for col in ['LINKED PMR DTRAK', 'LINKED PMR SUBJECT']:
        if col not in df_in_raw.columns:
            df_in_raw[col] = ""
            
    df_nom = df_in_raw[nom_mask][nom_cols].fillna("").reset_index()
    # Rename for the UI display
    df_nom_ui = df_nom.copy()
    df_nom_ui.columns = ["Original_Row", "Date Received", "DTRAK No.", "Control No.", "Subject", "Origin", "Division", "Staff Assigned", "Admin Notes", "Staff Notes", "🔗 Linked PMR", "🔗 PMR Subject"]
    
    # 3. VIRTUAL PMR
    pmr_mask = df_in_raw['SUBJECT'].astype(str).str.contains('PMR|MOM', case=False, regex=True, na=False)
    df_pmr = df_in_raw[pmr_mask][['DATE RECEIVED', 'DTRAK NO.', 'OFFICE CONTROL NO.', 'SUBJECT']].fillna("").reset_index(drop=True)
    df_pmr.columns = ["Date", "DTRAK", "Control", "Subject"]

except Exception as e:
    st.error(f"⚠️ API Authentication Error. Ensure GCP Service Account is set up! \n\n {e}")
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

# --- 4. THE UI LAYOUT ---
col_main, col_action = st.columns([3.5, 1], gap="small")

with col_main:
    st.title("HFDB Documents")
    tab_in, tab_out, tab_nom = st.tabs(["📥 INCOMING", "📤 OUTGOING", "🤝 MEETINGS"])
    
    config_in = { df_in.columns[i]: st.column_config.TextColumn(list(["Received","Time","DTRAK No.","Control No.","Subject","Doc Type","Origin","Acted","Time","Sent","Division","Staff","Tag","Action Taken"])[i]) for i in range(14) }
    config_out = { df_out.columns[i]: st.column_config.TextColumn(list(["Date","Time","Control No.","Subject","Former DTRAK","Current DTRAK","Doc Type","Staff","Action Taken","Date Acted","Time","Status","Admin Date","Admin Time"])[i]) for i in range(14) }

    config_nom = {
        "Original_Row": None, # Hide the technical index
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
        q_in = st.text_input("Search Incoming Documents", placeholder="🔍 Search...", key="in_search")
        filtered_in = df_in[df_in.astype(str).apply(lambda x: x.str.contains(q_in, case=False)).any(axis=1)] if q_in else df_in
        selection_in = st.dataframe(filtered_in, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", column_config=config_in, key="in_grid")

    with tab_out:
        q_out = st.text_input("Search Outgoing Documents", placeholder="🔍 Search...", key="out_search")
        filtered_out = df_out[df_out.astype(str).apply(lambda x: x.str.contains(q_out, case=False)).any(axis=1)] if q_out else df_out
        selection_out = st.dataframe(filtered_out, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", column_config=config_out, key="out_grid")
        
    with tab_nom:
        q_nom = st.text_input("Search Notice of Meetings (NOM)", placeholder="🔍 Search Title or Date...", key="nom_search")
        filtered_nom = df_nom_ui[df_nom_ui.astype(str).apply(lambda x: x.str.contains(q_nom, case=False)).any(axis=1)] if q_nom else df_nom_ui
        
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
                # gspread includes the header row, so we add 2 to convert Pandas index to Google Sheet Row Number
                actual_sheet_row = current_nom["Original_Row"] + 2 

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
                        
                        with st.spinner("Writing to Google Sheets..."):
                            try:
                                # We find exactly which columns in GSheets correspond to our new Linked headers
                                # Assuming they are added at the end (e.g., Column S and T). 
                                # Let's assume Column Q is Staff Notes, so we write to R and S
                                ws_in.update_cell(actual_sheet_row, 18, pmr_dtrak) # Column R
                                ws_in.update_cell(actual_sheet_row, 19, pmr_subj)  # Column S
                                
                                st.balloons()
                                st.success("✅ Permanently Linked in GSheets!")
                                st.rerun() # Refresh app to show new data
                            except Exception as write_err:
                                st.error(f"Write failed: {write_err}")
                    else:
                        st.warning("Please choose a valid PMR.")
            else:
                st.info("Tap a row in the Meetings Log to link a PMR.")
            st.markdown('</div>', unsafe_allow_html=True)

with col_action:
    # --- File Request Panel remains unchanged ---
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
