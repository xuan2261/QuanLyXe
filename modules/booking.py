import time
import streamlit as st
from config import db
import hashlib
import urllib.parse
from bson.objectid import ObjectId
import datetime
import logging
import os

logger = logging.getLogger(__name__)

# Hàm kiểm tra tình trạng xe (đã thuê hay chưa)
def check_vehicle_availability(vehicle_id, start_date, end_date):
    """Kiểm tra xem xe có sẵn sàng trong khoảng thời gian đã cho hay không."""
    # Lấy danh sách các booking hiện có của xe.
    # Không tính các đơn có trạng thái đã hủy (cancelled) hoặc đã hoàn thành (completed).
    existing_bookings = db.bookings.find({
        "vehicle_id": vehicle_id,
        "status": {"$nin": ["cancelled", "completed"]}
    })

    for booking in existing_bookings:
        booking_start = datetime.datetime.strptime(booking["start_date"], "%Y-%m-%d").date()
        booking_end = datetime.datetime.strptime(booking["end_date"], "%Y-%m-%d").date()

        # Kiểm tra xem khoảng thời gian mới có trùng với booking hiện có hay không
        if start_date <= booking_end and end_date >= booking_start:
            return False  # Xe không khả dụng

    return True  # Xe khả dụng

# Hàm xử lý thanh toán giả lập (Mock Payment)
def process_mock_payment(user, total_amount, booking_id):
    st.write(f"Thanh toán giả lập cho khách hàng {user['full_name']}")
    st.write(f"Tổng số tiền thanh toán: {total_amount} USD")

    # Tạo form riêng cho thanh toán giả lập
    with st.form(key="payment_form"):
        card_number = st.text_input("Số thẻ (16 số)", max_chars=16, type="password")
        card_holder = st.text_input("Tên chủ thẻ")
        expiry_date = st.text_input("Ngày hết hạn (YYYY-MM-DD)")
        submit_payment = st.form_submit_button("Xác Nhận Thanh Toán")

        if submit_payment:
            from modules.payment import process_simulated_payment
            payment_result = process_simulated_payment(card_number, total_amount, booking_id)

            if payment_result["status"] == "success":
                st.success(payment_result["message"])
                st.write("Trạng thái đơn hàng đã được cập nhật.")
                # Cập nhật trạng thái xe khi đã thanh toán
                booking = db.bookings.find_one({"_id": booking_id})
                if booking:
                    db.vehicles.update_one({"_id": booking["vehicle_id"]}, {"$set": {"status": "rented"}})

                time.sleep(2)
                # Ẩn form thanh toán sau khi thanh toán thành công
                st.session_state['show_payment_form'] = False
                # Xóa các thông tin liên quan đến đơn hàng hiện tại
                del st.session_state['current_booking_id']
                del st.session_state['total_price']
                del st.session_state['booking_user']
                
                st.rerun()
            else:
                st.error(payment_result["message"])

def bookings(user):
    list_user_bookings(user)  # Hiển thị danh sách xe đã thuê
    create_booking(user)  # Tạo đơn đặt xe mới

def _get_vehicle_details(selected_vehicle):
    """Lấy thông tin chi tiết của xe được chọn."""
    vehicles_list = list(db.vehicles.find())
    vehicle = next((v for v in vehicles_list if f"{v['brand']} {v['model']} - Biển số: {v['license_plate']} - Giá: {v['price_per_day']} USD/ngày - Năm: {v['year']} - Yêu cầu hạng bằng lái: {v['required_license_type']}" == selected_vehicle), None)
    return vehicle

def _calculate_total_price(start_date, end_date, price_per_day):
    """Tính tổng giá tiền thuê xe."""
    total_days = (end_date - start_date).days + 1
    total_price = total_days * price_per_day
    return total_price

def _save_booking_to_db(user, vehicle_id, start_date, end_date, total_price):
    """Lưu thông tin booking vào MongoDB."""
    booking_data = {
        "user_id": user["_id"],
        "vehicle_id": vehicle_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_price": total_price,
        "payment_status": "pending",
        "status": "pending",
        "created_at": datetime.datetime.now()
    }
    booking_id = db.bookings.insert_one(booking_data).inserted_id
    return booking_id

# Define a mapping of license types to numerical values for comparison
LICENSE_HIERARCHY = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C": 5,
    "D": 6,
    "E": 7,
    "F": 8
}

