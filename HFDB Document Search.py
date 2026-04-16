import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="HFDB Document Searching Tool", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e0e0e0; }
    .stTextInput > div > div > input { background-color: #1a1f26 !important; color: #00ffcc !important; border-radius: 10px; border: 2px solid #30363d; }
    .action-panel { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid #30363d; position: sticky; top: 1rem; }
    .stButton > button { background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: black; font-weight: bold; border-radius: 12px; height: 45px; width: 100%; border: none; }
    /* This makes the dataframe rows wrap text naturally */
    .stDataFrame div[data-testid="stTable"] div { white-space: normal !important; }
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
    st.success("✅ Search Portal Online")
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
    st.title("HFDB Document Searching Tool")
    tab_in, tab_out = st.tabs(["📥 INCOMING DOCUMENTS", "📤 OUTGOING DOCUMENTS"])
    
    # --- CONFIG WITH TEXT WRAPPING ---
    # We use st.column_config.TextColumn() with no width restriction for wrapping
    def get_config(df_ref):
        return {
            df_ref.columns[0]: st.column_config.TextColumn("Date", width="small"),
            df_ref.columns[1]: st.column_config.TextColumn("Time", width=45),
            df_ref.columns[2]: st.column_config.TextColumn("DTRAK No.", width=110),
            df_ref.columns[3]: st.column_config.TextColumn("Control No.", width=110),
            # 'large' + missing width constraint allows the text to expand
            df_ref.columns[4]: st.column_config.TextColumn("Subject", width="large"),
            df_ref.columns[13] if len(df_ref.columns) > 13 else "Action": st.column_config.TextColumn("Action Taken", width="large"),
        }

    with tab_in:
        q_in = st.text_input("Search Incoming", placeholder="🔍 Type keywords...", key="in_search")
        filtered_in = df_in[df_in.astype(str).apply(lambda x: x.str.contains(q_in, case=False)).any(axis=1)] if q_in else df_in
        
        if q_in:
            st.caption(f"Found {len(filtered_in)} matches for '{q_in}'")
            
        selection_in = st.dataframe(
            filtered_in, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="multi-row", column_config=get_config(df_in), key="in_grid"
        )

    with tab_out:
        q_out = st.text_input("Search Outgoing", placeholder="🔍 Type keywords...", key="out_search")
        filtered_out = df_out[df_out.astype(str).apply(lambda x: x.str.contains(q_out, case=False)).any(axis=1)] if q_out else df_out
        
        if q_out:
            st.caption(f"Found {len(filtered_out)} matches for '{q_out}'")

        selection_out = st.dataframe(
            filtered_out, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="multi-row", column_config=get_config(df_out), key="out_grid"
        )

with col_action:
    st.markdown('<div class="action-panel">', unsafe_allow_html=True)
    st.header("📤 Request File")
    
    names_list = [""] + user_df.iloc[:, 0].dropna().tolist()
    user_name = st.selectbox("1. Select Your Name", names_list)
    
    st.divider()
    
    sel_in = selection_in.selection.rows
    sel_out = selection_out.selection.rows
    
    if len(sel_in) > 0 or len(sel_out) > 0:
        total_selected = len(sel_in) + len(sel_out)
        st.write(f"**Selected:** {total_selected}")
        
        selected_dtraks = []
        if sel_in: selected_dtraks.extend(filtered_in.iloc[sel_in, 2].tolist())
        if sel_out: selected_dtraks.extend(filtered_out.iloc[sel_out, 5].tolist())
        
        for d in selected_dtraks:
            st.info(f"📄 {d}")
        
        if st.button("SEND REQUEST"):
            if not user_name:
                st.error("Select name!")
            else:
                with st.spinner("Pinging..."):
                    try:
                        user_email = user_df[user_df.iloc[:, 0] == user_name].iloc[0, 1]
                    except:
                        user_email = None
                        
                    if send_signal(user_name, user_email, selected_dtraks):
                        st.snow()
                        st.success("Sent!")
    else:
        st.warning("Select rows to continue.")
    st.markdown('</div>', unsafe_allow_html=True)
