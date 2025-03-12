from fastapi import FastAPI, File, UploadFile
import pytesseract
from PIL import Image
import io

app = FastAPI()

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # Read the uploaded image
    image = Image.open(io.BytesIO(await file.read()))
    
    # Extract text using Tesseract
    text = pytesseract.image_to_string(image)
    
    return {"text": text}

@app.get("/")
async def root():
    return {"message": "FastAPI backend is running!"}