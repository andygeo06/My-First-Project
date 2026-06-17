import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="DOH Facility Profiles Magazine",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM MAGAZINE-STYLE CSS ---
st.markdown("""
    <style>
    /* Classic editorial paper color background */
    .stApp {
        background-color: #FDFBF7;
        color: #2F2E2C;
    }
    /* Typography customizations */
    h1, h2, h3 {
        font-family: 'Georgia', 'Times New Roman', serif;
        color: #1A1A19;
    }
    .magazine-header {
        text-align: center;
        border-bottom: 3px double #1A1A19;
        padding-bottom: 15px;
        margin-bottom: 30px;
    }
    .section-banner {
        background-color: #F4EFE6;
        padding: 10px;
        border-left: 5px solid #8B7E66;
        font-weight: bold;
        margin-top: 25px;
        margin-bottom: 15px;
        font-family: 'Georgia', serif;
    }
    /* Simple table card styling */
    .data-card {
        background-color: #FFFFFF;
        padding: 15px;
        border: 1px solid #E6E1DA;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTICATION & DATA FETCHING ---
@st.cache_data(ttl=600)
def load_sheet_data():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Extract service account directly from st.secrets to match your configuration structure
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # Handle newline escaping often caused by TOH environmental conversions
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Access sheet using the URL parameter defined in your secrets file
    sheet_url = st.secrets["https://docs.google.com/spreadsheets/d/1jX5bZX6V3M399a8D6vJjtx2BtNSkl8yfvcKGE_XLgco/edit?usp=sharing"]
    workbook = client.open_by_url(sheet_url)
    sheet = workbook.worksheet("DATA")
    
    return pd.DataFrame(sheet.get_all_records())

# Try loading data safely
try:
    df = load_sheet_data()
except Exception as e:
    st.error("Authentication or connection failed. Please check your st.secrets configurations.")
    st.stop()

total_hospitals = len(df)

# --- MAGAZINE PAGE NAVIGATION STATE ---
if 'page_index' not in st.session_state:
    st.session_state.page_index = 0

# Navigation Functions
def next_page():
    if st.session_state.page_index < total_hospitals - 1:
        st.session_state.page_index += 1

def prev_page():
    if st.session_state.page_index > 0:
        st.session_state.page_index -= 1

# --- HEADER NAVIGATION CONTROLS ---
nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
with nav_col1:
    st.button("◀ Previous Page", on_click=prev_page, disabled=(st.session_state.page_index == 0), key="top_prev")
with nav_col2:
    page_select = st.selectbox(
        "Jump to Page", 
        options=range(total_hospitals), 
        format_func=lambda x: f"Page {x+1}: {df.iloc[x]['Q. 1.2 - Official acronym'] or df.iloc[x]['Q. 1.1 - Official name of the facility']}",
        index=st.session_state.page_index,
        key="page_tracker"
    )
    st.session_state.page_index = page_select
with nav_col3:
    st.button("Next Page ▶", on_click=next_page, disabled=(st.session_state.page_index == total_hospitals - 1), key="top_next")

# Extract the working row based on active selection
row = df.iloc[st.session_state.page_index]

# --- RENDER MAGAZINE COVER/PROFILE HEADER ---
st.markdown(f"""
    <div class="magazine-header">
        <h1>{row['Q. 1.1 - Official name of the facility']}</h1>
        <p style="font-style: italic; font-size: 1.2rem; color: #555;">{row['Q. 1.2 - Official acronym']} — Region {row['Q. 1.3 - Region (geographic)']}</p>
    </div>
""", unsafe_allow_html=True)

# Main layout split for the visual spread
col_left_gallery, col_right_profile = st.columns([2, 3])

with col_left_gallery:
    # Render main structural visuals cleanly
    if row['Q. 6.3 - Official seal']:
        st.image(row['Q. 6.3 - Official seal'], caption="Official Seal", width=160)
    
    if row['Q. 6.1 - Exterior facade of the main building (at least two)']:
        # Splits comma-separated image URLs if multiple exist
        facades = str(row['Q. 6.1 - Exterior facade of the main building (at least two)']).split(',')
        st.image(facades[0].strip(), caption="Exterior Facade View", use_container_width=True)
        
    if row['Q. 6.2 - Interior lobby of the main building']:
        st.image(row['Q. 6.2 - Interior lobby of the main building'], caption="Main Lobby Interior", use_container_width=True)

with col_right_profile:
    st.markdown('<div class="section-banner">SECTION 1: LEADERSHIP & IDENTITY</div>', unsafe_allow_html=True)
    
    lead_col1, lead_col2 = st.columns([1, 2])
    with lead_col1:
        if row['Q. 6.4 - Chief of the facility']:
            st.image(row['Q. 6.4 - Chief of the facility'], use_container_width=True)
    with lead_col2:
        st.markdown(f"### {row['Q. 2.1 - Name of the facility chief']}")
        st.caption(f"**{row['Q. 2.2 - Position title of the facility chief']}**")
        st.write(f"**Founding Identity:** {row['Q. 2.7 - Founding name and year']}")
        st.write(f"**Motto/Slogan:** *{row['Q. 2.5 - Institution's motto or slogan']}*")
        
    st.markdown(f"**Institution Vision:**\n> {row['Q. 2.3 - Institution's vision']}")
    st.markdown(f"**Institution Mission:**\n> {row['Q. 2.4 - Institution's mission']}")
    st.write(f"**Latest Hospital Mandate:** {row['Q. 2.6 - Latest hospital mandate']}")
    st.write(f"**Workforce Demographics:** {row['Q. 2.8 - Number (numerator/denominator) and percent of females employed as of end of 2024']}")

# --- SECTION 2: PHYSICAL & OPERATIONAL CLASSIFICATION ---
st.markdown('<div class="section-banner">SECTION 2: FACILITY CLASSIFICATION & INFRASTRUCTURE</div>', unsafe_allow_html=True)
infra1, infra2, infra3 = st.columns(3)
with infra1:
    st.markdown('<div class="data-card">', unsafe_allow_html=True)
    st.markdown("**Basic Footprint**")
    st.write(f"**Land Area:** {row['Q. 3.1 - Land area (in sqm)']} sqm")
    st.write(f"**Gross Floor Area:** {row['Q. 3.2 - Total gross floor area (in sqm)']} sqm")
    st.write(f"**Main Address:** {row['Q. 1.4 - Address of the main location']}")
    st.write(f"**Coordinates:** {row['Q. 1.5 - GPS coordinates']}")
    st.markdown('</div>', unsafe_allow_html=True)

with infra2:
    st.markdown('<div class="data-card">', unsafe_allow_html=True)
    st.markdown("**Regulatory Status**")
    st.write(f"**Classification:** {row['Q. 3.3 - Hospital classification (per LTO 2024)']}")
    st.write(f"**Capability Level:** {row['Q. 3.4 - Hospital capability level (per LTO 2024)']}")
    st.write(f"**Malasakit Center Inception:** {row['Q. 3.8 - Year the Malasakit Center opened in the hospital']}")
    st.markdown('</div>', unsafe_allow_html=True)

with infra3:
    st.markdown('<div class="data-card">', unsafe_allow_html=True)
    st.markdown("**Bed Capacities**")
    st.write(f"**Authorized (by Law):** {row['Q. 3.5 - Authorized bed capacity (by law)']}")
    st.write(f"**Authorized (by License):** {row['Q. 3.6 - Authorized bed capacity (by license)']}")
    st.write(f"**Implementing Capacity (2024):** {row['Q. 3.7 - Implementing bed capacity (as of 2024)']}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- SECTION 3: APEX CLINICAL NETWORKS & SPECIALTY DESIGNATIONS ---
st.markdown('<div class="section-banner">SECTION 3: CLINICAL CAPABILITIES & SPECIALTY DESIGNATIONS</div>', unsafe_allow_html=True)
net_col1, net_col2 = st.columns(2)
with net_col1:
    st.write(f"**Eligible Apex/End-Referral Facility:** {row['Q. 3.9 (F) - Is the hospital an eligible apex or end-referral facility as of 2024?']}")
    st.write(f"**Linked Health Care Provider Networks (HCPN):** {row['Q. 3.9.1 - List all health care provider networks (HCPN) linked to you as their apex/end-referral facility as of end of 2024']}")
    st.write(f"**MOA / Legally Bound Networks:** {row['Q. 3.9.2 - List HCPNs that are linked to you, which have Memoranda of Agreements or other legal instruments as of end of 2024']}")
with net_col2:
    st.write(f"**Outside Main Location Operational Facilities:** {row['Q. 3.11 - Additional facilities owned and operated by the hospital outside of its main location as of 2024']}")
    st.write(f"**Outside Main Location Contractual Facilities:** {row['Q. 3.12 - Additional facilities operated but not owned by the hospital outside its main location as of 2024']}")
    st.write(f"**BUCAS Center Name:** {row['Q 3.13.1 - Name of BUCAS Center']} ({row['Q 3.13.2 - Address of the BUCAS Center (in-house/stand-alone)']})")

st.markdown("##### DOH Designated Specialty Centers")
specialty_fields = [
    "BRAIN AND SPINE CARE", "BURN CARE", "CANCER CARE", "CARDIOVASCULAR CARE", 
    "DERMATOLOGY CARE", "EYE CARE", "GERIATRIC CARE", "INFECTIOUS DISEASE AND TROPICAL MEDICINE", 
    "LUNG CARE", "MENTAL HEALTH", "NEONATAL CARE", "ORTHOPEDIC CARE", 
    "PHYSICAL REHABILITATION MEDICINE", "RENAL CARE AND KIDNEY TRANSPLANT", "TOXICOLOGY", "TRAUMA CARE"
]

# Create a clean display grid for the active specialty items
spec_cols = st.columns(4)
for i, spec in enumerate(specialty_fields):
    col_target = spec_cols[i % 4]
    sheet_header_key = f"Q. 3.10.{i+1} - Are you designated with a specialty center on {spec}?"
    if sheet_header_key in row and str(row[sheet_header_key]).strip().lower() == "yes":
        col_target.markdown(f"🏛️ **{spec.title()}**")

# --- SECTION 4: HISTORICAL METRICS & PERFORMANCE DATA ---
st.markdown('<div class="section-banner">SECTION 4: OPERATIONAL METRICS & ANNUAL TRENDS</div>', unsafe_allow_html=True)

metrics_data = {
    "Metric Category": [
        "Bed Occupancy Rate", 
        "Inpatient Bed Days", 
        "Average Daily Patients Served", 
        "Average Daily Discharges", 
        "Outpatient Visits", 
        "Emergency Room Visits"
    ],
    "2022": [row["Q. 4.1.1 - Bed occupancy rate (2022)"], row["Q. 4.2.1 - Inpatient bed days (2022)"], row["Q. 4.3.1 - Average daily patients served (2022)"], row["Q. 4.4.1 - Average daily discharges (2022)"], row["Q. 4.5.1 - Outpatient visits (2022)"], row["Q. 4.6.1 - Emergency room visits (2022)"]],
    "2023": [row["Q. 4.1.2 - Bed occupancy rate (2023)"], row["Q. 4.2.2 - Inpatient bed days (2023)"], row["Q. 4.3.2 - Average daily patients served (2023)"], row["Q. 4.4.2 - Average daily discharges (2023)"], row["Q. 4.5.2 - Outpatient visits (2023)"], row["Q. 4.6.2 - Emergency room visits (2023)"]],
    "2024": [row["Q. 4.1.3 - Bed occupancy rate (2024)"], row["Q. 4.2.3 - Inpatient bed days (2024)"], row["Q. 4.3.3 - Average daily patients served (2024)"], row["Q. 4.4.3 - Average daily discharges (2024)"], row["Q. 4.5.3 - Outpatient visits (2024)"], row["Q. 4.6.3 - Emergency room visits (2024)"]]
}
st.table(pd.DataFrame(metrics_data).set_index("Metric Category"))

stat1, stat2, stat3 = st.columns(3)
with stat1:
    st.write(f"**Malasakit Financial Beneficiaries (2024):** {row['Q. 4.7 - Patients who received financial assistance through the Malasakit Center (2024; \"N/A\" if not applicable)']}")
with stat2:
    st.write(f"**Adult Female Patients (≥18, 2024):** {row['Q. 4.8 - Number (numerator/denominator) and percent of female patients aged 18 and above served (2024)']}")
with stat3:
    st.write(f"**Juvenile Female Patients (≤17, 2024):** {row['Q. 4.9 - Number (numerator/denominator) and percent of female patients aged 17 and below served (2024)']}")

# --- SECTION 5: CERTIFICATIONS & RATINGS ---
st.markdown('<div class="section-banner">SECTION 5: QUALITY COMPLIANCE & ACCREDITATIONS</div>', unsafe_allow_html=True)
rate1, rate2, rate3 = st.columns(3)
rate1.metric("Hospital Scorecard Rating (2024)", str(row["Q 5.1 - Hospital scorecard rating (2024)"]))
rate2.metric("IHOMP Assessment Rating (2019)", str(row["Q 5.2 - IHOMP assessment rating (2019)"]))
rate3.metric("Green Star Quality Rating (2024)", str(row["Q 5.3 - Green star rating (2024)"]))

st.write(f"**ISO 9001 Certification Framework:** {row['Q. 5.4 - ISO 9001 certification body and latest year of certification (\"N/A\" if not applicable)']}")
st.write(f"**PGS Milestone Attainment:** {row['Q. 5.5 - PGS status attained and/or award and year (\"N/A\" if not applicable)']}")

# --- SECTION 6: INSTITUTIONAL DIRECTORY ---
st.markdown('<div class="section-banner">SECTION 6: MEDIA & INTER-AGENCY CONTACTS</div>', unsafe_allow_html=True)
media1, media2 = st.columns(2)
with media1:
    st.markdown("**Public Touchpoints**")
    st.write(f"📞 **Telephone:** {row['Q. 1.6 - Telephone number/s (\"N/A\" if not applicable)']}")
    st.write(f"📱 **Mobile:** {row['Q. 1.7 - Mobile phone number/s (\"N/A\" if not applicable)']}")
    st.write(f"📧 **Official Email:** {row['Q. 1.8 - Official email address/es (\"N/A\" if not applicable)']}")
    st.write(f"🌐 **Web URL:** {row['Q. 1.9 - Official web address (\"N/A\" if not applicable)']}")
    st.write(f"💬 **Social Media Channel:** {row['Q. 1.10 - Official social media account/s (\"N/A\" if not applicable)']}")
with media2:
    st.markdown("**Administrative Contact Person**")
    st.write(f"👤 **Name:** {row['Q. 7.1 - Name of contact person']}")
    st.write(f"💼 **Designated Role:** {row['Q 7.2 - Position title of the contact person']}")
    st.write(f"🏢 **Assignment Unit:** {row['Q. 7.3 - Department/Division/Section/Unit']}")
    st.write(f"📱 **Secure Phone Line:** {row['Q. 7.4 - Personal mobile number']}")
    st.write(f"📧 **Direct Work Email:** {row['Q. 7.5 - Personal email address']}")

# --- BOTTOM FOOTER NAVIGATION ---
st.markdown("---")
btm_col1, btm_col2, btm_col3 = st.columns([1, 2, 1])
with btm_col1:
    st.button("◀ Previous Facility", on_click=prev_page, disabled=(st.session_state.page_index == 0), key="btm_prev")
with btm_col2:
    st.markdown(f"<p style='text-align: center; color: gray;'>Profile {st.session_state.page_index + 1} of {total_hospitals}</p>", unsafe_allow_html=True)
with btm_col3:
    st.button("Next Facility ▶", on_click=next_page, disabled=(st.session_state.page_index == total_hospitals - 1), key="btm_next")
