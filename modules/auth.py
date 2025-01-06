import streamlit as st
from config import db
import bcrypt
from utils import sanitize_input
import datetime
import time
import pyotp
import qrcode
import io
from PIL import Image

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

def generate_2fa_secret():
    """Tạo secret key cho 2FA."""
    return pyotp.random_base32()

def generate_2fa_qr_code(secret, user_email):
    """Tạo mã QR code cho 2FA."""
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user_email, issuer_name="Rental System")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to Streamlit-compatible image
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return buffered

def verify_2fa(secret, token):
    """Xác thực mã 2FA."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token)

def update_user_info(user):
    st.subheader("Cập Nhật Thông Tin Cá Nhân")

    # Lấy thông tin người dùng từ database
    user_data = db.users.find_one({"_id": user["_id"]})

    if user_data:
        # Form cho phép người dùng chỉnh sửa thông tin
        with st.form(key='update_form'):
            full_name = st.text_input("Họ và Tên", value=user_data['full_name'])
            email = st.text_input("Email", value=user_data['email'])
            phone = st.text_input("Số Điện Thoại", value=user_data['phone'])
            address = st.text_input("Địa chỉ", value=user_data['address'] if 'address' in user_data else "")
            
            # Hiển thị thông tin bằng lái nếu có
            if 'driver_license' in user_data and user_data['driver_license']:
                license_type = st.selectbox("Hạng bằng lái", ["A1", "A2", "B1", "B2", "C", "D", "E", "F"], index=["A1", "A2", "B1", "B2", "C", "D", "E", "F"].index(user_data['driver_license']['type']) if user_data['driver_license']['type'] else 0)
                license_expiry = st.date_input("Ngày hết hạn bằng lái", value=datetime.datetime.strptime(user_data['driver_license']['expiry_date'], "%Y-%m-%d").date())
            else:
                license_type = st.selectbox("Hạng bằng lái", ["A1", "A2", "B1", "B2", "C", "D", "E", "F"])
                license_expiry = st.date_input("Ngày hết hạn bằng lái")

            # Xử lý 2FA
            if '2fa_enabled' not in user_data:
                user_data['2fa_enabled'] = False

            # Sử dụng session state để lưu trạng thái kích hoạt 2FA
            if '2fa_enabled' not in st.session_state:
                st.session_state['2fa_enabled'] = user_data['2fa_enabled']

            two_fa_enabled = st.checkbox("Kích hoạt 2FA", value=st.session_state['2fa_enabled'])

            # Nếu người dùng thay đổi trạng thái 2FA
            if two_fa_enabled != st.session_state['2fa_enabled']:
                st.session_state['2fa_enabled'] = two_fa_enabled
                st.session_state['2fa_show_qr'] = True
                st.session_state['2fa_secret_temp'] = generate_2fa_secret()
                # st.rerun()

            # Nếu trạng thái là đã bật và đã lưu secret key
            if two_fa_enabled and '2fa_secret' in user_data:
                st.write("2FA đã được kích hoạt.")
            
            update_button = st.form_submit_button(label="Cập Nhật Thông Tin")

        # Hiển thị QR code và yêu cầu người dùng quét (ngoài form)
        if '2fa_show_qr' in st.session_state and st.session_state['2fa_show_qr']:
            qr_code = generate_2fa_qr_code(st.session_state['2fa_secret_temp'], email)
            st.image(qr_code)
            st.write("Quét mã QR code bằng ứng dụng Authenticator và nhấn nút bên dưới để xác nhận.")
            update_button = False
            if st.button("Đã quét mã QR"):
                # Lưu 2fa_secret vào user_data tạm thời
                user_data['2fa_secret'] = st.session_state['2fa_secret_temp']
                st.session_state['2fa_show_qr'] = False
                st.success("Đã lưu thông tin 2FA.")
                update_button = True
                # st.rerun()

        if update_button:
            # Cập nhật thông tin người dùng trong database
            updated_data = {
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "address": address,
                "driver_license": {
                    "type": license_type,
                    "expiry_date": license_expiry.isoformat()
                },
                "2fa_enabled": st.session_state['2fa_enabled']
            }

            # Chỉ cập nhật secret key nếu người dùng đã bật 2FA và secret key tồn tại trong user_data
            if '2fa_secret' in user_data:
                updated_data["2fa_secret"] = encrypt_data(user_data['2fa_secret'])

            db.users.update_one({"_id": user_data['_id']}, {"$set": updated_data})
            st.success("Thông tin cá nhân đã được cập nhật.")
            st.rerun()
    else:
        st.error("Không tìm thấy thông tin người dùng.")

def login():
    st.subheader("Đăng Nhập")
    email = sanitize_input(st.text_input("Email"))
    password = st.text_input("Mật khẩu", type="password")

    if st.button("Đăng Nhập"):
        user = db.users.find_one({"email": email}, {"_id": 1, "password": 1, "full_name": 1, "role": 1, "2fa_enabled": 1, "2fa_secret": 1})
        if user:
            decrypted_password = decrypt_data(user['password'])
            if bcrypt.checkpw(password.encode('utf-8'), decrypted_password.encode('utf-8')):
                # Check if 2FA is enabled
                if user.get("2fa_enabled") and user.get("2fa_secret"):
                    st.session_state['2fa_required'] = True
                    st.session_state['2fa_user_id'] = str(user["_id"])
                    st.session_state['2fa_secret'] = user["2fa_secret"]  # Store the secret for later verification
                    st.experimental_rerun()  # Refresh the page to show 2FA input
                else:
                    st.success(f"Chào mừng {user['full_name']}!")
                    return user
            else:
                st.error("Email hoặc mật khẩu không đúng!")
                return None
        else:
            st.error("Email hoặc mật khẩu không đúng!")
            return None

# Xử lý 2FA (nếu đã bật)
# def two_factor_authentication(user_id, secret):
#     st.subheader("Xác Thực 2FA")

#     # Tạo widget text_input và nút bấm một lần duy nhất
#     if "otp_token" not in st.session_state:
#         st.session_state["otp_token"] = ""  # Giá trị mặc định cho OTP
#     if "otp_verified" not in st.session_state:
#         st.session_state["otp_verified"] = False

#     # Hiển thị widget bên ngoài vòng lặp
#     token = st.text_input(
#         "Nhập mã từ ứng dụng Authenticator",
#         type="password",
#         key="2fa_token_input",
#         value=st.session_state["otp_token"],  # Hiển thị giá trị đã lưu
#         on_change=lambda: st.session_state.update(otp_verified=False)  # Đặt lại trạng thái khi thay đổi mã
#     )

#     # Nút xác thực
#     if st.button("Xác thực", key="2fa_confirm_button"):
#         if verify_2fa(decrypt_data(secret), token):
#             st.session_state["otp_verified"] = True  # Cập nhật trạng thái xác thực thành công
#             st.success("Xác thực thành công!")
#         else:
#             st.session_state["otp_verified"] = False
#             st.error("Mã xác thực không đúng. Vui lòng thử lại.")

#     # Kiểm tra trạng thái xác thực trong vòng lặp
#     while '2fa_required' in st.session_state:
#         if st.session_state["otp_verified"]:
#             # Xóa các session state liên quan đến 2FA
#             del st.session_state['2fa_required']
#             del st.session_state['otp_token']

#             # Tìm và trả về user object từ database
#             user = db.users.find_one({"_id": user_id})
#             if user:
#                 return user
#             else:
#                 st.error("Không tìm thấy thông tin người dùng.")
#                 return None

#         time.sleep(1)  # Tạm dừng để tránh vòng lặp quá nhanh