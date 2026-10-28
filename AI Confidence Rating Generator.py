import streamlit as st
import pandas as pd
import gspread
from google import genai
import time

st.set_page_config(page_title="Form Response AI Essay Analyzer", layout="wide")

st.title("📄 Google Form Responses - AI Essay Analyzer")
st.write("Enter your sheet link to evaluate response text (Columns D & E) with Gemini AI and record results in Column H.")

# Load secrets from Streamlit Secrets
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
    service_account_info = dict(st.secrets["gcp_service_account"])
except Exception as e:
    st.error("Missing Streamlit secrets configuration! Please check your App Secrets on Streamlit Community Cloud.")
    st.stop()

# Helper function with robust retry and error handling
def generate_with_retry(ai_client, model_name, prompt, max_retries=2):
    for attempt in range(max_retries):
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
            return "Error: Empty response from AI"
        except Exception as e:
            error_str = str(e)
            if ("503" in error_str or "429" in error_str) and attempt < max_retries - 1:
                time.sleep((2 ** attempt) * 2)
                continue
            else:
                return f"API Error: {error_str}"
    return "Error: Max retries exceeded"

# User Input Form
with st.form("analysis_form"):
    sheet_url = st.text_input(
        "Google Sheet URL / Link", 
        placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit..."
    )
    tab_name = st.text_input("Tab Name", value="Form Responses 1")
    submitted = st.form_submit_button("Fetch & Analyze Essays", type="primary")

if submitted:
    if not sheet_url.strip():
        st.error("Please enter a valid Google Sheet URL.")
    else:
        try:
            st.info("Authenticating with Google Sheets...")
            gc = gspread.service_account_from_dict(service_account_info)
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.worksheet(tab_name)

            st.info("Fetching response data from sheet...")
            
            d_values = worksheet.col_values(4)[1:]  # Skip header D1
            e_values = worksheet.col_values(5)[1:]  # Skip header E1
            h_values = worksheet.col_values(8)[1:]  # Existing Column H values

            max_len = max(len(d_values), len(e_values))

            d_values += [""] * (max_len - len(d_values))
            e_values += [""] * (max_len - len(e_values))
            h_values += [""] * (max_len - len(h_values))

            ai_client = genai.Client(api_key=gemini_api_key)

            results = []
            updates_to_make = []

            progress_bar = st.progress(0)
            status_text = st.empty()

            for i in range(max_len):
                row_idx = i + 2  
                col_d_text = str(d_values[i]).strip()
                col_e_text = str(e_values[i]).strip()
                
                combined_essay = f"{col_d_text}\n{col_e_text}".strip()
                existing_h = str(h_values[i]).strip()

                if existing_h:
                    results.append(existing_h)
                    continue

                if not combined_essay:
                    results.append("No essay text found")
                    continue

                status_text.text(f"Analyzing Row {row_idx} of {max_len + 1}...")

                prompt = (
                    "Analyze the following submission text and evaluate whether it was likely written by an AI or a human. "
                    "Provide a concise response starting with a confidence percentage (e.g., '85% Likely AI') "
                    "followed by 1 brief bullet explaining why based on writing style, perplexity, or repetition.\n\n"
                    f"Text:\n\"{combined_essay}\""
                )

                # Safely generate analysis without breaking the loop
                analysis = generate_with_retry(ai_client, "gemini-3.8-flash", prompt)
                results.append(analysis)

                updates_to_make.append({
                    'range': f'H{row_idx}',
                    'values': [[analysis]]
                })

                progress_bar.progress((i + 1) / max_len)
                time.sleep(0.3)  # Short breather

            if updates_to_make:
                st.info("Writing results back to Column H...")
                worksheet.batch_update(updates_to_make)
                st.success("Successfully analyzed and updated Column H!")
            else:
                st.warning("No new pending rows detected in Column H.")

            st.subheader("Results Overview")
            df = pd.DataFrame({
                "Row": range(2, max_len + 2),
                "Column D": d_values,
                "Column E": e_values,
                "Column H (AI Detection Result)": results
            })
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Failed to process sheet: {str(e)}")
