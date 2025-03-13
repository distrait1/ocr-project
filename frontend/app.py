import streamlit as st
from PIL import Image
import io
import datetime
from keycloak import KeycloakOpenID
from streamlit_cookies_manager import CookieManager
import pytesseract
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace
from kafka import KafkaProducer
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Backend API URL
BACKEND_URL = "http://localhost:8000/upload"

# Keycloak settings
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM") 
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET") 
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", 3)) 


# Initialize Keycloak client
keycloak_openid = KeycloakOpenID(server_url=KEYCLOAK_SERVER_URL,
                                 client_id=KEYCLOAK_CLIENT_ID,
                                 realm_name=KEYCLOAK_REALM,
                                 client_secret_key=KEYCLOAK_CLIENT_SECRET)

cookies = CookieManager()

# Initialize Spark Session
spark = SparkSession.builder.appName("OCRProcessor").getOrCreate()

# Initialize Kafka Producer
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

def process_text_with_spark(text):
    """Processes the OCR text using PySpark."""
    data = [(text,)]
    df = spark.createDataFrame(data, ["raw_text"])

    # Example: Remove non-alphanumeric characters and extra spaces
    df = df.withColumn("cleaned_text", regexp_replace(col("raw_text"), "[^\\w\\s]+", ""))
    df = df.withColumn("cleaned_text", regexp_replace(col("cleaned_text"), "\\s+", " "))

    # Extract the cleaned text
    cleaned_text = df.select("cleaned_text").collect()[0]["cleaned_text"]
    
    return cleaned_text

def authenticate_user(username, password):
    try:
        token = keycloak_openid.token(username, password)
    except Exception as e:
        st.error("Incorrect email or password.")
        return None, False
    roles = set(keycloak_openid.decode_token(token['access_token'])["resource_access"]
                    .get(KEYCLOAK_CLIENT_ID, {}).get("roles", []))
    if "access-tesseract" not in roles:
        return token, False
    return token, True

if cookies.ready():
    if "token" in cookies:
        st.session_state["token"] = cookies.get("token")
    if "expires_at" in cookies:
        try:
            st.session_state["expires_at"] = datetime.datetime.fromisoformat(cookies.get("expires_at"))
        except Exception:
            pass

if "expires_at" in st.session_state and datetime.datetime.now(datetime.timezone.utc) > st.session_state["expires_at"]:
    st.error("Session expired. Please log in again.")
    st.session_state.clear()
    cookies.__delitem__("token")
    cookies.__delitem__("expires_at")
    cookies.save()
    st.rerun()

def logout():
    st.session_state.clear()
    cookies.__delitem__("token")
    cookies.__delitem__("expires_at")
    cookies.save()
    st.rerun()

if "token" not in st.session_state:
    st.title("Login to Image Text Extractor")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        token, has_access = authenticate_user(username, password)
        if token is None:
            st.error("Incorrect email or password.")
        elif not has_access:
            st.error("Insufficient permissions. Your account does not have the required role.")
        else:
            st.session_state["token"] = token
            st.session_state["expires_at"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=SESSION_EXPIRY_HOURS)
            cookies["token"] = token
            cookies["expires_at"] = st.session_state["expires_at"].isoformat()
            cookies.save()
            st.success("Login successful!")
            st.rerun()
else:
    st.title("Image Text Extractor")
    if st.button("Logout"):
        logout()
    
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        # Display the uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)

        if st.button("Extract Text"):
            # Read the uploaded image
            image = Image.open(uploaded_file)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image)
            
            # Process text using Spark
            processed_text = process_text_with_spark(text)
            
            producer.send("ocr-text", {"text": processed_text})
            
            st.text_area("Extracted Text", processed_text, height=200)
    
    st.write("User authenticated and active session.")