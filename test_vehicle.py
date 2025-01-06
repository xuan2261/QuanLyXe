import pytest
from unittest.mock import patch
import datetime
from bson.objectid import ObjectId
import mongomock
from modules.vehicle import manage_vehicles, db


# Thiết lập môi trường test và đảm bảo cơ sở dữ liệu sạch
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    # Sử dụng mongomock để tạo một cơ sở dữ liệu giả lập trong bộ nhớ
    mock_client = mongomock.MongoClient()
    monkeypatch.setattr("modules.vehicle.db", mock_client["test_database"])
    yield


# Test thêm xe thành công
def test_manage_vehicles_add_vehicle_success():
    with patch("streamlit.text_input") as mock_text_input, patch(
        "streamlit.number_input"
    ) as mock_number_input, patch("streamlit.button") as mock_button, patch(
        "streamlit.success"
    ) as mock_success, patch("streamlit.form_submit_button") as mock_form_submit_button, patch("streamlit.selectbox") as mock_selectbox:
        mock_text_input.side_effect = ["Toyota", "Camry", "ABC1234", ""]
        mock_number_input.side_effect = [2023, 50]
        mock_selectbox.return_value = "B1"
        mock_button.return_value = False  # Không nhấn nút chỉnh sửa
        mock_form_submit_button.return_value = True

        manage_vehicles()

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
        "required_license_type": "B1",
    })

    with patch("streamlit.text_input") as mock_text_input, patch(
        "streamlit.number_input"
    ) as mock_number_input, patch("streamlit.button") as mock_button, patch(
        "streamlit.error"
    ) as mock_error, patch("streamlit.form_submit_button") as mock_form_submit_button, patch("streamlit.selectbox") as mock_selectbox:
        mock_text_input.side_effect = ["Ford", "Mustang", "ABC1234", ""]
        mock_number_input.side_effect = [2023, 100]
        mock_selectbox.return_value = "B2"
        mock_button.return_value = False
        mock_form_submit_button.return_value = True

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
        "required_license_type": "B1",
    })
    vehicle_id = str(vehicle.inserted_id)

    with patch("streamlit.text_input") as mock_text_input, patch(
        "streamlit.number_input"
    ) as mock_number_input, patch("streamlit.button") as mock_button, patch(
        "streamlit.form_submit_button"
    ) as mock_form_submit_button, patch(
        "streamlit.success"
    ) as mock_success, patch("streamlit.selectbox") as mock_selectbox:
        mock_text_input.side_effect = ["Honda", "Accord", "DEF5678", ""]
        mock_number_input.side_effect = [2023, 60]
        mock_selectbox.return_value = "B2"
        mock_button.side_effect = [False, True]
        mock_form_submit_button.return_value = True

        manage_vehicles()

        updated_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert updated_vehicle is not None
        assert updated_vehicle["brand"] == "Honda"
        assert updated_vehicle["model"] == "Accord"


# Test xóa xe thành công
def test_manage_vehicles_delete_vehicle_success():
    vehicle = db.vehicles.insert_one({
        "brand": "Honda",
        "model": "Civic",
        "license_plate": "ABC1234",
        "price_per_day": 40,
        "status": "available",
        "year": 2022,
        "created_at": datetime.datetime.now(),
        "image": "",
        "required_license_type": "B1",
    })
    vehicle_id = str(vehicle.inserted_id)

    with patch("streamlit.button") as mock_button, patch("streamlit.success") as mock_success:
        mock_button.side_effect = [False, True]

        manage_vehicles()

        deleted_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert deleted_vehicle is None


# Test xóa xe đang được thuê hoặc đã được đặt
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
        "required_license_type": "B1",
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
        "created_at": datetime.datetime.now(),
    })

    with patch("streamlit.button") as mock_button, patch("streamlit.error") as mock_error:
        mock_button.side_effect = [False, True]

        manage_vehicles()

        mock_error.assert_called_once_with("Không thể xóa xe đang được thuê hoặc đã được đặt.")