# Hàm tạo booking và xử lý thanh toán
def create_booking(user):
    st.header("Đặt Xe")
    # Lấy danh sách xe từ db, xử lý lỗi nếu không kết nối được mongodb
    try:
        vehicles_list = list(db.vehicles.find())
    except Exception as e:
        st.error("Không thể kết nối tới cơ sở dữ liệu. Vui lòng thử lại sau!")
        logger.error(f"Lỗi khi kết nối tới cơ sở dữ liệu: {e}")
        return
    
    vehicles = [
        f"{vehicle['brand']} {vehicle['model']} - Biển số: {vehicle['license_plate']} - Giá: {vehicle['price_per_day']} USD/ngày - Năm: {vehicle['year']} - Yêu cầu hạng bằng lái: {vehicle['required_license_type']}"
        for vehicle in vehicles_list
    ]

    with st.form(key="booking_form"):
        selected_vehicle = st.selectbox("Chọn Xe", vehicles)
        start_date = st.date_input("Ngày Bắt Đầu", datetime.date.today())
        end_date = st.date_input("Ngày Kết Thúc", datetime.date.today())
        submit_booking = st.form_submit_button("Xác Nhận Đặt")

    if submit_booking:
        if start_date > end_date:
            st.error("Ngày kết thúc không được trước ngày bắt đầu.")
            return

        vehicle = _get_vehicle_details(selected_vehicle)
        if not vehicle:
            st.error("Không tìm thấy xe đã chọn. Vui lòng thử lại.")
            return
        
        # Kiểm tra hạng bằng lái
        user_license_type = user.get("driver_license", {}).get("type")
        required_license_type = vehicle.get("required_license_type")

        if user_license_type and required_license_type:
            if LICENSE_HIERARCHY.get(user_license_type, 0) < LICENSE_HIERARCHY.get(required_license_type, 0):
                st.error("Hạng bằng lái của bạn không đủ điều kiện để thuê xe này.")
                return

        if not check_vehicle_availability(vehicle["_id"], start_date, end_date):
            st.error("Xe đã được thuê trong khoảng thời gian này. Vui lòng chọn xe hoặc thời gian khác.")
            return

        total_price = _calculate_total_price(start_date, end_date, vehicle["price_per_day"])
        st.write(f"Tổng giá tiền: {total_price} USD")

        # Lưu thông tin booking vào MongoDB
        booking_id = _save_booking_to_db(user, vehicle["_id"], start_date, end_date, total_price)
        st.success("Đặt xe thành công! Đang ở trạng thái chờ, hãy tiến hành thanh toán!")

        # Lưu booking_id vào session_state dưới dạng ObjectId
        st.session_state['current_booking_id'] = booking_id
        st.session_state['total_price'] = total_price
        st.session_state['booking_user'] = user

        # Bắt đầu hiển thị form thanh toán
        st.session_state['show_payment_form'] = True

    # Hiển thị form thanh toán nếu đã có thông tin booking trong session_state và show_payment_form là True
    if st.session_state.get('show_payment_form', False):
        st.subheader("Thanh Toán")
        payment_method = st.radio("Chọn phương thức thanh toán", ["Thanh Toán Giả Lập"])

        if payment_method == "Thanh Toán Giả Lập":
            process_mock_payment(st.session_state['booking_user'], st.session_state['total_price'], st.session_state['current_booking_id'])

# Hàm cập nhật trạng thái thanh toán
def update_payment_status(booking_id, status):
    logger.info(f"Cập nhật trạng thái thanh toán cho booking_id: {booking_id} thành {status}")
    result = db.bookings.update_one({"_id": booking_id}, {"$set": {"payment_status": status}})
    if result.modified_count == 1:
        logger.info(f"Cập nhật thành công.")
    else:
        logger.warning(f"Không tìm thấy đơn đặt xe với booking_id này.")

