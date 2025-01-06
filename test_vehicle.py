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
    monkeypatch.setattr(st, "text_input", lambda *args, **kwargs: kwargs.get('value', "mock_input"))
    monkeypatch.setattr(st, "number_input", lambda *args, **kwargs: kwargs.get('value', 2023))
    monkeypatch.setattr(st, "selectbox", lambda *args, **kwargs: kwargs.get('index', "B1"))
    monkeypatch.setattr(st, "form", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(st, "form_submit_button", lambda *args, **kwargs: True)
    monkeypatch.setattr(st, "session_state", {"editing_vehicle_id": None})
    monkeypatch.setattr(st, "error", lambda *args, **kwargs: print(f"Error: {args[0]}"))
    monkeypatch.setattr(st, "success", lambda *args, **kwargs: print(f"Success: {args[0]}"))
    monkeypatch.setattr(st, "info", lambda *args, **kwargs: print(f"Info: {args[0]}"))
    monkeypatch.setattr(st, "warning", lambda *args, **kwargs: print(f"Warning: {args[0]}"))
    monkeypatch.setattr(st, "write", lambda *args, **kwargs: print(str(args[0])))
    monkeypatch.setattr(st, "columns", lambda x: [MagicMock()] * (x if isinstance(x, int) else len(x)))
    monkeypatch.setattr(st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "empty", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(st, "markdown", lambda *args, **kwargs: None)

    # Mock st.button để quản lý hành vi click nút dựa trên tham số label
    def mock_st_button(label, key=None, *args, **kwargs):
        if key == "add_submit":
            return True  # Luôn True cho nút 'Thêm Xe'
        elif "edit_" in key:
            return False  # Trả về False cho nút "Chỉnh Sửa"
        elif "delete_" in key:
            return True  # Trả về True cho nút "Xóa"
        return False

    monkeypatch.setattr(st, "button", mock_st_button)

    yield

    # Reset lại session state sau mỗi test case
    if hasattr(st, "session_state"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]

# Test hàm manage_vehicles
def test_manage_vehicles_add_vehicle_success(setup_test_environment):
    with patch("streamlit.text_input") as mock_text_input, \
         patch("streamlit.number_input") as mock_number_input, \
         patch("streamlit.selectbox") as mock_selectbox, \
         patch("streamlit.form_submit_button") as mock_form_submit_button, \
         patch("streamlit.success") as mock_success:

        # Thiết lập các giá trị trả về cho các input fields
        mock_text_input.side_effect = ["Toyota", "Camry", "ABC1234", ""]
        mock_number_input.side_effect = [2023, 50]
        mock_selectbox.return_value = "B1"
        mock_form_submit_button.return_value = True

        manage_vehicles()

        # Kiểm tra xem thông báo thành công có xuất hiện không
        mock_success.assert_called_once_with("Xe đã được thêm thành công!")

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
    with patch("streamlit.text_input") as mock_text_input, \
         patch("streamlit.number_input") as mock_number_input, \
         patch("streamlit.selectbox") as mock_selectbox, \
         patch("streamlit.form_submit_button") as mock_form_submit_button, \
         patch("streamlit.error") as mock_error:

        mock_text_input.side_effect = ["Ford", "Mustang", "ABC1234", ""]
        mock_number_input.side_effect = [2023, 100]
        mock_selectbox.return_value = "B2"
        mock_form_submit_button.return_value = True

        manage_vehicles()

        # Kiểm tra thông báo lỗi
        mock_error.assert_called_with("Xe với biển số ABC1234 đã tồn tại!")

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
    with patch("streamlit.text_input") as mock_text_input, \
        patch("streamlit.number_input") as mock_number_input, \
        patch("streamlit.selectbox") as mock_selectbox, \
        patch("streamlit.form_submit_button") as mock_form_submit_button, \
        patch("streamlit.success") as mock_success, \
        patch("streamlit.button") as mock_button:

        # Giả lập hành động của người dùng
        mock_text_input.side_effect = ["Honda", "Accord", "DEF5678", ""]
        mock_number_input.side_effect = [2023, 60]
        mock_selectbox.return_value = "B2"
        mock_form_submit_button.return_value = True
        mock_button.side_effect = [True]

        # Giả lập người dùng đã chọn chỉnh sửa xe này
        st.session_state['editing_vehicle_id'] = vehicle_id

        # Gọi hàm manage_vehicles
        manage_vehicles()

        # Kiểm tra thông báo thành công
        mock_success.assert_called_once_with("Thông tin xe đã được cập nhật thành công!")

        # Kiểm tra xem thông tin xe đã được cập nhật đúng không
        updated_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert updated_vehicle is not None
        assert updated_vehicle["brand"] == "Honda"
        assert updated_vehicle["model"] == "Accord"
        assert updated_vehicle["license_plate"] == "DEF5678"
        assert updated_vehicle["price_per_day"] == 60
        assert updated_vehicle["year"] == 2023
        assert updated_vehicle["required_license_type"] == "B2"

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
    with patch("streamlit.button") as mock_button, patch("streamlit.success") as mock_success:
        # Giả lập hành động của người dùng cho nút xóa
        mock_button.return_value = True
        manage_vehicles()

        # Kiểm tra xem xe đã bị xóa chưa
        deleted_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert deleted_vehicle is None

        # Kiểm tra thông báo thành công
        mock_success.assert_called_once_with(f"Xe Honda Civic đã bị xóa.")

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