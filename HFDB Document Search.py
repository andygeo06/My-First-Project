import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Sentinel 4.4 - Cloud Portal", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e0e0e0; }
    .stTextInput > div > div > input { background-color: #1a1f26 !important; color: #00ffcc !important; border-radius: 10px; border: 2px solid #30363d; }
    .action-panel { background: rgba(255, 255, 255, 0.05); padding: 25px; border-radius: 15px; border: 1px solid #30363d; position: sticky; top: 2rem; }
    .stButton > button { background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: black; font-weight: bold; border-radius: 12px; height: 50px; width: 100%; border: none; }
    .stButton > button:hover { box-shadow: 0 0 15px #4facfe; transform: translateY(-2px); }
    </style>
""", unsafe_allow_html=True)

# --- 2. THE SMART DATA LOADER (Targeting your specific tabs) ---
@st.cache_data(ttl=300)
def load_sheet_data(url, sheet_name):
    # Encodes spaces in sheet names for the URL
    safe_name = sheet_name.replace(" ", "%20")
    csv_url = url.replace("/edit?usp=sharing", f"/gviz/tq?tqx=out:csv&sheet={safe_name}")
    return pd.read_csv(csv_url)

try:
    SHEET_URL = st.secrets["gsheets_url"]
    # Loading INCOMING SEARCH for the main grid and USER for the names
    df = load_sheet_data(SHEET_URL, "INCOMING SEARCH")
    user_df = load_sheet_data(SHEET_URL, "USER")
    st.success("✅ Sentinel System Online")
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.info("Ensure tab names are exactly 'INCOMING SEARCH' and 'USER'")
    st.stop()

# --- 3. SIGNAL FUNCTION ---
def send_signal(user_name, dtrak_list):
    bot_email = st.secrets["BOT_EMAIL"]
    bot_pw = st.secrets["BOT_PASSWORD"]
    for dtrak in dtrak_list:
        msg = MIMEText(f"SENTINEL REQUEST: {dtrak} for {user_name}")
        msg['Subject'] = str(dtrak)
        msg['From'] = bot_email
        msg['To'] = bot_email
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(bot_email, bot_pw)
                server.send_message(msg)
        except: return False
    return True

# --- 4. THE LAYOUT ---
col_main, col_action = st.columns([3, 1], gap="large")

with col_main:
    st.title("🛡️ Sentinel Search")
    st.caption("20th Congress | HFDB Document Tracking")
    
    # Toggle between Incoming and Outgoing (Optional Bonus!)
    mode = st.radio("Select View", ["Incoming", "Outgoing"], horizontal=True)
    
    if mode == "Outgoing":
        # Load Outgoing if the user switches
        df = load_sheet_data(SHEET_URL, "OUTGOING SEARCH")

    query = st.text_input("", placeholder=f"🔍 Search {mode} by Subject, DTRAK, or Office...")

    if query:
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
        filtered_df = df[mask]
    else:
        filtered_df = df

    selection = st.dataframe(
        filtered_df, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row"
    )

with col_action:
    st.markdown('<div class="action-panel">', unsafe_allow_html=True)
    st.header("📤 Request")
    
    # Pull names from the 'USER' tab (Assuming names are in the first column)
    names_list = [""] + user_df.iloc[:, 0].dropna().tolist()
    user_name = st.selectbox("1. Select Your Name", names_list)
    
    st.divider()
    
    selected_indices = selection.selection.rows
    if len(selected_indices) > 0:
        st.write(f"**Selected:** {len(selected_indices)}")
        
        # We search for a column that looks like DTRAK NO. to be safe
        dtrak_col = [col for col in filtered_df.columns if 'DTRAK' in col.upper()]
        if dtrak_col:
            selected_dtraks = filtered_df.iloc[selected_indices][dtrak_col[0]].tolist()
            for d in selected_dtraks:
                st.info(f"📄 {d}")
        
            if st.button("SEND TO MY EMAIL"):
                if not user_name:
                    st.error("Select name!")
                else:
                    with st.spinner("Pinging Server..."):
                        if send_signal(user_name, selected_dtraks):
                            st.balloons()
                            st.success("Request processed!")
        else:
            st.error("DTRAK column not found in this sheet.")
    else:
        st.warning("Select rows on the left.")
    st.markdown('</div>', unsafe_allow_html=True)
