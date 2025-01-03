import streamlit as st
from config import db
from pymongo.errors import ServerSelectionTimeoutError, DuplicateKeyError
import pymongo
from bson import ObjectId
import os
import json
import logging
import datetime
from utils import sanitize_input

logger = logging.getLogger(__name__)

# Serialize ObjectId and datetime for JSON
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

def initialize_vehicle_data():
    """Khởi tạo một số loại xe nếu chưa có dữ liệu."""
    try:
        if db.vehicles.count_documents({}) == 0:
            st.info("Khởi tạo dữ liệu xe trong MongoDB...")
            sample_vehicles = [
                {
                    "brand": "Toyota",
                    "model": "Camry",
                    "license_plate": "ABC123",
                    "price_per_day": 50,
                    "status": "available",
                    "year": 2020,
                    "created_at": datetime.datetime.now(),
                    "image": "",
                    "required_license_type": "B1"
                },
                {
                    "brand": "Ford",
                    "model": "Mustang",
                    "license_plate": "DEF456",
                    "price_per_day": 100,
                    "status": "available",
                    "year": 2021,
                    "created_at": datetime.datetime.now(),
                    "image": "",
                    "required_license_type": "B2"
                },
                {
                    "brand": "Honda",
                    "model": "Civic",
                    "license_plate": "GHI789",
                    "price_per_day": 40,
                    "status": "available",
                    "year": 2019,
                    "created_at": datetime.datetime.now(),
                    "image": "",
                    "required_license_type": "A1"
                },
                {
                    "brand": "BMW",
                    "model": "X5",
                    "license_plate": "JKL012",
                    "price_per_day": 150,
                    "status": "available",
                    "year": 2022,
                    "created_at": datetime.datetime.now(),
                    "image": "",
                    "required_license_type": "C"
                },
                {
                    "brand": "Tesla",
                    "model": "Model 3",
                    "license_plate": "MNO345",
                    "price_per_day": 120,
                    "status": "available",
                    "year": 2023,
                    "created_at": datetime.datetime.now(),
                    "image": "",
                    "required_license_type": "B2"
                }
            ]
            db.vehicles.insert_many(sample_vehicles)
            st.success("Khởi tạo dữ liệu xe thành công!")
        # else:
            # st.info("Dữ liệu xe đã tồn tại.")

        # Tạo index duy nhất cho trường license_plate để đảm bảo không có biển số trùng
        db.vehicles.create_index([("license_plate", pymongo.ASCENDING)], unique=True)
        # Cũng nên tạo index cho các trường thường xuyên được query
        db.vehicles.create_index([("brand", pymongo.ASCENDING)])
        db.vehicles.create_index([("price_per_day", pymongo.ASCENDING)])
    except ServerSelectionTimeoutError:
        st.warning("Không thể kết nối tới MongoDB. Vui lòng kiểm tra kết nối mạng.")

