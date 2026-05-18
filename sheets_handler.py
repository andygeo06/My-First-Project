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
@st.cache_data(ttl="10m") # Cache clears every 10 mins to catch new signups
def get_staff_data():
    """Pulls the STAFF tab. Assumes columns: Name, Role, Login_Code"""
    conn = get_connection()
    try:
        # Update spreadsheet URL or use secrets.toml mapping
        df = conn.read(worksheet="STAFF", usecols=[0, 1, 2], ttl="10m")
        df.columns = ["Name", "Role", "Login_Code"]
        df = df.dropna(subset=["Name"]) # Clean empty rows
        return df
    except Exception as e:
        st.error(f"Failed to load STAFF sheet: {e}")
        return pd.DataFrame(columns=["Name", "Role", "Login_Code"])

def get_unregistered_staff():
    """Returns a list of names from the STAFF tab that don't have a login code yet."""
    df = get_staff_data()
    # Filter for rows where Login_Code is null, NaN, or empty string
    unregistered = df[df["Login_Code"].isna() | (df["Login_Code"] == "")]
    return unregistered["Name"].tolist()

# -----------------------------------------------------------------------------
# AUTHENTICATION LOGIC
# -----------------------------------------------------------------------------
def authenticate_user(login_code):
    """
    Checks the entered code against the DB. 
    Returns a dict with user info if valid, or None if invalid.
    """
    df = get_staff_data()
    
    # Check if code exists in the dataframe
    match = df[df["Login_Code"] == login_code]
    
    if not match.empty:
        user_info = match.iloc[0]
        return {
            "name": user_info["Name"],
            "role": user_info["Role"],
            "code": user_info["Login_Code"]
        }
    return None

# -----------------------------------------------------------------------------
# WRITE OPERATIONS (Sign-up)
# -----------------------------------------------------------------------------
def generate_hfdb_code():
    """Generates a random code like HFDB-0AKjd88sk211"""
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return f"HFDB-{suffix}"

def register_new_user(name):
    """
    Generates a code, updates the sheet, and clears the cache.
    Returns the newly generated code so the user can copy it.
    """
    new_code = generate_hfdb_code()
    conn = get_connection()
    
    # 1. Get current data (bypass cache to ensure we have latest)
    df = conn.read(worksheet="STAFF", usecols=[0, 1, 2], ttl=0)
    df.columns = ["Name", "Role", "Login_Code"]
    
    # 2. Find the row with the matching name and update the code
    df.loc[df["Name"] == name, "Login_Code"] = new_code
    
    # 3. Write back to Google Sheets
    try:
        conn.update(worksheet="STAFF", data=df)
        
        # 4. Clear the cache so the new user instantly shows as registered
        st.cache_data.clear()
        
        return new_code
    except Exception as e:
        st.error(f"Failed to register user in database: {e}")
        return None
