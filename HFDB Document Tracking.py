import streamlit as st
import pandas as pd
import random
import string
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# CORE CONNECTION
# -----------------------------------------------------------------------------
def get_connection():
    """Initializes and returns the Google Sheets connection."""
    return st.connection("gsheets", type=GSheetsConnection)

# -----------------------------------------------------------------------------
# READ OPERATIONS (Cached to save API tokens)
# -----------------------------------------------------------------------------
@st.cache_data(ttl="10m") 
def get_staff_data():
    """Pulls the STAFF tab. Adapts to the 7-column structure (A to G)."""
    conn = get_connection()
    try:
        # Read columns A through G (0 to 6)
        df = conn.read(worksheet="STAFF", usecols=[0, 1, 2, 3, 4, 5, 6], ttl="10m")
        df.columns = ["Division", "Nickname", "Name of Staff", "Staff Email", "Division Email", "Code", "Category"]
        df = df.dropna(subset=["Name of Staff"]) # Clean empty rows
        return df
    except Exception as e:
        st.error(f"Failed to load STAFF sheet: {e}")
        return pd.DataFrame(columns=["Division", "Nickname", "Name of Staff", "Staff Email", "Division Email", "Code", "Category"])

def get_unregistered_staff():
    """Returns a list of names from the STAFF tab that don't have a login code yet."""
    df = get_staff_data()
    unregistered = df[df["Code"].isna() | (df["Code"] == "")]
    return unregistered["Name of Staff"].tolist()

# -----------------------------------------------------------------------------
# AUTHENTICATION LOGIC
# -----------------------------------------------------------------------------
def authenticate_user(login_code):
    """
    Checks the entered code against the DB. 
    Returns a dict with comprehensive user info if valid, or None.
    """
    df = get_staff_data()
    
    match = df[df["Code"] == login_code]
    
    if not match.empty:
        user_info = match.iloc[0]
        return {
            "division": user_info["Division"],
            "nickname": user_info["Nickname"],
            "name": user_info["Name of Staff"],
            "staff_email": user_info["Staff Email"],
            "division_email": user_info["Division Email"],
            "code": user_info["Code"],
            "category": user_info["Category"] # Explicit category tracking
        }
    return None

# -----------------------------------------------------------------------------
# WRITE OPERATIONS (Sign-up)
# -----------------------------------------------------------------------------
def generate_hfdb_code():
    """Generates a random code like HFDB-0AKjd88sk211"""
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return f"HFDB-{suffix}"

def register_new_user(name_of_staff):
    """
    Generates a code, updates the sheet, and clears the cache.
    Returns the newly generated code so the user can copy it.
    """
    new_code = generate_hfdb_code()
    conn = get_connection()
    
    # 1. Get current data (bypass cache to ensure we have latest)
    df = conn.read(worksheet="STAFF", usecols=[0, 1, 2, 3, 4, 5, 6], ttl=0)
    df.columns = ["Division", "Nickname", "Name of Staff", "Staff Email", "Division Email", "Code", "Category"]
    
    # 2. Find the row with the matching Name and update the Code column
    df.loc[df["Name of Staff"] == name_of_staff, "Code"] = new_code
    
    # 3. Write back to Google Sheets
    try:
        conn.update(worksheet="STAFF", data=df)
        
        # 4. Clear the cache so the new user instantly shows as registered
        st.cache_data.clear()
        
        return new_code
    except Exception as e:
        st.error(f"Failed to register user in database: {e}")
        return None
