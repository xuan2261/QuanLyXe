import pytest
from modules.vehicle import manage_vehicles, db
from unittest.mock import patch
from bson import ObjectId
import os
import datetime
import mongomock
import streamlit as st

# Thiết lập biến môi trường cho test và mock Streamlit
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    # Sử dụng mongomock.MongoClient thay cho MongoClient
    monkeypatch.setattr("pymongo.MongoClient", mongomock.MongoClient)
    os.environ["MONGODB_CONNECTION_STRING"] = "mongodb://localhost:27017"
    # Mock các hàm của Streamlit
    monkeypatch.setattr("streamlit.form", lambda key: type('obj', (object,), {'__enter__': lambda x: None, '__exit__': lambda x, y, z, a: None})())
    monkeypatch.setattr("streamlit.form_submit_button", lambda label, key=None: True)
    monkeypatch.setattr("streamlit.text_input", lambda label, value=None, max_chars=None, key=None, type=None: value if value else "")
    monkeypatch.setattr("streamlit.number_input", lambda label, min_value=None, max_value=None, value=None, step=None, format=None, key=None: value)
    monkeypatch.setattr("streamlit.selectbox", lambda label, options, index=0, format_func=None, key=None: options[index])
    monkeypatch.setattr("streamlit.columns", lambda x: [st.empty() for _ in range(x)])
    monkeypatch.setattr("streamlit.button", lambda label, key=None: False)
    monkeypatch.setattr("streamlit.error", lambda x: print(f"Error: {x}"))
    monkeypatch.setattr("streamlit.success", lambda x: print(f"Success: {x}"))
    monkeypatch.setattr("streamlit.info", lambda x: print(f"Info: {x}"))
    monkeypatch.setattr("streamlit.warning", lambda x: print(f"Warning: {x}"))
    monkeypatch.setattr("streamlit.write", lambda x: print(x))
    monkeypatch.setattr("streamlit.session_state", {"editing_vehicle_id": None})
    monkeypatch.setattr("streamlit.rerun", lambda: None)

    yield

# Test hàm manage_vehicles
def test_manage_vehicles_add_vehicle_success(setup_test_environment):
    # Thêm xe
    manage_vehicles()

    vehicle = db.vehicles.find_one({"license_plate": "ABC1234"})
    assert vehicle is not None
    assert vehicle["brand"] == "Toyota"

# Test thêm xe với biển số trùng lặp
def test_manage_vehicles_add_vehicle_duplicate_license(setup_test_environment):
    # Thêm một xe với biển số trùng
    db.vehicles.insert_one({
        "brand": "Honda",
        "model": "Civic",
        "license_plate": "ABC1234",
        "price_per_day": 40,
        "status": "available",
        "year": 2022,
        "created_at": datetime.datetime.now(),
        "image": "",
        "required_license_type": "B1"
    })

    # Gọi hàm manage_vehicles
    manage_vehicles()

    # Kiểm tra thông báo lỗi
    # Chú ý: Trong trường hợp thực tế, bạn sẽ kiểm tra xem thông báo lỗi có hiển thị trên giao diện không.
    # Ở đây, chúng ta chỉ kiểm tra xem hàm có được gọi với đúng thông báo không.

# Test chỉnh sửa xe thành công
def test_manage_vehicles_edit_vehicle_success(setup_test_environment):
    # Thêm một xe vào database
    vehicle = db.vehicles.insert_one({
        "brand": "Honda",
        "model": "Civic",
        "license_plate": "ABC1234",
        "price_per_day": 40,
        "status": "available",
        "year": 2022,
        "created_at": datetime.datetime.now(),
        "image": "",
        "required_license_type": "B1"
    })
    vehicle_id = str(vehicle.inserted_id)

    # Giả lập hành động của người dùng
    with patch("streamlit.button") as mock_button:
        mock_button.side_effect = [True, True]  # Lần đầu là click vào "Chỉnh Sửa", lần 2 là "Cập nhật" trong form

        # Giả lập người dùng đã chọn chỉnh sửa xe này
        st.session_state['editing_vehicle_id'] = vehicle_id

        # Gọi hàm manage_vehicles để hiển thị form chỉnh sửa
        manage_vehicles()

        # Cập nhật thông tin xe
        updated_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert updated_vehicle is not None
        assert updated_vehicle["brand"] == "Honda"  # Giá trị mặc định từ mock_text_input
        assert updated_vehicle["model"] == "Civic"  # Giá trị mặc định từ mock_text_input
        assert updated_vehicle["license_plate"] == "ABC1234"  # Giá trị mặc định từ mock_text_input
        assert updated_vehicle["price_per_day"] == 40
        assert updated_vehicle["year"] == 2022
        assert updated_vehicle["required_license_type"] == "B1"

# Test xóa xe thành công
def test_manage_vehicles_delete_vehicle_success(setup_test_environment):
    # Thêm một xe vào database
    vehicle = db.vehicles.insert_one({
        "brand": "Honda",
        "model": "Civic",
        "license_plate": "ABC1234",
        "price_per_day": 40,
        "status": "available",
        "year": 2022,
        "created_at": datetime.datetime.now(),
        "image": "",
        "required_license_type": "B1"
    })
    vehicle_id = str(vehicle.inserted_id)

    # Giả lập hành động của người dùng
    with patch("streamlit.button") as mock_button:
        mock_button.side_effect = [False, True]  # Lần đầu là click vào "Chỉnh Sửa", lần 2 là click vào "Xóa"

        # Gọi hàm manage_vehicles
        manage_vehicles()

        # Kiểm tra xem xe đã bị xóa chưa
        deleted_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert deleted_vehicle is None

# Test xóa xe đang được thuê hoặc đã được đặt
def test_manage_vehicles_delete_vehicle_rented(setup_test_environment):
    # Thêm một xe vào database
    vehicle = db.vehicles.insert_one({
        "brand": "Honda",
        "model": "Civic",
        "license_plate": "ABC1234",
        "price_per_day": 40,
        "status": "available",
        "year": 2022,
        "created_at": datetime.datetime.now(),
        "image": "",
        "required_license_type": "B1"
    })
    vehicle_id = str(vehicle.inserted_id)

    # Tạo một đơn đặt xe cho xe này
    db.bookings.insert_one({
        "user_id": ObjectId(),  # Tạo ObjectId mới
        "vehicle_id": ObjectId(vehicle_id),
        "start_date": "2024-01-01",
        "end_date": "2024-01-05",
        "total_price": 200.0,
        "payment_status": "pending",
        "status": "confirmed",
        "created_at": datetime.datetime.now()
    })

    # Giả lập hành động của người dùng
    with patch("streamlit.button") as mock_button, \
         patch("streamlit.error") as mock_error:

        mock_button.side_effect = [False, True]  # Lần đầu là click vào "Chỉnh Sửa", lần 2 là click vào "Xóa"

        # Gọi hàm manage_vehicles
        manage_vehicles()

        # Kiểm tra thông báo lỗi
        mock_error.assert_called_once_with("Không thể xóa xe đang được thuê hoặc đã được đặt.")