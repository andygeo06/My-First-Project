import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Sentinel 4.4 - Cloud Portal", layout="wide")

# Custom CSS for Dark Mode and Layout
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e0e0e0; }
    .stTextInput > div > div > input { background-color: #1a1f26 !important; color: #00ffcc !important; border-radius: 10px; border: 2px solid #30363d; }
    .action-panel { background: rgba(255, 255, 255, 0.05); padding: 25px; border-radius: 15px; border: 1px solid #30363d; position: sticky; top: 2rem; }
    .stButton > button { background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: black; font-weight: bold; border-radius: 12px; height: 50px; width: 100%; border: none; }
    .stButton > button:hover { box-shadow: 0 0 15px #4facfe; transform: translateY(-2px); transition: 0.3s; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA CONNECTION (Direct Pandas Method) ---
@st.cache_data(ttl=600)
def load_data(url):
    # This trick converts a Google Sheet URL into a direct CSV export
    # gid=0 usually refers to the first tab (INCOMING SEARCH)
    csv_url = url.replace("/edit?usp=sharing", "/export?format=csv&gid=0")
    if "/edit#gid=" in url:
        csv_url = url.replace("/edit#gid=", "/export?format=csv&gid=")
    return pd.read_csv(csv_url)

try:
    SHEET_URL = st.secrets["gsheets_url"]
    df = load_data(SHEET_URL)
except Exception as e:
    st.error(f"⚠️ Connection Failed: {e}")
    st.info("Check your Streamlit Secrets for 'gsheets_url' and ensure the Sheet is Public.")
    st.stop()

# --- 3. SIGNAL FUNCTION (To your Local Server) ---
def send_signal(user_name, dtrak_list):
    bot_email = st.secrets["BOT_EMAIL"]
    bot_pw = st.secrets["BOT_PASSWORD"]
    
    # Building the signal email
    for dtrak in dtrak_list:
        msg = MIMEText(f"SENTINEL CLOUD REQUEST: {dtrak} for {user_name}")
        msg['Subject'] = dtrak
        msg['From'] = f"Sentinel Cloud <{bot_email}>"
        msg['To'] = bot_email
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(bot_email, bot_pw)
                server.send_message(msg)
        except Exception as e:
            st.error(f"Signal failed: {e}")
            return False
    return True

# --- 4. THE UI LAYOUT (Main: 3, Action: 1) ---
col_main, col_action = st.columns([3, 1], gap="large")

with col_main:
    st.title("🛡️ Sentinel Cloud Search")
    st.caption("20th Congress | HFDB Document Tracking")
    
    query = st.text_input("", placeholder="🔍 Search by Subject, DTRAK, or Office Control...")

    # Instant Filter
    if query:
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
        filtered_df = df[mask]
    else:
        filtered_df = df

    # Data Display
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
    
    # Identify User
    user_name = st.selectbox("1. Select Your Name", ["", "User A", "User B", "User C"])
    
    st.divider()
    
    # Action Logic
    selected_indices = selection.selection.rows
    if len(selected_indices) > 0:
        st.write(f"**Selected:** {len(selected_indices)} file(s)")
        selected_dtraks = filtered_df.iloc[selected_indices]['DTRAK NO.'].tolist()
        
        for d in selected_dtraks:
            st.info(f"📄 {d}")
        
        if st.button("SEND TO MY EMAIL"):
            if not user_name:
                st.error("Select name first!")
            else:
                with st.spinner("Pinging Office Server..."):
                    if send_signal(user_name, selected_dtraks):
                        st.balloons()
                        st.success("Signal Sent! Your local server is now processing.")
    else:
        st.warning("Click rows on the left to select.")
    
    st.markdown('</div>', unsafe_allow_html=True)
