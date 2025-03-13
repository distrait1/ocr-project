from kafka import KafkaConsumer
import json
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class OCRData(Base):
    __tablename__ = 'ocr_data'
    id = Column(Integer, primary_key=True)
    text = Column(String)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

consumer = KafkaConsumer(
    "ocr-text",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

for message in consumer:
    text = message.value['text']
    ocr_entry = OCRData(text=text)
    session.add(ocr_entry)
    session.commit()
    print(f"Stored: {text}")
    
session.close()