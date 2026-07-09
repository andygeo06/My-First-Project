import streamlit as st
import qrcode
from io import BytesIO

def generate_qr(data):
    # Create QR code object
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save image to a bytes buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

st.title("🔗 Link to QR Code Converter")

# User input
url_input = st.text_input("Enter your link here:")

if url_input:
    # Generate the QR code
    qr_buffer = generate_qr(url_input)
    
    # Display the image in Streamlit
    st.image(qr_buffer, caption="Scan this code", use_container_width=False)
    
    # Add a download button
    st.download_button(
        label="Download QR Code",
        data=qr_buffer,
        file_name="qrcode.png",
        mime="image/png"
    )
