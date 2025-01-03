import streamlit as st
from config import db
import bcrypt
from utils import sanitize_input
import datetime
import time

def encrypt_data(data):
    """Mã hóa dữ liệu sử dụng Fernet."""
    from cryptography.fernet import Fernet
    import os
    FERNET_KEY = os.environ.get("FERNET_KEY").encode()
    cipher = Fernet(FERNET_KEY)
    encrypted_data = cipher.encrypt(data.encode())
    return encrypted_data.decode()

def decrypt_data(encrypted_data):
    """Giải mã dữ liệu đã mã hóa bằng Fernet."""
    from cryptography.fernet import Fernet
    import os
    FERNET_KEY = os.environ.get("FERNET_KEY").encode()
    cipher = Fernet(FERNET_KEY)
    decrypted_data = cipher.decrypt(encrypted_data.encode())
    return decrypted_data.decode()

def register():
    st.subheader("Đăng Ký")
    full_name = sanitize_input(st.text_input("Họ và Tên"))
    email = sanitize_input(st.text_input("Email"))
    password = st.text_input("Mật khẩu", type="password")
    phone = sanitize_input(st.text_input("Số Điện Thoại"))
    address = sanitize_input(st.text_input("Địa chỉ (không bắt buộc)"))
    license_type = st.selectbox("Hạng bằng lái", ["A1", "A2", "B1", "B2", "C", "D", "E", "F"])
    license_expiry = st.date_input("Ngày hết hạn bằng lái")

    if st.button("Đăng Ký"):
        if full_name and email and password and phone:
            
            # Kiểm tra email đã tồn tại chưa
            existing_user = db.users.find_one({"email": email})
            if existing_user:
                st.error("Email đã tồn tại. Vui lòng sử dụng email khác.")
                return
            
            existing_phone = db.users.find_one({"phone": phone})
            if existing_phone:
                st.error("Số điện thoại đã tồn tại. Vui lòng sử dụng số điện thoại khác.")
                return
            
            
            # Mã hóa mật khẩu
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            # Mã hóa mật khẩu đã hash lần nữa trước khi lưu vào db
            encrypted_password = encrypt_data(hashed_pw.decode())
            user = {
                "full_name": full_name,
                "email": email,
                "password": encrypted_password,
                "phone": phone,
                "address": address,
                "role": "customer",
                "created_at": datetime.datetime.now(),
                "driver_license": {
                    "type": license_type,
                    "expiry_date": license_expiry.isoformat()
                }
            }
            try:
                db.users.insert_one(user)
                st.success("Đăng ký thành công! Đang chuyển hướng đến trang đăng nhập...")
                time.sleep(2) # Tạm dừng 2 giây để hiển thị thông báo
                st.session_state['login_form_submitted'] = True # Đánh dấu là đã đăng ký
                st.rerun() # Thay experimental_rerun bằng rerun
            except Exception as e:
                st.error("Đăng ký thất bại, email đã tồn tại!")
                st.error(f"Chi tiết lỗi: {e}")
        else:
            st.error("Vui lòng điền đầy đủ thông tin!")

def login():
    st.subheader("Đăng Nhập")
    email = sanitize_input(st.text_input("Email"))
    password = st.text_input("Mật khẩu", type="password")

    if st.button("Đăng Nhập"):
        user = db.users.find_one({"email": email}, {"_id": 1, "password": 1, "full_name": 1, "role": 1})
        if user:
            decrypted_password = decrypt_data(user['password'])
            if bcrypt.checkpw(password.encode('utf-8'), decrypted_password.encode('utf-8')):
                st.success(f"Chào mừng {user['full_name']}!")
                return user
            else:
                st.error("Email hoặc mật khẩu không đúng!")
                return None
        else:
            st.error("Email hoặc mật khẩu không đúng!")
            return None