# Hàm hiển thị danh sách xe đã thuê
def list_user_bookings(user):
    st.subheader("Các xe đã thuê")
    bookings = db.bookings.find({"user_id": user["_id"]})
    if not bookings:
        st.write("Bạn chưa thuê xe nào.")
    else:
        for booking in bookings:
            try:
                vehicle = db.vehicles.find_one({"_id": booking["vehicle_id"]})
                if vehicle:
                    # Tạo các cột để hiển thị thông tin và nút
                    col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1, 1]) # Chia thành 5 cột

                    with col1:
                        st.write(f"Xe: {vehicle['brand']} {vehicle['model']} - Biển số: {vehicle['license_plate']} -  Từ: {booking['start_date']} đến {booking['end_date']} - Trạng thái đơn hàng: {booking['status']} - Trạng thái thanh toán: {booking['payment_status']}")
                    
                    # Khởi tạo giá trị của st.session_state nếu chưa có
                    if f"extend_{booking['_id']}_active" not in st.session_state:
                        st.session_state[f"extend_{booking['_id']}_active"] = False
                    if f"cancel_{booking['_id']}_active" not in st.session_state:
                        st.session_state[f"cancel_{booking['_id']}_active"] = False
                    
                    with col2:
                        if is_booking_expired(booking) or booking["status"] in ["cancelled", "completed"]:
                            if st.button(f"Thuê lại", key=f"rent_again_{booking['_id']}"):
                                st.session_state[f"extend_{booking['_id']}_active"] = False  # Reset trạng thái gia hạn
                                st.session_state[f"rent_again_{booking['_id']}_active"] = True
                                st.rerun()
                        else:
                            if st.button(f"Gia hạn", key=f"extend_{booking['_id']}"):
                                st.session_state[f"rent_again_{booking['_id']}_active"] = False # Reset trạng thái thuê lại
                                st.session_state[f"extend_{booking['_id']}_active"] = True
                                st.rerun()

                    with col3:
                        # Nút hủy đơn hàng
                        # Chỉ hiển thị nếu đơn hàng ở trạng thái 'pending'
                        if booking["status"] == "pending":
                            if st.button(f"Hủy đơn", key=f"cancel_{booking['_id']}"):
                                # Cập nhật trạng thái đơn hàng thành "cancelled"
                                db.bookings.update_one({"_id": booking["_id"]}, {"$set": {"status": "cancelled"}})
                                # Cập nhật lại trạng thái của xe
                                db.vehicles.update_one({"_id": vehicle["_id"]}, {"$set": {"status": "available"}})
                                st.success(f"Đơn hàng {booking['_id']} đã được hủy.")
                                st.rerun()

                    with col4:
                        # Nút xem chi tiết
                        if st.button("Chi tiết", key=f"detail_{booking['_id']}"):
                            # Lưu thông tin chi tiết đơn hàng vào session_state
                            st.session_state['booking_details'] = {
                                "ID Đơn": str(booking["_id"]),
                                "Khách Hàng": user['full_name'],
                                "Email": user["email"],
                                "Xe": f"{vehicle['brand']} {vehicle['model']} - Biển số: {vehicle['license_plate']}",
                                "Thời Gian Thuê": f"Từ {booking['start_date']} đến {booking['end_date']}",
                                "Số Ngày Thuê": str((datetime.datetime.strptime(booking['end_date'], "%Y-%m-%d").date() - datetime.datetime.strptime(booking['start_date'], "%Y-%m-%d").date()).days + 1),
                                "Tổng Giá (USD)": f"{booking['total_price']} USD",
                                "Trạng Thái Thanh Toán": booking["payment_status"],
                                "Trạng Thái Đơn Hàng": booking["status"]
                            }
                            st.session_state['show_details'] = True
                            st.rerun()
                    
                    # Hiển thị thông tin chi tiết đơn hàng (nếu có)
                    if 'booking_details' in st.session_state and st.session_state.get('show_details', False) == True:
                        st.subheader("Thông Tin Chi Tiết Đơn Hàng")
                        for key, value in st.session_state['booking_details'].items():
                            st.write(f"**{key}:** {value}")
                        if st.button("Đóng"):
                            del st.session_state['booking_details']
                            st.session_state['show_details'] = False
                            st.rerun()

                    if st.session_state.get(f"rent_again_{booking['_id']}_active", False):
                        create_booking(user)
                        # st.session_state[f"rent_again_{booking['_id']}_active"] = False

                    if st.session_state.get(f"extend_{booking['_id']}_active", False):
                        new_end_date = st.date_input("Chọn ngày gia hạn", key=f"date_{booking['_id']}")
                        if new_end_date > datetime.datetime.strptime(booking["end_date"], "%Y-%m-%d").date():
                            if st.button("Xác nhận gia hạn", key=f"confirm_{booking['_id']}"):
                                # Tính toán số ngày mới gia hạn
                                old_end_date = datetime.datetime.strptime(booking["end_date"], "%Y-%m-%d").date()
                                days_extended = (new_end_date - old_end_date).days
                                total_price = days_extended * vehicle['price_per_day']

                                # Cập nhật ngày kết thúc và tổng giá mới
                                result = db.bookings.update_one(
                                    {"_id": booking["_id"]},
                                    {"$set": {
                                        "end_date": new_end_date.isoformat(),
                                        "total_price": booking['total_price'] + total_price,
                                        "payment_status": "pending",  # Cập nhật lại trạng thái thanh toán
                                        "status": "pending"  # Cập nhật lại trạng thái đơn hàng
                                    }}
                                )

                                if result.modified_count == 1:
                                    st.success(f"Đã gia hạn đơn hàng đến ngày {new_end_date.isoformat()}. Vui lòng thanh toán {total_price} USD.")
                                    # Xử lý thanh toán cho gia hạn
                                    st.session_state['current_booking_id'] = booking["_id"]
                                    payment_method = st.radio("Chọn phương thức thanh toán", ["Thanh Toán Giả Lập"])
                                    if payment_method == "Thanh Toán Giả Lập":
                                        process_mock_payment(user, total_price, booking["_id"])
                                    # Cập nhật lại trạng thái sau khi xử lý thanh toán
                                    st.session_state[f"extend_{booking['_id']}_active"] = False
                                    st.rerun()
                                else:
                                    st.error("Có lỗi xảy ra khi gia hạn đơn hàng.")
                        else:
                            st.error("Ngày kết thúc mới phải sau ngày kết thúc hiện tại.")
                else:
                    st.error("Không tìm thấy thông tin xe.")
            except Exception as e:
                st.error(f"Lỗi: {e}")
                logger.error(f"Lỗi: {e}")

