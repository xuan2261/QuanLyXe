import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging

# Tải biến môi trường từ file .env
load_dotenv()

# Kết nối tới MongoDB
MONGO_URI = os.getenv("MONGODB_CONNECTION_STRING")
client = MongoClient(MONGO_URI) # Cấu hình connection pool
db = client["rental_system"]

# Cấu hình logging chi tiết
logging.basicConfig(
    filename='system.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Cấu hình secret key cho JWT
SECRET_KEY = os.getenv("SECRET_KEY")