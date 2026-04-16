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
    df_raw = load_sheet_data(SHEET_URL, "INCOMING SEARCH")
    user_df = load_sheet_data(SHEET_URL, "USER")
    
    # --- 3. COLUMN FILTERING (A to N only) ---
    # We take the first 14 columns (A=0 to N=13)
    df = df_raw.iloc[:, :14]
    
    st.success("✅ Search Portal Online")
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 4. SIGNAL FUNCTION ---
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

# --- 5. UI LAYOUT ---
col_main, col_action = st.columns([3.5, 1], gap="small")

with col_main:
    st.title("HFDB Document Searching Tool")
    query = st.text_input("", placeholder="🔍 Search by Subject, DTRAK, or Office...")

    if query:
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
        filtered_df = df[mask]
    else:
        filtered_df = df

    # --- 6. DATA DISPLAY CONFIGURATION ---
    # Here we map your specific Column A-N instructions
    selection = st.dataframe(
        filtered_df, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            df.columns[0]: st.column_config.TextColumn("Received", width="small"),           # A
            df.columns[1]: st.column_config.TextColumn("Time", width=40),          # B
            df.columns[2]: st.column_config.TextColumn("DTRAK No.", width=120),        # C
            df.columns[3]: st.column_config.TextColumn("Control No.", width=120),  # D
            df.columns[4]: st.column_config.TextColumn("Subject", width="large"),        # E (Readable)
            df.columns[5]: st.column_config.TextColumn("Doc Type", width="small"),           # F (Truncated)
            df.columns[6]: st.column_config.TextColumn("Origin", width="small"),         # G
            df.columns[7]: st.column_config.TextColumn("Acted", width="small"),       # H
            df.columns[8]: st.column_config.TextColumn("Time", width=40),           # I
            df.columns[9]: st.column_config.TextColumn("Sent", width="small"),           # J
            df.columns[10]: st.column_config.TextColumn("Division", width="small"),      # K
            df.columns[11]: st.column_config.TextColumn("Staff", width="small"),         # L
            df.columns[12]: st.column_config.TextColumn("Tag", width="small"),           # M
            df.columns[13]: st.column_config.TextColumn("Action Taken", width="large"),  # N (Important)
        }
    )

with col_action:
    st.markdown('<div class="action-panel">', unsafe_allow_html=True)
    st.header("📤 Request File Copy")
    
    names_list = [""] + user_df.iloc[:, 0].dropna().tolist()
    user_name = st.selectbox("1. Select Your Name in the Dropdown Below", names_list)
    
    st.divider()
    
    selected_indices = selection.selection.rows
    if len(selected_indices) > 0:
        st.write(f"**Selected:** {len(selected_indices)}")
        
        # Pulling DTRAK (Column C / Index 2)
        selected_dtraks = filtered_df.iloc[selected_indices, 2].tolist()
        for d in selected_dtraks:
            st.info(f"📄 {d}")
        
        if st.button("SEND TO MY EMAIL"):
            if not user_name:
                st.error("Select name!")
            else:
                with st.spinner("Pinging..."):
                    if send_signal(user_name, selected_dtraks):
                        st.snow()
                        st.success("Done!")
    else:
        st.warning("Select items using the checkbox on the far left.")
    st.markdown('</div>', unsafe_allow_html=True)