def manage_vehicles():
    st.subheader("Quản Lý Xe")
    
    # Form thêm xe
    with st.form(key='add_vehicle_form'):
        brand = sanitize_input(st.text_input("Thương Hiệu"))
        model = sanitize_input(st.text_input("Mẫu Xe"))
        license_plate = sanitize_input(st.text_input("Biển Số Xe"))
        year = st.number_input("Năm Sản Xuất", min_value=1900, max_value=datetime.datetime.now().year, value=2022)
        price_per_day = st.number_input("Giá Thuê Mỗi Ngày", min_value=0)
        image = st.text_input("Link Ảnh Xe")
        required_license_type = st.selectbox("Hạng bằng lái yêu cầu", ["A1", "A2", "B1", "B2", "C", "D", "E", "F"])
        submit_button = st.form_submit_button(label='Thêm Xe')

    if submit_button:
        # Kiểm tra xem biển số xe có trống không
        if not license_plate.strip():
            st.error("Biển số xe không được để trống!")
        else:
            vehicle_data = {
                "brand": brand,
                "model": model,
                "license_plate": license_plate.strip(),
                "price_per_day": price_per_day,
                "status": "available",
                "year": year,
                "created_at": datetime.datetime.now(),
                "image": image,
                "required_license_type": required_license_type
            }
            try:
                # Kiểm tra xem biển số xe có trùng không
                existing_vehicle = db.vehicles.find_one({"license_plate": license_plate.strip()})
                if existing_vehicle:
                    st.error(f"Xe với biển số {license_plate} đã tồn tại!")
                else:
                    db.vehicles.insert_one(vehicle_data)
                    st.success("Xe đã được thêm thành công!")
                    st.rerun()  # Làm mới giao diện sau khi thêm xe
            except DuplicateKeyError:
                st.error("Biển số xe này đã tồn tại. Vui lòng kiểm tra lại!")
            except ServerSelectionTimeoutError:
                st.warning("Không thể kết nối đến MongoDB. Vui lòng thử lại sau!")

    # Hiển thị danh sách xe và thêm nút xóa/chỉnh sửa trong một hàng
    st.subheader("Danh Sách Xe")
    try:
        vehicles = db.vehicles.find({})
        for vehicle in vehicles:
            # Sử dụng các cột để hiển thị thông tin và các nút trên cùng một hàng
            cols = st.columns([3, 1, 1, 1])  # Chia layout thành 4 cột với các kích thước khác nhau
            with cols[0]:
                # Thay thế bằng:
                vehicle_data = vehicle
                st.write(f"{vehicle_data['brand']} {vehicle_data['model']} (Biển số: {vehicle_data['license_plate']}), Năm sản xuất: {vehicle_data['year']}, Giá: {vehicle_data['price_per_day']} USD/ngày, Hạng Bằng Lái: {vehicle_data['required_license_type']}")

            with cols[1]:
                # Nút chỉnh sửa xe
                if st.button(f"Chỉnh Sửa", key=f"edit_{vehicle['_id']}"):
                    st.session_state['editing_vehicle_id'] = str(vehicle["_id"])

            with cols[2]:
                # Nút xóa xe
                if st.button(f"Xóa", key=f"delete_{vehicle['_id']}"):
                    try:
                        # Kiểm tra xem xe có đang được thuê không
                        booking = db.bookings.find_one({"vehicle_id": vehicle["_id"], "status": {"$ne": "completed"}})
                        if booking:
                            st.error("Không thể xóa xe đang được thuê hoặc đã được đặt.")
                        else:
                            db.vehicles.delete_one({"_id": vehicle["_id"]})
                            st.success(f"Xe {vehicle['brand']} {vehicle['model']} đã bị xóa.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi xóa xe: {e}")

        # Hiển thị form chỉnh sửa nếu có xe đang được chỉnh sửa
        editing_vehicle_id = st.session_state.get('editing_vehicle_id', None)
        if editing_vehicle_id:
            vehicle_to_edit = db.vehicles.find_one({"_id": ObjectId(editing_vehicle_id)})
            if vehicle_to_edit:
                edit_vehicle(vehicle_to_edit)
            else:
                st.error("Không tìm thấy xe để chỉnh sửa.")
                st.session_state['editing_vehicle_id'] = None

    except ServerSelectionTimeoutError:
        st.error("Không thể kết nối tới MongoDB!")

