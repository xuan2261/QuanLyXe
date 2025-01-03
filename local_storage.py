from config import db
from pymongo.errors import ServerSelectionTimeoutError
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kết nối SQLite
def get_db_connection():
    return sqlite3.connect('local_data.db', check_same_thread=False)

# Tạo bảng cục bộ nếu chưa có
def initialize_db():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            brand TEXT,
                            model TEXT,
                            license_plate TEXT UNIQUE,
                            price_per_day REAL,
                            status TEXT,
                            year INTEGER,
                            created_at TEXT,
                            image TEXT
                        )''')
            conn.commit()
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")

# Gọi hàm khởi tạo cơ sở dữ liệu khi ứng dụng khởi động
initialize_db()

def save_vehicle_locally(vehicle_data):
    """Lưu dữ liệu xe tạm thời khi MongoDB không kết nối được."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO vehicles (brand, model, license_plate, price_per_day, status, year, created_at, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (vehicle_data['brand'], vehicle_data['model'], vehicle_data['license_plate'], vehicle_data['price_per_day'], vehicle_data['status'], vehicle_data['year'], vehicle_data['created_at'], vehicle_data.get('image', '')))
            conn.commit()
            logger.info("Vehicle saved locally.")
    except sqlite3.Error as e:
        logger.error(f"Error saving vehicle locally: {e}")

def get_all_local_vehicles():
    """Lấy tất cả các xe từ bộ nhớ cục bộ."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT brand, model, license_plate, price_per_day, status, year, created_at, image FROM vehicles')
            vehicles = cursor.fetchall()
            # Chuyển đổi dữ liệu tuple sang dictionary
            vehicles_dict = []
            for vehicle in vehicles:
                vehicles_dict.append({
                    "brand": vehicle[0],
                    "model": vehicle[1],
                    "license_plate": vehicle[2],
                    "price_per_day": vehicle[3],
                    "status": vehicle[4],
                    "year": vehicle[5],
                    "created_at": vehicle[6],
                    "image": vehicle[7]
                })
            logger.info("Fetched all local vehicles.")
            return vehicles_dict
    except sqlite3.Error as e:
        logger.error(f"Error fetching local vehicles: {e}")
        return []

def clear_local_storage():
    """Xóa dữ liệu đã lưu cục bộ sau khi đồng bộ với MongoDB."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM vehicles')
            conn.commit()
            logger.info("Local storage cleared.")
    except sqlite3.Error as e:
        logger.error(f"Error clearing local storage: {e}")

def is_mongodb_connected():
    """Kiểm tra xem MongoDB có kết nối được không."""
    try:
        # Kiểm tra kết nối bằng cách truy vấn thử một bản ghi
        db.command('ping')
        logger.info("MongoDB is connected.")
        return True
    except ServerSelectionTimeoutError:
        logger.warning("MongoDB connection failed.")
        return False