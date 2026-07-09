import streamlit as st
import qrcode
from io import BytesIO

def generate_qr(data):
    # Aggressive cleaning: remove whitespace, tabs, and newlines
    clean_data = "".join(data.split())
    
    # Force add https:// if it is missing
    if not clean_data.lower().startswith(("http://", "https://")):
        clean_data = "https://" + clean_data
        
    # Use High error correction (better for dense/complex URLs)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(clean_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

st.title("🔗 HFDB Professional Bulk QR Generator")

st.markdown("""
Paste your links below. Each link will be automatically formatted for **direct mobile browser opening**. 
Use your phone's **native camera app** for the best experience.
""")

# Text area for bulk input
links_input = st.text_area("Paste your links here (one per line):", height=200)

if st.button("Initialize Generation"):
    if links_input:
        # Split by lines and remove empty ones
        links = [line for line in links_input.split('\n') if line.strip()]
        
        st.success(f"Successfully processed {len(links)} link(s).")
        
        # Grid layout for readability
        cols = st.columns(2)
        
        for index, link in enumerate(links):
            qr_buffer = generate_qr(link)
            
            with cols[index % 2]:
                st.image(qr_buffer, caption=f"Link {index + 1}", use_container_width=True)
                st.download_button(
                    label=f"Download QR {index + 1}",
                    data=qr_buffer,
                    file_name=f"qrcode_{index + 1}.png",
                    mime="image/png"
                )
    else:
        st.warning("Please paste at least one link before initializing.")
