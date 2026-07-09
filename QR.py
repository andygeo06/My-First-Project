import streamlit as st
import qrcode
from io import BytesIO

def generate_qr(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data.strip())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

st.title("🔗 Bulk Link to QR Code Converter")

# Use text_area for multi-line input
links_input = st.text_area("Paste your links here (one link per line):", height=150)

# The initialization button
if st.button("Initialize Generation"):
    if links_input:
        # Split input by newline and remove empty lines
        links = [line for line in links_input.split('\n') if line.strip()]
        
        st.success(f"Processing {len(links)} links...")
        
        # Use columns to display QR codes in a grid (2 columns)
        cols = st.columns(2)
        
        for index, link in enumerate(links):
            qr_buffer = generate_qr(link)
            
            # Display in alternating columns
            with cols[index % 2]:
                st.image(qr_buffer, caption=f"QR {index + 1}", use_container_width=True)
                st.download_button(
                    label=f"Download QR {index + 1}",
                    data=qr_buffer,
                    file_name=f"qrcode_{index + 1}.png",
                    mime="image/png"
                )
    else:
        st.warning("Please paste at least one link before initializing.")
