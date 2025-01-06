import pytest
from modules.vehicle import manage_vehicles, db, edit_vehicle
from unittest.mock import patch, MagicMock
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

    # Mock các hàm của Streamlit để tránh lỗi liên quan đến UI
    monkeypatch.setattr(st, "text_input", lambda *args, **kwargs: "mock_input")
    monkeypatch.setattr(st, "number_input", lambda *args, **kwargs: 2023)
    monkeypatch.setattr(st, "selectbox", lambda *args, **kwargs: "B1")
    monkeypatch.setattr(st, "form", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(st, "form_submit_button", lambda *args, **kwargs: True)
    monkeypatch.setattr(st, "session_state", {"editing_vehicle_id": None})
    monkeypatch.setattr(st, "error", lambda *args, **kwargs: print(f"Error: {args[0]}"))
    monkeypatch.setattr(st, "success", lambda *args, **kwargs: print(f"Success: {args[0]}"))
    monkeypatch.setattr(st, "info", lambda *args, **kwargs: print(f"Info: {args[0]}"))
    monkeypatch.setattr(st, "warning", lambda *args, **kwargs: print(f"Warning: {args[0]}"))
    monkeypatch.setattr(st, "write", lambda *args, **kwargs: print(str(args[0])))
    monkeypatch.setattr(st, "columns", lambda x: [MagicMock()] * len(x))
    monkeypatch.setattr(st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "empty", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(st, "markdown", lambda *args, **kwargs: None)

    # Mock st.button để luôn trả về False, trừ khi được override trong test case cụ thể
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)

    yield

    # Reset lại session state sau mỗi test case
    if hasattr(st, "session_state"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]

# Test thêm xe thành công
def test_manage_vehicles_add_vehicle_success(setup_test_environment):
    # Mock đầu vào
    with patch("streamlit.text_input", side_effect=["Toyota", "Camry", "ABC1234", ""]), \
         patch("streamlit.number_input", side_effect=[2023, 50]), \
         patch("streamlit.selectbox", return_value="B1"), \
         patch("streamlit.success") as mock_success, \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.form_submit_button", return_value=True):
        # Gọi hàm manage_vehicles để test
        manage_vehicles()

        # Kiểm tra xem thông báo thành công có xuất hiện không
        mock_success.assert_called_once_with("Xe đã được thêm thành công!")

        # Kiểm tra xe đã được thêm vào cơ sở dữ liệu
        vehicle = db.vehicles.find_one({"license_plate": "ABC1234"})
        assert vehicle is not None
        assert vehicle["brand"] == "Toyota"
        assert vehicle["model"] == "Camry"

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

    # Mock đầu vào
    with patch("streamlit.text_input", side_effect=["Ford", "Mustang", "ABC1234", ""]), \
         patch("streamlit.number_input", side_effect=[2023, 100]), \
         patch("streamlit.selectbox", return_value="B2"), \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.form_submit_button", return_value=True):
        # Gọi hàm manage_vehicles
        manage_vehicles()

        # Kiểm tra thông báo lỗi
        mock_error.assert_called_once_with("Xe với biển số ABC1234 đã tồn tại!")

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

    # Mock trạng thái chỉnh sửa
    st.session_state["editing_vehicle_id"] = vehicle_id

    # Mock hành động chỉnh sửa
    with patch("streamlit.text_input", side_effect=["Honda", "Accord", "DEF5678", ""]), \
         patch("streamlit.number_input", side_effect=[2023, 60]), \
         patch("streamlit.selectbox", return_value="B2"), \
         patch("streamlit.success") as mock_success, \
         patch("modules.vehicle.edit_vehicle") as mock_edit_vehicle, \
         patch("streamlit.form_submit_button", return_value=True):
        # Gọi hàm manage_vehicles
        manage_vehicles()

        # Kiểm tra xem hàm edit_vehicle đã được gọi
        mock_edit_vehicle.assert_called_once()

        # Kiểm tra xe đã được cập nhật
        updated_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert updated_vehicle["model"] == "Accord"
        assert updated_vehicle["license_plate"] == "DEF5678"

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

    # Gọi hàm manage_vehicles
    with patch("streamlit.button") as mock_button:
        mock_button.return_value = True
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

    # Gọi hàm manage_vehicles
    with patch("streamlit.button") as mock_button, \
         patch("streamlit.error") as mock_error:
        mock_button.return_value = True
        manage_vehicles()

        # Kiểm tra thông báo lỗi
        mock_error.assert_called_once_with("Không thể xóa xe đang được thuê hoặc đã được đặt.")