import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="HFDB Document Searching Tool", layout="wide")

st.markdown("""
    <style>
    /* 1. COMPACT TOP (No Gap) */
    header[data-testid="stHeader"] { visibility: hidden; height: 0% !important; }
    [data-testid="stDecoration"] { display: none; }
    .block-container { padding-top: 0rem !important; padding-bottom: 8rem !important; }

    /* 2. THE GLOW RETURNED */
    /* Title Glow */
    h1 {
        text-shadow: 0 0 10px #00ffcc, 0 0 20px rgba(0, 255, 204, 0.3);
        color: #00ffcc !important;
    }

    /* Search Bar Glow */
    .stTextInput > div > div > input { 
        border-radius: 10px; 
        border: 2px solid #00ffcc !important; 
        background-color: transparent !important;
        box-shadow: 0 0 8px rgba(0, 255, 204, 0.2);
    }

    /* 3. ADAPTIVE EYE-CARE COLORS */
    @media (prefers-color-scheme: light) {
        [data-testid="stAppViewContainer"] { background-color: #f0f2f6 !important; color: #1f2937 !important; }
        .stTabs [data-baseweb="tab"] p { color: #1f2937 !important; font-weight: bold; }
        /* Softer glow for light mode to prevent eye strain */
        h1 { text-shadow: 0 0 5px rgba(0, 138, 123, 0.2); color: #008a7b !important; }
        .stTextInput > div > div > input { border: 2px solid #008a7b !important; color: #004d40 !important; }
    }

    /* 4. ACTION PANEL & GLOWING BUTTON */
    .action-panel { 
        padding: 20px; 
        border-radius: 15px; 
        border: 2px solid #00ffcc;
        background-color: rgba(0, 255, 204, 0.05);
        box-shadow: 0 4px 15px rgba(0, 255, 204, 0.1);
    }
    
    .stButton > button { 
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); 
        color: black; font-weight: bold; border-radius: 12px; height: 50px; width: 100%; border: none;
        box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);
    }

    /* 5. PULSING INDICATOR WITH GLOW */
    .mobile-hint {
        background: #007bff; color: white; padding: 10px; border-radius: 10px;
        text-align: center; font-weight: bold; margin-bottom: 15px;
        box-shadow: 0 0 15px rgba(0, 123, 255, 0.6);
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); box-shadow: 0 0 5px rgba(0, 123, 255, 0.4); }
        50% { opacity: 0.8; transform: scale(0.98); box-shadow: 0 0 20px rgba(0, 123, 255, 0.8); }
        100% { opacity: 1; transform: scale(1); box-shadow: 0 0 5px rgba(0, 123, 255, 0.4); }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING ---
@st.cache_data(ttl=300)
def load_sheet_data(url, sheet_name):
    safe_name = sheet_name.replace(" ", "%20")
    csv_url = url.replace("/edit?usp=sharing", f"/gviz/tq?tqx=out:csv&sheet={safe_name}")
    return pd.read_csv(csv_url)

try:
    SHEET_URL = st.secrets["gsheets_url"]
    df_in_raw = load_sheet_data(SHEET_URL, "INCOMING SEARCH")
    df_out_raw = load_sheet_data(SHEET_URL, "OUTGOING SEARCH")
    user_df = load_sheet_data(SHEET_URL, "USER")
    
    df_in = df_in_raw.iloc[:, :14].fillna("")
    df_out = df_out_raw.iloc[:, :14].fillna("")
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
    st.title("HFDB File Search")
    
    # Logic for Mobile Hint
    # We check if any checkboxes are ticked before showing the hint
    tab_in, tab_out = st.tabs(["📥 INCOMING", "📤 OUTGOING"])
    
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

    with tab_in:
        q_in = st.text_input("Search Incoming Documents", placeholder="🔍 Search...", key="in_search")
        filtered_in = df_in[df_in.astype(str).apply(lambda x: x.str.contains(q_in, case=False)).any(axis=1)] if q_in else df_in
        selection_in = st.dataframe(
            filtered_in, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="multi-row", 
            column_config=config_in, key="in_grid"
        )

    with tab_out:
        q_out = st.text_input("Search Outgoing Documents", placeholder="🔍 Search...", key="out_search")
        filtered_out = df_out[df_out.astype(str).apply(lambda x: x.str.contains(q_out, case=False)).any(axis=1)] if q_out else df_out
        selection_out = st.dataframe(
            filtered_out, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="multi-row", 
            column_config=config_out, key="out_grid"
        )

with col_action:
    # --- DYNAMIC MOBILE PROMPT ---
    # This only shows if the user has selected something but hasn't reached the bottom yet
    sel_in = selection_in.selection.rows
    sel_out = selection_out.selection.rows
    
    if len(sel_in) > 0 or len(sel_out) > 0:
        st.markdown('<div class="mobile-hint">👇 SCROLL DOWN TO FINISH REQUEST</div>', unsafe_allow_html=True)

    st.markdown('<div class="action-panel">', unsafe_allow_html=True)
    st.header("📤 File Request")
    
    names_list = [""] + user_df.iloc[:, 0].dropna().tolist()
    user_name = st.selectbox("Select Your Name in the Dropdown", names_list)
    
    st.divider()
    
    if len(sel_in) > 0 or len(sel_out) > 0:
        total_selected = len(sel_in) + len(sel_out)
        st.write(f"**Selected:** {total_selected}")
        
        selected_dtraks = []
        if sel_in: selected_dtraks.extend(filtered_in.iloc[sel_in, 2].tolist())
        if sel_out: selected_dtraks.extend(filtered_out.iloc[sel_out, 5].tolist())
        
        for d in selected_dtraks:
            st.info(f"📄 {d}")
        
        if st.button("SEND TO MY EMAIL"):
            if not user_name:
                st.error("Select name!")
            else:
                with st.spinner("Processing..."):
                    try:
                        user_email = user_df[user_df.iloc[:, 0] == user_name].iloc[0, 1]
                    except:
                        user_email = None
                    if send_signal(user_name, user_email, selected_dtraks):
                        st.snow()
                        st.success("Done!")
    else:
        st.warning("Kindly select which item(s) to request.")
    st.markdown('</div>', unsafe_allow_html=True)
