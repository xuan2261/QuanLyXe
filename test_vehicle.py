import pytest
from modules.vehicle import manage_vehicles, db, edit_vehicle
from unittest.mock import patch, MagicMock
from bson import ObjectId
import os
import datetime
import mongomock
import streamlit as st


# Thiết lập môi trường test
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    # Sử dụng mongomock để tạo cơ sở dữ liệu giả lập
    mock_client = mongomock.MongoClient()
    monkeypatch.setattr("modules.vehicle.db", mock_client["test_database"])

    # Mock các hàm của Streamlit để không phụ thuộc vào giao diện
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

    yield


# Test thêm xe thành công
def test_manage_vehicles_add_vehicle_success():
    with patch("streamlit.text_input", side_effect=["Toyota", "Camry", "ABC1234", ""]), \
         patch("streamlit.number_input", side_effect=[2023, 50]), \
         patch("streamlit.selectbox", return_value="B1"), \
         patch("streamlit.success") as mock_success, \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.form_submit_button", return_value=True):
        manage_vehicles()

        # Kiểm tra xem xe đã được thêm thành công
        mock_success.assert_called_once_with("Xe đã được thêm thành công!")
        vehicle = db.vehicles.find_one({"license_plate": "ABC1234"})
        assert vehicle is not None
        assert vehicle["brand"] == "Toyota"


# Test thêm xe với biển số trùng lặp
def test_manage_vehicles_add_vehicle_duplicate_license():
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

    with patch("streamlit.error") as mock_error:
        manage_vehicles()
        mock_error.assert_called_once_with("Xe với biển số ABC1234 đã tồn tại!")


# Test chỉnh sửa xe thành công
def test_manage_vehicles_edit_vehicle_success():
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

    st.session_state["editing_vehicle_id"] = vehicle_id

    with patch("streamlit.text_input", side_effect=["Honda", "Accord", "DEF5678", ""]), \
         patch("streamlit.number_input", side_effect=[2023, 60]), \
         patch("streamlit.selectbox", return_value="B2"), \
         patch("streamlit.success") as mock_success, \
         patch("streamlit.form_submit_button", return_value=True):
        manage_vehicles()
        updated_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert updated_vehicle["model"] == "Accord"


# Test xóa xe đang được thuê
def test_manage_vehicles_delete_vehicle_rented():
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

    db.bookings.insert_one({
        "user_id": ObjectId(),
        "vehicle_id": ObjectId(vehicle_id),
        "start_date": "2024-01-01",
        "end_date": "2024-01-05",
        "total_price": 200.0,
        "payment_status": "pending",
        "status": "confirmed",
        "created_at": datetime.datetime.now()
    })

    with patch("streamlit.error") as mock_error:
        manage_vehicles()
        mock_error.assert_any_call("Không thể xóa xe đang được thuê hoặc đã được đặt.")