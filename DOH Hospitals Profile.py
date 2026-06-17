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

# --- EDITORIAL SYSTEM DESIGN (CSS) ---
st.markdown("""
    <style>
    /* Premium editorial paper texture style background */
    .stApp {
        background-color: #FAF8F5;
        color: #2B2A28;
    }
    h1, h2, h3, h4 {
        font-family: 'Georgia', 'Times New Roman', serif;
        color: #1C1B1A;
        font-weight: 700;
    }
    .magazine-header {
        text-align: center;
        border-bottom: 4px double #1C1B1A;
        padding-bottom: 20px;
        margin-bottom: 35px;
    }
    .magazine-header h1 {
        font-size: 2.8rem;
        margin-bottom: 5px;
    }
    .section-banner {
        background-color: #F1EAE0;
        padding: 12px 18px;
        border-left: 6px solid #7D6E57;
        font-weight: bold;
        font-size: 1.1rem;
        margin-top: 35px;
        margin-bottom: 20px;
        font-family: 'Georgia', serif;
        letter-spacing: 1px;
    }
    .data-card {
        background-color: #FFFFFF;
        padding: 20px;
        border: 1px solid #E2DCD2;
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 15px;
        height: 100%;
    }
    .block-quote-editorial {
        border-left: 3px italic #7D6E57;
        padding-left: 15px;
        font-style: italic;
        color: #4A4946;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTICATION & SECURITY CONTROL ---
@st.cache_data(ttl=600)
def load_sheet_data():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Safely parse service account block dictionary from st.secrets TOML
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Connect using the public/private sheet URL parameter matching your secrets file
    sheet_url = st.secrets["GSHEETS_URL"]
    workbook = client.open_by_url(sheet_url)
    sheet = workbook.worksheet("DATA")
    
    return pd.DataFrame(sheet.get_all_records())

try:
    df = load_sheet_data()
except Exception as e:
    st.error(f"Data Connection Error: {str(e)}")
    st.stop()

# --- RESILIENT DATA LOOKUP ENGINE ---
# This ensures string mismatches, single quotes, or minor tracking variations won't break runtime execution.
def get_val(row_data, prefix_token, fallback="N/A"):
    matched_col = [col for col in row_data.index if str(col).strip().startswith(prefix_token)]
    if matched_col:
        val = row_data[matched_col[0]]
        if pd.isna(val) or str(val).strip() == "":
            return fallback
        return str(val).strip()
    return fallback

total_records = len(df)

# --- SESSION NAVIGATION STATE ---
if 'page_index' not in st.session_state:
    st.session_state.page_index = 0

def page_forward():
    if st.session_state.page_index < total_records - 1:
        st.session_state.page_index += 1

def page_backward():
    if st.session_state.page_index > 0:
        st.session_state.page_index -= 1

# --- TOP EDITORIAL NAVIGATIONSpread BAR ---
nav_t1, nav_t2, nav_t3 = st.columns([1, 2, 1])
with nav_t1:
    st.button("◀ Previous Page", on_click=page_backward, disabled=(st.session_state.page_index == 0), key="t_prev")
with nav_t2:
    selected_idx = st.selectbox(
        "Jump directly to facility index:",
        options=range(total_records),
        format_func=lambda x: f"Page {x+1}: {get_val(df.iloc[x], 'Q. 1.2')} - {get_val(df.iloc[x], 'Q. 1.1')[:45]}...",
        index=st.session_state.page_index,
        key="magazine_selector"
    )
    st.session_state.page_index = selected_idx
with nav_t3:
    st.button("Next Page ▶", on_click=page_forward, disabled=(st.session_state.page_index == total_records - 1), key="t_next")

# Extract focused row context
row = df.iloc[st.session_state.page_index]

# --- FACILITY COVER PAGE HEADER ---
st.markdown(f"""
    <div class="magazine-header">
        <h1>{get_val(row, 'Q. 1.1')}</h1>
        <p style="font-size: 1.3rem; font-style: italic; color: #5E5D5A; margin-top: 5px;">
            {get_val(row, 'Q. 1.2')} — Geographic Region {get_val(row, 'Q. 1.3')}
        </p>
    </div>
""", unsafe_allow_html=True)

# --- MAIN PAGE SPREAD: VISUAL SIDE vs IDENTITY SIDE ---
spread_left, spread_right = st.columns([2, 3])

with spread_left:
    # Asset Management Grid (Seals, portraits and landscapes)
    seal_url = get_val(row, 'Q. 6.3')
    if seal_url != "N/A":
        st.image(seal_url, caption="Official Institutional Seal", width=150)
        
    facade_val = get_val(row, 'Q. 6.1')
    if facade_val != "N/A":
        facade_urls = facade_val.split(',')
        st.image(facade_urls[0].strip(), caption="Exterior Facade (Primary View)", use_container_width=True)
        if len(facade_urls) > 1:
            st.image(facade_urls[1].strip(), caption="Exterior Facade (Alternate View)", use_container_width=True)
            
    lobby_url = get_val(row, 'Q. 6.2')
    if lobby_url != "N/A":
        st.image(lobby_url, caption="Main Interior Lobby", use_container_width=True)

with spread_right:
    st.markdown('<div class="section-banner">I. LEADERSHIP, VISION & CORPORATE IDENTITY</div>', unsafe_allow_html=True)
    
    chief_col1, chief_col2 = st.columns([1, 2])
    with chief_col1:
        chief_img = get_val(row, 'Q. 6.4')
        if chief_img != "N/A":
            st.image(chief_img, use_container_width=True, caption="Chief of Facility")
    with chief_col2:
        st.markdown(f"### {get_val(row, 'Q. 2.1')}")
        st.markdown(f"**Designated Role:** *{get_val(row, 'Q. 2.2')}*")
        st.write(f"**Founding Identity:** {get_val(row, 'Q. 2.7')}")
        st.write(f"**Motto / Slogan:** \"{get_val(row, 'Q. 2.5')}\"")

    st.markdown(f"**Institutional Vision Blueprint:**")
    st.markdown(f"<div class='block-quote-editorial'>{get_val(row, 'Q. 2.3')}</div>", unsafe_allow_html=True)
    st.markdown(f"**Mission Directives:**")
    st.markdown(f"<div class='block-quote-editorial'>{get_val(row, 'Q. 2.4')}</div>", unsafe_allow_html=True)
    
    st.write(f"**Latest Legislative / Operational Mandate:** {get_val(row, 'Q. 2.6')}")
    st.write(f"**Staff Gender Metric (End of 2024):** {get_val(row, 'Q. 2.8')}")

# --- PHYSICAL INFRASTRUCTURE & CLASSIFICATION ---
st.markdown('<div class="section-banner">II. INFRASTRUCTURE CAPACITY & LICENSING</div>', unsafe_allow_html=True)
inf_c1, inf_c2, inf_c3 = st.columns(3)

with inf_c1:
    st.markdown(f"""<div class="data-card">
        <h4>Spatial Footprint</h4><hr style='margin:10px 0;'>
        <b>Total Land Area:</b> {get_val(row, 'Q. 3.1')} sqm<br><br>
        <b>Gross Floor Area:</b> {get_val(row, 'Q. 3.2')} sqm<br><br>
        <b>Main Physical Location:</b> {get_val(row, 'Q. 1.4')}<br><br>
        <b>Geospatial Mapping Coordinates:</b> {get_val(row, 'Q. 1.5')}
    </div>""", unsafe_allow_html=True)

with inf_c2:
    st.markdown(f"""<div class="data-card">
        <h4>Regulatory Classifications</h4><hr style='margin:10px 0;'>
        <b>LTO Classification (2024):</b> {get_val(row, 'Q. 3.3')}<br><br>
        <b>Clinical Capability Level:</b> {get_val(row, 'Q. 3.4')}<br><br>
        <b>Malasakit Center Establishment Year:</b> {get_val(row, 'Q. 3.8')}
    </div>""", unsafe_allow_html=True)

with inf_c3:
    st.markdown(f"""<div class="data-card">
        <h4>Bed Allocations Framework</h4><hr style='margin:10px 0;'>
        <b>Authorized Capacity (Statutory Law):</b> {get_val(row, 'Q. 3.5')}<br><br>
        <b>Authorized Capacity (DOH License):</b> {get_val(row, 'Q. 3.6')}<br><br>
        <b>Actual Implementing Beds (As of 2024):</b> {get_val(row, 'Q. 3.7')}
    </div>""", unsafe_allow_html=True)

# --- APEX CARE STRATEGIES & NETWORKS ---
st.markdown('<div class="section-banner">III. APEX REFERRAL STATUS & HEALTH NETWORKS</div>', unsafe_allow_html=True)
ap_c1, ap_c2 = st.columns(2)
with ap_c1:
    st.write(f"**Eligible Apex or End-Referral Designation:** {get_val(row, 'Q. 3.9 (F)')}")
    st.write(f"**Linked Health Care Provider Networks (HCPN):** {get_val(row, 'Q. 3.9.1')}")
    st.write(f"**HCPN Binding Frameworks (MOAs/Legal Instruments):** {get_val(row, 'Q. 3.9.2')}")
with ap_c2:
    st.write(f"**External Owned & Operated Extensions:** {get_val(row, 'Q. 3.11')}")
    st.write(f"**External Operated (Non-Owned) Extensions:** {get_val(row, 'Q. 3.12')}")
    st.write(f"**Associated BUCAS Facility Hub:** {get_val(row, 'Q 3.13.1')} — *{get_val(row, 'Q 3.13.2')}*")

# --- DESIGNATED SPECIALTY CENTERS SPECIAL INTERACTION ---
st.write("#### Designated National Specialty Centers Matrix")
has_specialties = get_val(row, 'Q. 3.10 (F)')
st.write(f"*DOH Designated Specialty Center Status:* **{has_specialties}**")

specialty_map = [
    ("BRAIN AND SPINE CARE", "Q. 3.10.1"), ("BURN CARE", "Q. 3.10.2"),
    ("CANCER CARE", "Q. 3.10.3"), ("CARDIOVASCULAR CARE", "Q. 3.10.4"),
    ("DERMATOLOGY CARE", "Q. 3.10.5"), ("EYE CARE", "Q. 3.10.6"),
    ("GERIATRIC CARE", "Q. 3.10.7"), ("INFECTIOUS DISEASE", "Q. 3.10.8"),
    ("LUNG CARE", "Q. 3.10.9"), ("MENTAL HEALTH", "Q. 3.10.10"),
    ("NEONATAL CARE", "Q. 3.10.11"), ("ORTHOPEDIC CARE", "Q. 3.10.12"),
    ("PHYSICAL REHABILITATION", "Q. 3.10.13"), ("RENAL & KIDNEY TRANSPLANT", "Q. 3.10.14"),
    ("TOXICOLOGY", "Q. 3.10.15"), ("TRAUMA CARE", "Q. 3.10.16")
]

spec_grid = st.columns(4)
for index, (label, token) in enumerate(specialty_map):
    target_column = spec_grid[index % 4]
    status = get_val(row, token, "No")
    if "yes" in status.lower():
        target_column.markdown(f"🔹 **{label}**: `Designated`")
    else:
        target_column.markdown(f"<span style='color:#B0AFA9;'>🔸 {label}: None</span>", unsafe_allow_html=True)

# --- CLINICAL PERFORMANCE AND HISTORICAL TRENDS MATRIX ---
st.markdown('<div class="section-banner">IV. STATISTICAL REPORTING & CHRONOLOGICAL TRENDS</div>', unsafe_allow_html=True)

metrics_table_structure = {
    "Operational Tracking Metrics (Chronological)": [
        "Bed Occupancy Rate (%)",
        "Inpatient Bed Days Metrics",
        "Average Daily Baseline Patients Served",
        "Average Daily Administrative Discharges",
        "Outpatient Clinical Visits Logged",
        "Emergency Room Outpatient Visits"
    ],
    "2022": [get_val(row, 'Q. 4.1.1'), get_val(row, 'Q. 4.2.1'), get_val(row, 'Q. 4.3.1'), get_val(row, 'Q. 4.4.1'), get_val(row, 'Q. 4.5.1'), get_val(row, 'Q. 4.6.1')],
    "2023": [get_val(row, 'Q. 4.1.2'), get_val(row, 'Q. 4.2.2'), get_val(row, 'Q. 4.3.2'), get_val(row, 'Q. 4.4.2'), get_val(row, 'Q. 4.5.2'), get_val(row, 'Q. 4.6.2')],
    "2024": [get_val(row, 'Q. 4.1.3'), get_val(row, 'Q. 4.2.3'), get_val(row, 'Q. 4.3.3'), get_val(row, 'Q. 4.4.3'), get_val(row, 'Q. 4.5.3'), get_val(row, 'Q. 4.6.3')]
}
st.table(pd.DataFrame(metrics_table_structure).set_index("Operational Tracking Metrics (Chronological)"))

stat_box1, stat_box2, stat_box3 = st.columns(3)
with stat_box1:
    st.info(f"**Malasakit Financial Grant Recipients (2024):**\n\n {get_val(row, 'Q. 4.7')}")
with stat_box2:
    st.info(f"**Adult Female Patient Service Matrix (≥18):**\n\n {get_val(row, 'Q. 4.8')}")
with stat_box3:
    st.info(f"**Pediatric/Juvenile Female Patient Matrix (≤17):**\n\n {get_val(row, 'Q. 4.9')}")

# --- COMPLIANCE, QUALITY STANDARDS & STRATEGIC RATINGS ---
st.markdown('<div class="section-banner">V. QUALITY GOVERNANCE, RATINGS & ACCREDITATIONS</div>', unsafe_allow_html=True)
score_c1, score_c2, score_c3 = st.columns(3)

score_c1.metric(label="Hospital Scorecard Rating (2024)", value=get_val(row, 'Q 5.1'))
score_c2.metric(label="IHOMP Assessment Rating (2019)", value=get_val(row, 'Q 5.2'))
score_c3.metric(label="Green Star Quality Rating (2024)", value=get_val(row, 'Q 5.3'))

st.write(f"**ISO 9001 Certification Parameters (Body & Year):** {get_val(row, 'Q. 5.4')}")
st.write(f"**Performance Governance System (PGS) Strategic Status:** {get_val(row, 'Q. 5.5')}")

# --- EXTERNAL CONTACTS AND CORRESPONDENCE TRACKING DIRECTORY ---
st.markdown('<div class="section-banner">VI. CHANNELS OF CORRESPONDENCE & DIRECTORY INFO</div>', unsafe_allow_html=True)
contact_spread_l, contact_spread_r = st.columns(2)

with contact_spread_l:
    st.markdown("""<div class="data-card" style="border-left: 4px solid #4A6B82;">
        <h5>Public Structural Touchpoints</h5><br>
        <b>Landline Connections:</b> """ + get_val(row, 'Q. 1.6') + """<br>
        <b>Mobile Hotlines:</b> """ + get_val(row, 'Q. 1.7') + """<br>
        <b>Official Corporate Email:</b> """ + get_val(row, 'Q. 1.8') + """<br>
        <b>Web Domain:</b> """ + get_val(row, 'Q. 1.9') + """<br>
        <b>Social Media Portals:</b> """ + get_val(row, 'Q. 1.10') + """
    </div>""", unsafe_allow_html=True)

with contact_spread_r:
    st.markdown("""<div class="data-card" style="border-left: 4px solid #824A4A;">
        <h5>Internal Administrative Liaison Profile</h5><br>
        <b>Contact Coordinator:</b> """ + get_val(row, 'Q. 7.1') + """<br>
        <b>Official Position Title:</b> """ + get_val(row, 'Q 7.2') + """<br>
        <b>Department / Operating Unit:</b> """ + get_val(row, 'Q. 7.3') + """<br>
        <b>Direct Mobile Connection:</b> """ + get_val(row, 'Q. 7.4') + """<br>
        <b>Direct Correspondence Email:</b> """ + get_val(row, 'Q. 7.5') + """
    </div>""", unsafe_allow_html=True)

# --- FOOTER MAGAZINE PAGE-FLIP NAVIGATION BLOCK ---
st.markdown("<hr style='border-top: 2px solid #E2DCD2;'>", unsafe_allow_html=True)
nav_b1, nav_b2, nav_b3 = st.columns([1, 2, 1])
with nav_b1:
    st.button("◀ Previous Profile Page", on_click=page_backward, disabled=(st.session_state.page_index == 0), key="b_prev")
with nav_b2:
    st.markdown(f"<p style='text-align: center; color: #767571; font-family: Georgia, serif;'>Profile Sheet {st.session_state.page_index + 1} of {total_records}</p>", unsafe_allow_html=True)
with nav_b3:
    st.button("Next Profile Page ▶", on_click=page_forward, disabled=(st.session_state.page_index == total_records - 1), key="b_next")
