Collecting workspace information

# Hệ Thống Quản Lý Cho Thuê Xe

## Giới Thiệu

Dự án này là một hệ thống quản lý cho thuê xe trực tuyến, cho phép người dùng tìm kiếm, đặt xe và quản lý các đơn đặt xe. Hệ thống cũng cung cấp các chức năng quản lý cho admin như quản lý xe, đơn đặt hàng và thống kê.

## Cấu Trúc Dự Án

```
__pycache__/
.env
.streamlit/
	secrets.toml
.vscode/
	launch.json
config.py
local_storage.py
main.py
models/
	booking_model.py
	payment_model.py
	user_model.py
	vehicle_model.py
modules/
	__pycache__/
	admin.py
	auth.py
	booking.py
	customer.py
	payment.py
	test_Temp.py
	vehicle.py
requirements.txt
system.log
templates/
	codeSendMail.txt
	email_template.html
test_payment.py
test_vehicle.py
utils.py
```

## Cài Đặt

1. Clone repository:
    ```sh
    git clone <repository-url>
    cd <repository-directory>
    ```

2. Tạo và kích hoạt virtual environment:
    ```sh
    python -m venv venv
    source venv/bin/activate  # Trên Windows: venv\Scripts\activate
    ```

3. Cài đặt các gói phụ thuộc:
    ```sh
    pip install -r requirements.txt
    ```

4. Tạo file 

.env

 và cấu hình các biến môi trường:
    ```env
    MONGODB_CONNECTION_STRING=<your_mongodb_connection_string>
    STRIPE_API_KEY=<your_stripe_api_key>
    VNPAY_TMN_CODE=<your_vnpay_tmn_code>
    VNPAY_HASH_SECRET=<your_vnpay_hash_secret>
    SECRET_KEY=<your_secret_key>
    FERNET_KEY=<your_fernet_key>
    COOKIE_PASSWORD=<your_cookie_password>
    ```

## Chạy Ứng Dụng

1. Khởi động ứng dụng:
    ```sh
    streamlit run main.py
    ```

2. Truy cập ứng dụng tại `http://localhost:8501`.

## Các Chức Năng Chính

### Người Dùng

- **Đăng Ký/Đăng Nhập**: Người dùng có thể đăng ký tài khoản mới hoặc đăng nhập vào hệ thống.
- **Tìm Kiếm Xe**: Tìm kiếm xe theo thương hiệu và giá thuê.
- **Đặt Xe**: Đặt xe và thanh toán trực tuyến.
- **Trả Xe**: Trả xe sau khi sử dụng.

### Admin

- **Quản Lý Xe**: Thêm, sửa, xóa thông tin xe.
- **Quản Lý Đơn Đặt Hàng**: Quản lý các đơn đặt hàng của người dùng.
- **Thống Kê**: Xem thống kê về số lượng đơn đặt hàng, doanh thu, số lượng khách hàng và xe.

## Cấu Hình

- **MongoDB**: Sử dụng MongoDB để lưu trữ dữ liệu.
- **Streamlit**: Sử dụng Streamlit để xây dựng giao diện người dùng.
- **JWT**: Sử dụng JSON Web Token (JWT) để xác thực người dùng.
- **Bcrypt**: Sử dụng Bcrypt để mã hóa mật khẩu.
- **Fernet**: Sử dụng Fernet để mã hóa dữ liệu nhạy cảm.

## Ghi Chú

- Đảm bảo MongoDB đang chạy và có thể kết nối được.
- Kiểm tra file 

system.log

 để xem các log chi tiết và xử lý lỗi nếu có.

## Đóng Góp

Nếu bạn muốn đóng góp cho dự án, vui lòng tạo pull request hoặc mở issue mới trên GitHub.

## Giấy Phép

Dự án này được cấp phép theo giấy phép MIT. Vui lòng xem file LICENSE để biết thêm chi tiết.
