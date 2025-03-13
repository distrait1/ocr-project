import streamlit as st
import requests
from PIL import Image
import io

BACKEND_URL = "http://127.0.0.1:8000/upload"

st.title("Image Text Extractor")

uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    # Display the uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_container_width=True)

    if st.button("Extract Text"):
        # Send the image to the backend
        files = {"file": uploaded_file.getvalue()}
        response = requests.post(BACKEND_URL, files=files)
        
        if response.status_code == 200:
            text = response.json()["text"]
            st.text_area("Extracted Text", text, height=200)
        else:
            st.error("Failed to extract text.")