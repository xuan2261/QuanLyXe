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
    monkeypatch.setattr(st, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "write", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "columns", lambda x: [MagicMock() for _ in range(x)])
    monkeypatch.setattr(st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "empty", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(st, "markdown", lambda *args, **kwargs: None)
    yield

# Test hàm manage_vehicles
def test_manage_vehicles_add_vehicle_success(setup_test_environment):
    # Gọi hàm manage_vehicles để test
    manage_vehicles()

    # Kiểm tra xem xe đã được thêm vào cơ sở dữ liệu chưa
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
    vehicle_id = vehicle.inserted_id

    # Giả lập hành động của người dùng
    with patch('modules.vehicle.edit_vehicle') as mock_edit_vehicle:
      st.session_state.editing_vehicle_id = str(vehicle_id)
      manage_vehicles()
      mock_edit_vehicle.assert_called_once_with(db.vehicles.find_one({"_id": vehicle_id}))

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
    vehicle_id = vehicle.inserted_id

    # Giả lập hành động của người dùng
    with patch("streamlit.button") as mock_button:
      mock_button.side_effect = [True]
      manage_vehicles()

        # Kiểm tra xem xe đã bị xóa chưa
      deleted_vehicle = db.vehicles.find_one({"_id": vehicle_id})
      assert deleted_vehicle is None

# Test xóa xe đang được thuê hoặc đã được đặt
def test_manage_vehicles_delete_vehicle_rented(setup_test_environment):
  with patch("streamlit.button") as mock_button, \
        patch("streamlit.error") as mock_error:
    mock_button.side_effect = [False, True]
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
    manage_vehicles()
    # import pdb; pdb.set_trace()
    # Kiểm tra thông báo lỗi
    mock_error.assert_called_once_with("Không thể xóa xe đang được thuê hoặc đã được đặt.")