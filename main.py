import os
import streamlit as st
st.set_page_config(page_title="Hệ Thống Quản Lý Cho Thuê Xe", layout="wide")

from modules.auth import register, login
from modules.customer import customer_dashboard
from modules.admin import admin_dashboard
from modules.vehicle import initialize_vehicle_data
from local_storage import get_all_local_vehicles, clear_local_storage, is_mongodb_connected
from config import db
from dotenv import load_dotenv
import bcrypt
import time
import json
from bson import ObjectId
import datetime
import logging
from streamlit_cookies_manager import EncryptedCookieManager
from jose import JWTError, jwt

load_dotenv()

# Thiết lập cấu hình logging
logging.basicConfig(
    filename='system.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cấu hình JWT
ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY")

# Helper function to serialize ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

# Hàm tạo tài khoản admin mặc định
def create_default_admin():
    admin_email = "admin@rental.com"
    admin_password = "admin123"

    existing_admin = db.users.find_one({"email": admin_email, "role": "admin"})
    if not existing_admin:
        from modules.auth import encrypt_data
        hashed_pw = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
        encrypted_password = encrypt_data(hashed_pw.decode())
        admin_user = {
            "full_name": "Admin",
            "email": admin_email,
            "password": encrypted_password,
            "phone": "123456789",
            "role": "admin",
            "created_at": datetime.datetime.now()
        }
        db.users.insert_one(admin_user)
        logger.info("Tài khoản admin mặc định đã được tạo!")
    else:
        logger.info("Tài khoản admin đã tồn tại.")

# (Tùy chọn) Chạy code tạo bảng payment_cards và thêm dữ liệu mẫu
def initialize_payment_cards():
    if "payment_cards" not in db.list_collection_names():
        db.create_collection("payment_cards")
        db.payment_cards.create_index([("card_number", 1)], unique=True)
        db.payment_cards.insert_many([
            {
                "card_number": "1111222233334444",
                "card_holder": "Nguyen Van A",
                "balance": 1500000.0,
                "account_status": "active",
                "expiry_date": "2025-12-31"
            },
            {
                "card_number": "5555666677778888",
                "card_holder": "Tran Thi B",
                "balance": 50.0,
                "account_status": "active",
                "expiry_date": "2024-12-31"
            },
            {
                "card_number": "9999888877776666",
                "card_holder": "Le Van C",
                "balance": 2000.0,
                "account_status": "locked",
                "expiry_date": "2026-12-31"
            },
            {
                "card_number": "1234567890123456",
                "card_holder": "Pham Thi D",
                "balance": 300.0,
                "account_status": "active",
                "expiry_date": "2022-12-31"  # Thẻ hết hạn
            }
        ])
        logger.info("Đã tạo bảng payment_cards và thêm dữ liệu mẫu.")

# Hàm xác thực token người dùng
def authenticate_user_token(user_token):
    try:
        payload = jwt.decode(user_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            user = db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                return user
        return None
    except JWTError as e:
        logger.error(f"Lỗi xác thực token: {e}")
        return None

# Hàm tạo token người dùng
def create_user_token(user):
    expires_delta = datetime.timedelta(minutes=3600) # Thời gian hết hạn token
    to_encode = {"sub": str(user["_id"])}
    expire = datetime.datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Hàm đăng nhập người dùng
def login_user(email, password):
    from modules.auth import decrypt_data
    user = db.users.find_one({"email": email})
    if user:
        decrypted_password = decrypt_data(user['password'])
        if bcrypt.checkpw(password.encode('utf-8'), decrypted_password.encode('utf-8')):
            logger.info("Đăng nhập thành công.")
            return user
    logger.warning("Đăng nhập thất bại: email hoặc mật khẩu không đúng.")
    return None

def clear_all_cookies(cookie_manager):
    for key in list(cookie_manager.keys()):
        del cookie_manager[key]
    cookie_manager.save()

def main():
    st.title("Hệ Thống Quản Lý Cho Thuê Xe")

    # Kiểm tra kết nối MongoDB
    if is_mongodb_connected():
        # initialize_vehicle_data()
        # create_default_admin()
        # initialize_payment_cards() # Chạy hàm khởi tạo bảng payment_cards

        # Đồng bộ dữ liệu từ local storage (nếu có)
        local_vehicles = get_all_local_vehicles()
        if local_vehicles:
            with st.spinner("Đang đồng bộ dữ liệu từ local storage..."):
                for vehicle in local_vehicles:
                    try:
                        db.vehicles.insert_one(vehicle)
                    except Exception as e:
                        logger.error(f"Lỗi khi đồng bộ xe: {e}")
                clear_local_storage()
            st.success("Đồng bộ dữ liệu thành công!")
    else:
        st.error("Không thể kết nối đến MongoDB. Vui lòng kiểm tra file `system.log`")

    # Sử dụng EncryptedCookieManager để quản lý cookie
    cookie_manager = EncryptedCookieManager(password="quanlychothuexe")

    if not cookie_manager.ready():
        # st.stop()
        with st.spinner("Đang tải..."):
            time.sleep(1)  # Chờ một khoảng thời gian ngắn để cookie_manager sẵn sàng

    # # Xóa tất cả cookie khi khởi động chương trình
    # clear_all_cookies(cookie_manager)

    user_token = cookie_manager.get("user_token")

    if user_token:
        user = authenticate_user_token(user_token)
        if user:
            # Bỏ qua mật khẩu khi hiển thị thông tin người dùng
            user.pop('password', None)

            if user.get("role") == "admin":
                admin_dashboard(user)
            else:
                customer_dashboard(user)

            if st.sidebar.button("Đăng Xuất"):
                # Xóa token session trong db
                db.sessions.delete_one({"token": user_token})
                # Xóa cookie
                clear_all_cookies(cookie_manager)
                time.sleep(0.5) # Dừng 1 khoảng ngắn
                st.success("Đăng xuất thành công!")
                st.rerun()
            
        else:
            st.warning("Phiên làm việc đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.")
            # Xóa cookie khi token không hợp lệ
            clear_all_cookies(cookie_manager)
            time.sleep(0.5) # Dừng 1 khoảng ngắn
            st.rerun()
    else:
        # Chỉ hiển thị form đăng nhập/đăng ký khi chưa đăng nhập
        show_login_register_forms(cookie_manager)

def show_login_register_forms(cookie_manager):
    menu = ["Đăng Nhập", "Đăng Ký"]

    # Kiểm tra nếu đã đăng ký thành công thì hiển thị form đăng nhập
    if 'login_form_submitted' in st.session_state and st.session_state['login_form_submitted']:
        choice = "Đăng Nhập"
        st.session_state['login_form_submitted'] = False  # Reset lại trạng thái
    else:
        # Chỉ tạo selectbox ở đây, một lần duy nhất
        choice = st.sidebar.selectbox("Menu", menu, key="menu_auth")

    if choice == "Đăng Ký":
        register()
    elif choice == "Đăng Nhập":
        email = st.text_input("Email")
        password = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng Nhập"):
            user = login_user(email, password)
            if user:
                user_token = create_user_token(user)

                # Lưu token vào cookie
                cookie_manager["user_token"] = user_token
                cookie_manager.save()

                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Email hoặc mật khẩu không đúng.")

if __name__ == '__main__':
    main()