# Hàm kiểm tra nếu đơn đặt xe đã hết hạn
def is_booking_expired(booking):
    return datetime.datetime.strptime(booking["end_date"], "%Y-%m-%d").date() < datetime.date.today()

def manage_bookings():
    st.subheader("Quản Lý Đơn Đặt Xe")

    # Thêm trường tìm kiếm
    search_term = st.text_input("Tìm kiếm đơn đặt xe (theo tên khách hàng, email, biển số, nhãn hiệu xe, mẫu xe, hoặc trạng thái thanh toán)")

    # Lấy tất cả các booking từ cơ sở dữ liệu
    bookings = list(db.bookings.find({}))

    # Nếu không có đơn đặt xe
    if len(bookings) == 0:
        st.write("Hiện tại chưa có đơn đặt xe nào.")
    else:
        # Lọc danh sách bookings dựa trên search_term
        filtered_bookings = []
        for booking in bookings:
            vehicle = db.vehicles.find_one({"_id": booking["vehicle_id"]})
            customer = db.users.find_one({"_id": booking["user_id"]})

            # Kiểm tra nếu thông tin khớp với search_term
            if (
                search_term.lower() in customer["full_name"].lower() or
                search_term.lower() in customer["email"].lower() or
                search_term.lower() in vehicle["license_plate"].lower() or
                search_term.lower() in vehicle["brand"].lower() or
                search_term.lower() in vehicle["model"].lower() or
                search_term.lower() in booking["payment_status"].lower()
            ):
                filtered_bookings.append(booking)

        # Nếu không có đơn đặt xe khớp với tìm kiếm
        if len(filtered_bookings) == 0:
            st.write("Không tìm thấy đơn đặt xe nào phù hợp.")
            return

        # CSS để làm cho bảng đồng nhất và dễ nhìn hơn
        st.markdown("""
        <style>
        .st-column {border: 1px solid #ddd; padding: 8px;}
        .st-header {background-color: #333; color: white; font-weight: bold; text-align: center;}
        </style>
        """, unsafe_allow_html=True)

        # Tạo cột tiêu đề bằng cách sử dụng st.columns
        col1, col2, col3, col4, col5, col6, col7, col8, col9, col10 = st.columns([0.8, 1.5, 1.5, 1.5, 1.5, 1, 1.5, 1.5, 1, 1]) # Thêm cột mới
        col1.markdown('<div class="st-header">ID Đơn</div>', unsafe_allow_html=True)
        col2.markdown('<div class="st-header">Khách Hàng</div>', unsafe_allow_html=True)
        col3.markdown('<div class="st-header">Email</div>', unsafe_allow_html=True)
        col4.markdown('<div class="st-header">Xe</div>', unsafe_allow_html=True)
        col5.markdown('<div class="st-header">Thời Gian Thuê</div>', unsafe_allow_html=True)
        col6.markdown('<div class="st-header">Số Ngày Thuê</div>', unsafe_allow_html=True)
        col7.markdown('<div class="st-header">Tổng Giá (USD)</div>', unsafe_allow_html=True)
        col8.markdown('<div class="st-header">Trạng Thái Thanh Toán</div>', unsafe_allow_html=True)
        col9.markdown('<div class="st-header">Trạng thái đơn</div>', unsafe_allow_html=True)
        col10.markdown('<div class="st-header"></div>', unsafe_allow_html=True)  # Cột cho nút "Chỉnh Sửa"

        # Hiển thị từng dòng dữ liệu trong bảng
        for index, booking in enumerate(filtered_bookings):
            vehicle = db.vehicles.find_one({"_id": booking["vehicle_id"]})
            customer = db.users.find_one({"_id": booking["user_id"]})

            start_date = datetime.datetime.strptime(booking['start_date'], "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(booking['end_date'], "%Y-%m-%d").date()
            total_days = (end_date - start_date).days + 1

            # Tạo các cột cho từng dòng dữ liệu
            col1, col2, col3, col4, col5, col6, col7, col8, col9, col10 = st.columns([0.8, 1.5, 1.5, 1.5, 1.5, 1, 1.5, 1.5, 1, 1]) # Thêm cột mới
            col1.write(str(booking["_id"]))
            col2.write(customer["full_name"])
            col3.write(customer["email"])
            col4.write(f"{vehicle['brand']} {vehicle['model']} - Biển số: {vehicle['license_plate']}")
            col5.write(f"Từ {booking['start_date']} đến {booking['end_date']}")
            col6.write(str(total_days))
            col7.write(f"{booking['total_price']} USD")
            col8.write(booking["payment_status"])
            col9.write(booking["status"])

            # Nút chỉnh sửa nằm ở cột cuối cùng
            # Nếu chưa thanh toán, cho phép chỉnh sửa
            if booking['payment_status'] != 'paid' or booking['status'] != 'completed':
                if col10.button("Chỉnh Sửa", key=f"edit_{index}"):
                    st.session_state['editing_booking_id'] = str(booking["_id"])
            else:
                # Nếu đã thanh toán và hoàn thành, không hiển thị nút "Chỉnh Sửa"
                col10.markdown('<div style="text-align: center;">(Đã hoàn thành)</div>', unsafe_allow_html=True)
            
            # Nút xem chi tiết đơn hàng
            if col10.button("Chi tiết", key=f"detail_{index}"):
                # Lưu thông tin chi tiết đơn hàng vào session_state
                st.session_state['booking_details'] = {
                    "ID Đơn": str(booking["_id"]),
                    "Khách Hàng": customer["full_name"],
                    "Email": customer["email"],
                    "Xe": f"{vehicle['brand']} {vehicle['model']} - Biển số: {vehicle['license_plate']}",
                    "Thời Gian Thuê": f"Từ {booking['start_date']} đến {booking['end_date']}",
                    "Số Ngày Thuê": str(total_days),
                    "Tổng Giá (USD)": f"{booking['total_price']} USD",
                    "Trạng Thái Thanh Toán": booking["payment_status"],
                    "Trạng Thái Đơn Hàng": booking["status"]
                }

        # Hiển thị thông tin chi tiết đơn hàng (nếu có)
        if 'booking_details' in st.session_state:
            st.subheader("Thông Tin Chi Tiết Đơn Hàng")
            for key, value in st.session_state['booking_details'].items():
                st.write(f"**{key}:** {value}")
            if st.button("Đóng"):
                del st.session_state['booking_details']

        # Nếu có booking đang được chỉnh sửa, hiển thị form chỉnh sửa
        editing_booking_id = st.session_state.get('editing_booking_id', None)
        if editing_booking_id:
            booking_to_edit = db.bookings.find_one({"_id": ObjectId(editing_booking_id)})
            if booking_to_edit:
                edit_booking(booking_to_edit)
            else:
                st.error("Không tìm thấy đơn đặt xe để chỉnh sửa.")
                st.session_state['editing_booking_id'] = None

# Hàm để chỉnh sửa booking
def edit_booking(booking):
    st.subheader("Chỉnh Sửa Đơn Đặt Xe")
    # Lấy thông tin cần thiết
    vehicle = db.vehicles.find_one({"_id": booking["vehicle_id"]})
    customer = db.users.find_one({"_id": booking["user_id"]})

    # Hiển thị thông tin hiện tại và cho phép chỉnh sửa
    with st.form(key=f"edit_form_{booking['_id']}"):
        start_date = st.date_input("Ngày Bắt Đầu", datetime.datetime.strptime(booking['start_date'], "%Y-%m-%d").date())
        end_date = st.date_input("Ngày Kết Thúc", datetime.datetime.strptime(booking['end_date'], "%Y-%m-%d").date())
        payment_status = st.selectbox("Trạng Thái Thanh Toán", ["pending", "paid", "failed", "refunded"], index=["pending", "paid", "failed", "refunded"].index(booking["payment_status"]))
        booking_status = st.selectbox("Trạng Thái Đơn Hàng", ["pending", "confirmed", "cancelled", "completed"], index=["pending", "confirmed", "cancelled", "completed"].index(booking["status"]))
        submit_button = st.form_submit_button(label="Cập Nhật")

    if submit_button:
        if start_date > end_date:
            st.error("Ngày kết thúc không được trước ngày bắt đầu.")
            return

        # Tính toán lại số ngày thuê và tổng giá
        total_days = (end_date - start_date).days + 1
        total_price = total_days * vehicle["price_per_day"]

        # Chuyển đổi start_date và end_date thành chuỗi ISO
        start_date_iso = start_date.isoformat()
        end_date_iso = end_date.isoformat()

        # Đảm bảo booking["_id"] là ObjectId
        booking_id = booking["_id"]
        if not isinstance(booking_id, ObjectId):
            booking_id = ObjectId(booking_id)

        # Cập nhật thông tin booking trong cơ sở dữ liệu
        result = db.bookings.update_one(
            {"_id": booking_id},
            {"$set": {
                "start_date": start_date_iso,
                "end_date": end_date_iso,
                "total_price": total_price,
                "payment_status": payment_status,
                "status": booking_status
            }}
        )

        if result.modified_count > 0:
            st.success("Cập nhật đơn đặt xe thành công!")
            # Xóa trạng thái chỉnh sửa
            st.session_state['editing_booking_id'] = None
            st.rerun()
        else:
            st.error("Cập nhật thất bại. Vui lòng kiểm tra lại.")

def check_booking_status(booking_id):
    """
    Kiểm tra trạng thái của đơn hàng.
    Trả về True nếu đơn hàng đã thanh toán và đang được thuê, ngược lại trả về False.
    """
    booking = db.bookings.find_one({"_id": booking_id})
    if booking and booking["payment_status"] == "paid" and booking["status"] == "confirmed":
        return True
    return False

def update_booking_status(booking_id, status):
    """Cập nhật trạng thái của đơn hàng."""
    result = db.bookings.update_one({"_id": booking_id}, {"$set": {"status": status}})
    return result.modified_count > 0

def update_vehicle_status(vehicle_id, status):
    """Cập nhật trạng thái của xe."""
    result = db.vehicles.update_one({"_id": vehicle_id}, {"$set": {"status": status}})
    return result.modified_count > 0

def return_vehicle(user):
    st.subheader("Trả xe")
    active_bookings = list(db.bookings.find({"user_id": user["_id"], "status": "confirmed", "payment_status": "paid"}))

    if not active_bookings:
        st.write("Bạn không có đơn hàng nào đang được thuê.")
        return

    for booking in active_bookings:
        vehicle = db.vehicles.find_one({"_id": booking["vehicle_id"]})
        if vehicle:
            st.write(f"Xe: {vehicle['brand']} {vehicle['model']} - Biển số: {vehicle['license_plate']}")
            if st.button("Trả Xe", key=f"return_{booking['_id']}"):
                
                # Cập nhật trạng thái đơn hàng
                if update_booking_status(booking["_id"], "completed"):
                    # Cập nhật trạng thái xe
                    vehicle_id = booking["vehicle_id"]
                    if not isinstance(vehicle_id, ObjectId):
                        vehicle_id = ObjectId(vehicle_id)
                    if update_vehicle_status(vehicle_id, "available"):
                        st.success(f"Trả xe {vehicle['brand']} {vehicle['model']} thành công!")
                        st.rerun()
                    else:
                        st.error("Có lỗi xảy ra khi cập nhật trạng thái xe.")
                else:
                    st.error("Có lỗi xảy ra khi cập nhật trạng thái đơn hàng.")
        else:
            st.error("Không tìm thấy thông tin xe.")