import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="HFDB Document Searching Tool", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e0e0e0; }
    .stTextInput > div > div > input { background-color: #1a1f26 !important; color: #00ffcc !important; border-radius: 10px; border: 2px solid #30363d; }
    .action-panel { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid #30363d; position: sticky; top: 1rem; }
    .stButton > button { background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: black; font-weight: bold; border-radius: 12px; height: 45px; width: 100%; border: none; }
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
    
    # We take columns A-N (0-13) for both
    df_in = df_in_raw.iloc[:, :14]
    df_out = df_out_raw.iloc[:, :14]
    st.success("✅ Search Portal Online")
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 3. SIGNAL FUNCTION (With Reply-To Logic) ---
def send_signal(user_name, user_email, dtrak_list):
    bot_email = st.secrets["BOT_EMAIL"]
    bot_pw = st.secrets["BOT_PASSWORD"]
    for dtrak in dtrak_list:
        msg = MIMEText(f"SENTINEL REQUEST: {dtrak} for {user_name}")
        msg['Subject'] = str(dtrak)
        msg['From'] = f"Sentinel Cloud <{bot_email}>"
        msg['To'] = bot_email
        
        # Set Reply-To so the office can reply directly to the staff member
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
    st.title("HFDB Document Searching Tool")
    tab_in, tab_out = st.tabs(["📥 INCOMING DOCUMENTS", "📤 OUTGOING DOCUMENTS"])
    
    # --- MICRO-MANAGEMENT: INCOMING CONFIG ---
    config_in = {
        df_in.columns[0]: st.column_config.TextColumn("Received", width="small"),
        df_in.columns[1]: st.column_config.TextColumn("Time", width=40),
        df_in.columns[2]: st.column_config.TextColumn("DTRAK No.", width=110),
        df_in.columns[3]: st.column_config.TextColumn("Control No.", width=110),
        df_in.columns[4]: st.column_config.TextColumn("Subject", width="large"),
        df_in.columns[5]: st.column_config.TextColumn("Doc Type", width="small"),
        df_in.columns[6]: st.column_config.TextColumn("Origin", width="small"),
        df_in.columns[7]: st.column_config.TextColumn("Acted", width="small"),
        df_in.columns[8]: st.column_config.TextColumn("Time", width=40),
        df_in.columns[9]: st.column_config.TextColumn("Sent", width="small"),
        df_in.columns[10]: st.column_config.TextColumn("Division", width="small"),
        df_in.columns[11]: st.column_config.TextColumn("Staff", width="small"),
        df_in.columns[12]: st.column_config.TextColumn("Tag", width="small"),
        df_in.columns[13]: st.column_config.TextColumn("Action Taken", width="large"),
    }

    # --- MICRO-MANAGEMENT: OUTGOING CONFIG ---
    config_out = {
        df_out.columns[0]: st.column_config.TextColumn("Date", width="small"),
        df_out.columns[1]: st.column_config.TextColumn("Time", width=40),
        df_out.columns[2]: st.column_config.TextColumn("Control No.", width=110),
        df_out.columns[3]: st.column_config.TextColumn("Subject", width="large"),
        df_out.columns[4]: st.column_config.TextColumn("Former DTRAK", width=110),
        df_out.columns[5]: st.column_config.TextColumn("Current DTRAK", width=110),
        df_out.columns[6]: st.column_config.TextColumn("Doc Type", width="small"),
        df_out.columns[7]: st.column_config.TextColumn("Staff", width="small"),
        df_out.columns[8]: st.column_config.TextColumn("Action Taken", width="large"),
        df_out.columns[9]: st.column_config.TextColumn("Date Acted", width="small"),
        df_out.columns[10]: st.column_config.TextColumn("Time", width=40),
        df_out.columns[11]: st.column_config.TextColumn("Status", width="small"),
        df_out.columns[12]: st.column_config.TextColumn("Admin Date", width="small"),
        df_out.columns[13]: st.column_config.TextColumn("Admin Time", width=40),
    }

    with tab_in:
        q_in = st.text_input("Search Incoming", placeholder="🔍 Search...", key="in_search")
        filtered_in = df_in[df_in.astype(str).apply(lambda x: x.str.contains(q_in, case=False)).any(axis=1)] if q_in else df_in
        selection_in = st.dataframe(
            filtered_in, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="multi-row", column_config=config_in, key="in_grid"
        )

    with tab_out:
        q_out = st.text_input("Search Outgoing", placeholder="🔍 Search...", key="out_search")
        filtered_out = df_out[df_out.astype(str).apply(lambda x: x.str.contains(q_out, case=False)).any(axis=1)] if q_out else df_out
        selection_out = st.dataframe(
            filtered_out, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="multi-row", column_config=config_out, key="out_grid"
        )

with col_action:
    st.markdown('<div class="action-panel">', unsafe_allow_html=True)
    st.header("📤 Request File Copy")
    
    names_list = [""] + user_df.iloc[:, 0].dropna().tolist()
    user_name = st.selectbox("1. Select Your Name", names_list)
    
    st.divider()
    
    sel_in = selection_in.selection.rows
    sel_out = selection_out.selection.rows
    
    if len(sel_in) > 0 or len(sel_out) > 0:
        total_selected = len(sel_in) + len(sel_out)
        st.write(f"**Selected:** {total_selected}")
        
        selected_dtraks = []
        # Grab DTRAK from Index 2 for Incoming, and Index 5 (Current DTRAK) for Outgoing
        if sel_in: selected_dtraks.extend(filtered_in.iloc[sel_in, 2].tolist())
        if sel_out: selected_dtraks.extend(filtered_out.iloc[sel_out, 5].tolist())
        
        for d in selected_dtraks:
            st.info(f"📄 {d}")
        
        if st.button("SEND TO MY EMAIL"):
            if not user_name:
                st.error("Select name!")
            else:
                with st.spinner("Pinging..."):
                    # Lookup email: Name is Col 0, Email is Col 1 in USER tab
                    try:
                        user_email = user_df[user_df.iloc[:, 0] == user_name].iloc[0, 1]
                    except:
                        user_email = None
                        
                    if send_signal(user_name, user_email, selected_dtraks):
                        st.snow()
                        st.success("Done!")
    else:
        st.warning("Select items to request.")
    st.markdown('</div>', unsafe_allow_html=True)