# Hàm để chỉnh sửa thông tin xe
def edit_vehicle(vehicle):
    st.subheader("Chỉnh Sửa Thông Tin Xe")

    # Hiển thị form để chỉnh sửa thông tin xe
    with st.form(key=f"edit_form_{vehicle['_id']}"):
        new_brand = sanitize_input(st.text_input("Thương Hiệu", value=vehicle["brand"]))
        new_model = sanitize_input(st.text_input("Mẫu Xe", value=vehicle["model"]))
        new_license_plate = sanitize_input(st.text_input("Biển Số Xe", value=vehicle["license_plate"]))
        new_price_per_day = st.number_input("Giá Thuê Mỗi Ngày", min_value=0, value=vehicle["price_per_day"])
        new_year = st.number_input("Năm Sản Xuất", min_value=1900, max_value=datetime.datetime.now().year, value=vehicle["year"])
        new_image = st.text_input("Link Ảnh Xe", value=vehicle.get("image", ""))
        new_required_license_type = st.selectbox("Hạng bằng lái yêu cầu", ["A1", "A2", "B1", "B2", "C", "D", "E", "F"], index=["A1", "A2", "B1", "B2", "C", "D", "E", "F"].index(vehicle["required_license_type"]) if "required_license_type" in vehicle else 0)
        submit_button = st.form_submit_button(label="Cập Nhật")

    if submit_button:
        # Kiểm tra xem biển số xe có trống không
        if not new_license_plate.strip():
            st.error("Biển số xe không được để trống!")
            return

        try:
            # Kiểm tra nếu biển số xe đã tồn tại cho xe khác
            existing_vehicle = db.vehicles.find_one({"license_plate": new_license_plate.strip(), "_id": {"$ne": vehicle["_id"]}})
            if existing_vehicle:
                st.error(f"Xe với biển số {new_license_plate} đã tồn tại!")
            else:
                # Cập nhật thông tin xe trong cơ sở dữ liệu
                result = db.vehicles.update_one(
                    {"_id": vehicle["_id"]},
                    {"$set": {
                        "brand": new_brand,
                        "model": new_model,
                        "license_plate": new_license_plate.strip(),
                        "price_per_day": new_price_per_day,
                        "year": new_year,
                        "image": new_image,
                        "required_license_type": new_required_license_type
                    }}
                )
                if result.modified_count > 0:
                    st.success("Thông tin xe đã được cập nhật thành công!")
                else:
                    st.info("Không có thay đổi nào được thực hiện.")
                st.session_state['editing_vehicle_id'] = None
                st.rerun()  # Làm mới giao diện sau khi cập nhật
        except DuplicateKeyError:
            st.error("Biển số xe này đã tồn tại. Vui lòng kiểm tra lại!")
        except ServerSelectionTimeoutError:
            st.warning("Không thể kết nối đến MongoDB. Vui lòng thử lại sau!")

def search_vehicles():
    st.subheader("Tìm Kiếm Xe")
    try:
        # Lọc theo thương hiệu và giá thuê xe
        brand_filter = st.text_input("Tìm kiếm theo thương hiệu")
        price_filter = st.slider("Giá thuê mỗi ngày (USD)", 0, 500, (0, 500))
        
        # Truy vấn MongoDB với các bộ lọc
        query = {}
        if brand_filter:
            query["brand"] = {"$regex": brand_filter, "$options": "i"}  # Tìm kiếm không phân biệt chữ hoa chữ thường
        query["price_per_day"] = {"$gte": price_filter[0], "$lte": price_filter[1]}
        
        vehicles = db.vehicles.find(query)
        
        # Hiển thị kết quả
        st.write(f"Hiển thị kết quả cho thương hiệu: {brand_filter}, giá từ {price_filter[0]} đến {price_filter[1]} USD/ngày")
        for vehicle in vehicles:
            # Thay thế bằng:
            vehicle_data = db.vehicles.find_one({"_id": vehicle["_id"]})

            # Chỉ hiển thị thông tin nếu có dữ liệu
            if vehicle_data:
                st.write(f"{vehicle_data['brand']} {vehicle_data['model']} (Biển số: {vehicle_data['license_plate']}), Năm sản xuất: {vehicle_data['year']}, Giá: {vehicle_data['price_per_day']} USD/ngày, Hạng Bằng Lái: {vehicle_data['required_license_type']}")
    
    except ServerSelectionTimeoutError:
        st.error("Không thể kết nối đến MongoDB. Vui lòng kiểm tra kết nối mạng.")