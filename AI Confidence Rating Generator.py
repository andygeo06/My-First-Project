import streamlit as st
import pandas as pd
import gspread
from groq import Groq
import time

st.set_page_config(page_title="Form Response AI Essay Analyzer (Groq)", layout="wide")

st.title("📄 Google Form Responses - AI Essay Analyzer (Groq Powered)")
st.write("Enter your sheet link to evaluate response text (Columns D & E) with Llama 3 on Groq and record results in Column H.")

# Load secrets from Streamlit Secrets
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    service_account_info = dict(st.secrets["gcp_service_account"])
except Exception as e:
    st.error("Missing Streamlit secrets configuration! Please ensure GROQ_API_KEY and gcp_service_account are set in your App Secrets.")
    st.stop()

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
            with st.status("Connecting and processing...", expanded=True) as status:
                st.write("Authenticating with Google Sheets...")
                gc = gspread.service_account_from_dict(service_account_info)
                sh = gc.open_by_url(sheet_url)
                worksheet = sh.worksheet(tab_name)

                st.write("Fetching response data from sheet...")
                d_values = worksheet.col_values(4)[1:]  # Skip header D1
                e_values = worksheet.col_values(5)[1:]  # Skip header E1
                h_values = worksheet.col_values(8)[1:]  # Existing Column H values

                max_len = max(len(d_values), len(e_values))

                d_values += [""] * (max_len - len(d_values))
                e_values += [""] * (max_len - len(e_values))
                h_values += [""] * (max_len - len(h_values))

                # Initialize Groq Client
                groq_client = Groq(api_key=groq_api_key)

                results = []
                updated_count = 0

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

                    st.write(f"Analyzing Row {row_idx} of {max_len + 1}...")

                    prompt = (
                        "Analyze the following submission text and evaluate whether it was likely written by an AI or a human. "
                        "Provide a concise response starting with a confidence percentage (e.g., '85% Likely AI') "
                        "followed by 1 brief bullet explaining why based on writing style, perplexity, or repetition.\n\n"
                        f"Text:\n\"{combined_essay}\""
                    )

                    # Call Groq API (Llama 3.3 70B)
                    try:
                        chat_completion = groq_client.chat.completions.create(
                            messages=[
                                {
                                    "role": "user",
                                    "content": prompt,
                                }
                            ],
                            model="openai/gpt-oss-120b",
                        )
                        analysis = chat_completion.choices[0].message.content.strip()
                    except Exception as api_err:
                        analysis = f"Groq API Error: {str(api_err)}"

                    results.append(analysis)

                    # Write to sheet immediately per row
                    try:
                        worksheet.update_acell(f'H{row_idx}', analysis)
                        updated_count += 1
                    except Exception as write_err:
                        st.warning(f"Could not write to Row {row_idx} directly: {write_err}")

                    time.sleep(0.2) # Short pause

                status.update(label="Processing complete!", state="complete", expanded=False)

            st.success(f"Successfully processed and updated {updated_count} rows using Groq!")

            # Summary Table
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
