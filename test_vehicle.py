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
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: True)
    monkeypatch.setattr(st, "error", lambda *args, **kwargs: print(f"Error: {args[0]}"))  # Sửa ở đây
    monkeypatch.setattr(st, "success", lambda *args, **kwargs: print(f"Success: {args[0]}"))
    monkeypatch.setattr(st, "info", lambda *args, **kwargs: print(f"Info: {args[0]}"))
    monkeypatch.setattr(st, "warning", lambda *args, **kwargs: print(f"Warning: {args[0]}"))
    monkeypatch.setattr(st, "write", lambda *args, **kwargs: print(str(args[0])))
    monkeypatch.setattr(st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "empty", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(st, "markdown", lambda *args, **kwargs: None)

    # Mock st.columns để trả về danh sách các đối tượng MagicMock có độ dài tương ứng
    def mock_columns(spec):
        if isinstance(spec, int):
            return [MagicMock()] * spec
        elif isinstance(spec, list):
            return [MagicMock()] * len(spec)
        else:
            return []

    monkeypatch.setattr(st, "columns", mock_columns)

    yield

    # Reset lại session state sau mỗi test case
    if hasattr(st, "session_state"):
        for key in st.session_state.keys():
            del st.session_state[key]

# Test hàm manage_vehicles
def test_manage_vehicles_add_vehicle_success():
    with patch("streamlit.error") as mock_error, patch("streamlit.success") as mock_success:
        # Gọi hàm manage_vehicles để test
        manage_vehicles()

        # Kiểm tra thông báo lỗi và thông báo thành công
        assert mock_error.call_count == 1
        assert "Biển số xe không được để trống!" in str(mock_error.call_args_list[0][0][0])
        mock_success.assert_called_once_with("Xe đã được thêm thành công!")

        # Kiểm tra xem xe đã được thêm vào cơ sở dữ liệu chưa
        vehicle = db.vehicles.find_one({"license_plate": "ABC1234"})
        assert vehicle is not None
        assert vehicle["brand"] == "Toyota"

# Test thêm xe với biển số trùng lặp
def test_manage_vehicles_add_vehicle_duplicate_license():
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
    with patch("streamlit.error") as mock_error:
        manage_vehicles()

        # Kiểm tra thông báo lỗi
        mock_error.assert_called_with("Xe với biển số ABC1234 đã tồn tại!")

# Test chỉnh sửa xe thành công
def test_manage_vehicles_edit_vehicle_success():
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
    with patch('modules.vehicle.edit_vehicle') as mock_edit_vehicle:
        st.session_state['editing_vehicle_id'] = vehicle_id
        manage_vehicles()
        mock_edit_vehicle.assert_called_once_with(db.vehicles.find_one({"_id": ObjectId(vehicle_id)}))

# Test xóa xe thành công
def test_manage_vehicles_delete_vehicle_success():
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
    manage_vehicles()

    # Kiểm tra xem xe đã bị xóa chưa
    deleted_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
    assert deleted_vehicle is None

# Test xóa xe đang được thuê hoặc đã được đặt
def test_manage_vehicles_delete_vehicle_rented():
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
    with patch("streamlit.error") as mock_error:
        manage_vehicles()
        # Kiểm tra thông báo lỗi
        mock_error.assert_called_once_with("Không thể xóa xe đang được thuê hoặc đã được đặt.")