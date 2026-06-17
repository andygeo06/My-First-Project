import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- PAGE SETUP ---
st.set_page_config(page_title="DOH Hospital Directory", layout="wide")

# --- DATA LOADING ---
@st.cache_data(ttl=3600)
def get_data():
    # Setup connection
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    # Ensure your credentials.json is in the same folder
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("2026 Receiving/Releasing").worksheet("DATA")
    return pd.DataFrame(sheet.get_all_records())

df = get_data()

# --- SIDEBAR ---
st.sidebar.title("Hospital Navigator")
hospital_list = df['Q. 1.1 - Official name of the facility'].unique()
selected_name = st.sidebar.selectbox("Select a Hospital", hospital_list)

# Filter data
row = df[df['Q. 1.1 - Official name of the facility'] == selected_name].iloc[0]

# --- MAIN UI ---
st.title(f"{row['Q. 1.1 - Official name of the facility']} ({row['Q. 1.2 - Official acronym']})")

# Header Section (Visuals)
col_l, col_r = st.columns([1, 3])
with col_l:
    st.image(row['Q. 6.3 - Official seal'], use_column_width=True)
with col_r:
    st.subheader(f"Chief: {row['Q. 2.1 - Name of the facility chief']}")
    st.write(f"**Position:** {row['Q. 2.2 - Position title of the facility chief']}")
    st.write(f"**Region:** {row['Q. 1.3 - Region (geographic)']}")

# Tabs for Organization
t1, t2, t3, t4 = st.tabs(["General Information", "Institutional Details", "Specialty Centers", "Performance Metrics"])

with t1:
    st.write(f"**Address:** {row['Q. 1.4 - Address of the main location']}")
    st.write(f"**Contact:** {row['Q. 1.6 - Telephone number/s']} | {row['Q. 1.7 - Mobile phone number/s']}")
    st.write(f"**Email:** {row['Q. 1.8 - Official email address/es']}")
    st.write(f"**Website:** {row['Q. 1.9 - Official web address']}")

with t2:
    with st.expander("Vision & Mission"):
        st.write(f"**Vision:** {row['Q. 2.3 - Institution's vision']}")
        st.write(f"**Mission:** {row['Q. 2.4 - Institution's mission']}")
    with st.expander("Infrastructure Data"):
        st.write(f"**Land Area:** {row['Q. 3.1 - Land area (in sqm)']} sqm")
        st.write(f"**Classification:** {row['Q. 3.3 - Hospital classification (per LTO 2024)']}")

with t3:
    st.write("### Designated Specialty Centers")
    specialty_cols = [c for c in df.columns if "Q. 3.10" in c]
    for col in specialty_cols:
        if row[col] == "Yes":
            st.success(f"✅ {col.split(' - ')[1]}")

with t4:
    st.metric("Bed Occupancy Rate (2024)", f"{row['Q. 4.1.3']}%")
    st.write(f"**Avg Daily Patients:** {row['Q. 4.3.3']}")
    st.write(f"**ER Visits (2024):** {row['Q. 4.6.3']}")

# --- FOOTER ---
st.divider()
st.caption(f"Last updated: 2026 | Managed by HFDB")
