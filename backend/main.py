from fastapi import FastAPI, File, UploadFile
import pytesseract
from PIL import Image
import io
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace
from kafka import KafkaProducer
import json

app = FastAPI()

# Initialize Spark Session
spark = SparkSession.builder.appName("OCRProcessor").getOrCreate()

# Initialize Kafka Producer
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # Read the uploaded image
    image = Image.open(io.BytesIO(await file.read()))
    
    # Extract text using Tesseract
    text = pytesseract.image_to_string(image)
    
    # Process text using Spark
    processed_text = process_text_with_spark(text)
    
    producer.send("ocr-text", {"text": processed_text})
    
    return {"text": processed_text}

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

@app.get("/")
async def root():
    return {"message": "FastAPI backend is running!"}
