import pytest
from unittest.mock import patch
import datetime
from bson.objectid import ObjectId
import mongomock
from modules.vehicle import manage_vehicles, db
import streamlit as st

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    mock_client = mongomock.MongoClient()
    monkeypatch.setattr("modules.vehicle.db", mock_client["test_database"])
    yield

def test_manage_vehicles_add_vehicle_success():
    with patch("streamlit.text_input") as mock_text_input, \
         patch("streamlit.number_input") as mock_number_input, \
         patch("streamlit.selectbox") as mock_selectbox, \
         patch("streamlit.form_submit_button") as mock_form_submit_button, \
         patch("streamlit.success") as mock_success:

        mock_text_input.side_effect = ["Toyota", "Camry", "ABC1234", ""] 
        mock_number_input.side_effect = [2023, 50] 
        mock_selectbox.return_value = "B1"
        mock_form_submit_button.return_value = True

        manage_vehicles()

        mock_success.assert_called_once_with("Xe đã được thêm thành công!")
        vehicle = db.vehicles.find_one({"license_plate": "ABC1234"})
        assert vehicle is not None
        assert vehicle["brand"] == "Toyota"
        assert vehicle["model"] == "Camry"

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

        mock_error.assert_called_once_with("Xe với biển số ABC1234 đã tồn tại!")

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

    with patch("streamlit.text_input") as mock_text_input, \
         patch("streamlit.number_input") as mock_number_input, \
         patch("streamlit.selectbox") as mock_selectbox, \
         patch("streamlit.form_submit_button") as mock_form_submit_button, \
         patch("streamlit.success") as mock_success:

        mock_text_input.side_effect = ["Honda", "Accord", "", ""]
        mock_number_input.side_effect = [2023, 60]
        mock_selectbox.return_value = "B2"
        mock_form_submit_button.return_value = True

        st.session_state['editing_vehicle_id'] = vehicle_id

        manage_vehicles()

        mock_success.assert_called_once_with("Thông tin xe đã được cập nhật thành công!")
        
        updated_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        
        assert updated_vehicle is not None
        assert updated_vehicle["model"] == "Accord"

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

    with patch("streamlit.button") as mock_button, \
         patch("streamlit.success") as mock_success:
        
         mock_button.side_effect = [False, True] 
        
         manage_vehicles()

         deleted_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
         
         assert deleted_vehicle is None

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

    with patch("streamlit.button") as mock_button, \
         patch("streamlit.error") as mock_error:
        
         mock_button.side_effect = [False, True] 
        
         manage_vehicles()

         mock_error.assert_called_once_with("Không thể xóa xe đang được thuê hoặc đã được đặt.")