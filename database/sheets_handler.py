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

def sanitize_and_pad_dataframe(df):
    """Dynamically pads columns to guarantee a 7-column layout (A to G)."""
    expected_cols = ["Division", "Nickname", "Name of Staff", "Staff Email", "Division Email", "Code", "Category"]
    current_col_count = len(df.columns)
    
    # If Google returns fewer columns than expected, pad the rest with blanks
    if current_col_count < len(expected_cols):
        for i in range(current_col_count, len(expected_cols)):
            df[f"padded_col_{i}"] = ""
            
    # Slice down to exactly the first 7 columns and assign standard headers
    df = df.iloc[:, :7]
    df.columns = expected_cols
    
    # FIX: Force text columns to 'object' type so Pandas allows string insertions
    df["Code"] = df["Code"].astype(object)
    df["Category"] = df["Category"].astype(object)
    return df

# -----------------------------------------------------------------------------
# READ OPERATIONS (Cached to save API tokens)
# -----------------------------------------------------------------------------
@st.cache_data(ttl="10m") 
def get_staff_data():
    """Pulls the STAFF tab dynamically without hardcoded index limits."""
    conn = get_connection()
    try:
        df = conn.read(worksheet="STAFF", ttl="10m")
        df = sanitize_and_pad_dataframe(df)
        df = df.dropna(subset=["Name of Staff"])
        return df
    except Exception as e:
        st.error(f"Failed to load STAFF sheet: {e}")
        return pd.DataFrame(columns=["Division", "Nickname", "Name of Staff", "Staff Email", "Division Email", "Code", "Category"])

def get_unregistered_staff():
    """Returns a list of names from the STAFF tab that don't have a login code yet."""
    df = get_staff_data()
    unregistered = df[df["Code"].isna() | (df["Code"] == "") | (df["Code"].astype(str).str.strip() == "nan") | (df["Code"].astype(str).str.strip() == "")]
    return unregistered["Name of Staff"].tolist()

# -----------------------------------------------------------------------------
# AUTHENTICATION LOGIC
# -----------------------------------------------------------------------------
def authenticate_user(login_code):
    """Checks the entered code against the DB. Returns user info dict or None."""
    df = get_staff_data()
    df["Code"] = df["Code"].astype(str).str.strip()
    match = df[df["Code"] == str(login_code).strip()]
    
    if not match.empty:
        user_info = match.iloc[0]
        return {
            "division": user_info["Division"],
            "nickname": user_info["Nickname"],
            "name": user_info["Name of Staff"],
            "staff_email": user_info["Staff Email"],
            "division_email": user_info["Division Email"],
            "code": user_info["Code"],
            "category": user_info["Category"]
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
    """Generates a code, updates the sheet, and clears the cache."""
    new_code = generate_hfdb_code()
    conn = get_connection()
    
    try:
        df = conn.read(worksheet="STAFF", ttl=0)
        df = sanitize_and_pad_dataframe(df)
        
        # Insert the newly minted code into the matched row safely
        df.loc[df["Name of Staff"] == name_of_staff, "Code"] = new_code
        
        conn.update(worksheet="STAFF", data=df)
        st.cache_data.clear()
        return new_code
    except Exception as e:
        st.error(f"Failed to register user in database: {e}")
        return None
