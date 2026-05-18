import streamlit as st
from database import sheets_handler

st.title("HFDB Document Tracking - Dev Test")

st.write("Testing Database Connection...")

# 1. Let's try to pull the STAFF sheet and display it
try:
    df_staff = sheets_handler.get_staff_data()
    st.success("Successfully connected to Google Sheets!")
    st.dataframe(df_staff) # This draws the table on your screen
    
    # 2. Let's list who needs to register
    unregistered = sheets_handler.get_unregistered_staff()
    st.write(f"Staff needing codes: {unregistered}")
    
except Exception as e:
    st.error("Failed to connect. Check your secrets.toml!")
    st.write(e)
