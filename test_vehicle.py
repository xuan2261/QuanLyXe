import pytest
from modules.vehicle import manage_vehicles, db
from unittest.mock import patch
from bson import ObjectId
import os
import datetime
import mongomock

# Thiết lập biến môi trường cho test
@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    # Sử dụng mongomock.MongoClient thay cho MongoClient
    with patch('pymongo.MongoClient', new=mongomock.MongoClient):
        os.environ["MONGODB_CONNECTION_STRING"] = "mongodb://localhost:27017" # Thay thế bằng connection string của MongoDB test
        yield

# Loại bỏ mock_objectid fixture

# Test hàm manage_vehicles
def test_manage_vehicles_add_vehicle_success(setup_test_environment):
    with patch("streamlit.text_input") as mock_text_input, patch(
        "streamlit.number_input"
    ) as mock_number_input, patch("streamlit.button") as mock_button, patch(
        "streamlit.success"
    ) as mock_success, patch("streamlit.form_submit_button") as mock_form_submit_button, patch("streamlit.selectbox") as mock_selectbox:
        mock_text_input.side_effect = ["Toyota", "Camry", "ABC1234", ""] # Thêm giá trị cho link ảnh xe
        mock_number_input.side_effect = [2023, 50]
        mock_selectbox.return_value = "B1" # Thiết lập giá trị mặc định cho selectbox
        mock_button.return_value = True
        mock_form_submit_button.return_value = True
        manage_vehicles()

        mock_success.assert_called_once_with("Xe đã được thêm thành công!")
        vehicle = db.vehicles.find_one({"license_plate": "ABC1234"})
        assert vehicle is not None
        assert vehicle["brand"] == "Toyota"
        assert vehicle["model"] == "Camry"
        assert vehicle["price_per_day"] == 50
        assert vehicle["year"] == 2023
        assert vehicle["required_license_type"] == "B1"

        # Không cần xóa xe vì dùng mongomock

def test_manage_vehicles_add_vehicle_duplicate_license(setup_test_environment):
    with patch("streamlit.text_input") as mock_text_input, patch(
        "streamlit.number_input"
    ) as mock_number_input, patch("streamlit.button") as mock_button, patch(
        "streamlit.error"
    ) as mock_error, patch("streamlit.form_submit_button") as mock_form_submit_button, patch("streamlit.selectbox") as mock_selectbox:
        # Thêm một xe với biển số trùng
        db.vehicles.insert_one(
            {
                "brand": "Honda",
                "model": "Civic",
                "license_plate": "ABC1234",
                "price_per_day": 40,
                "status": "available",
                "year": 2022,
                "created_at": datetime.datetime.now(),
                "image": "",
                "required_license_type": "B1"
            }
        )

        mock_text_input.side_effect = ["Ford", "Mustang", "ABC1234", ""]
        mock_number_input.side_effect = [2023, 100]
        mock_selectbox.return_value = "B2"
        mock_button.return_value = True
        mock_form_submit_button.return_value = True

        manage_vehicles()

        mock_error.assert_called_once_with(
            "Biển số xe này đã tồn tại. Vui lòng kiểm tra lại!"
        )

        # Không cần xóa xe vì dùng mongomock

def test_manage_vehicles_edit_vehicle_success(setup_test_environment):
    with patch("streamlit.text_input") as mock_text_input, patch(
        "streamlit.number_input"
    ) as mock_number_input, patch("streamlit.button") as mock_button, patch(
        "streamlit.form_submit_button"
    ) as mock_form_submit_button, patch(
        "streamlit.success"
    ) as mock_success, patch("streamlit.selectbox") as mock_selectbox:

        # Thêm một xe vào database
        vehicle = db.vehicles.insert_one(
            {
                "brand": "Honda",
                "model": "Civic",
                "license_plate": "ABC1234",
                "price_per_day": 40,
                "status": "available",
                "year": 2022,
                "created_at": datetime.datetime.now(),
                "image": "",
                "required_license_type": "B1"
            }
        )
        vehicle_id = str(vehicle.inserted_id)

        # Giả lập hành động của người dùng
        mock_text_input.side_effect = ["Honda", "Accord", "DEF5678", ""]  # Thay đổi thông tin xe
        mock_number_input.side_effect = [2023, 60]
        mock_selectbox.return_value = "B2"
        mock_button.side_effect = [False, True]  # Lần đầu trả về False để hiển thị nút "Chỉnh sửa", lần 2 trả về True để click nút "Xóa"
        mock_form_submit_button.return_value = True

        # Gọi hàm manage_vehicles
        manage_vehicles()

        # Kiểm tra thông tin xe sau khi chỉnh sửa
        updated_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert updated_vehicle is not None
        assert updated_vehicle["brand"] == "Honda"
        assert updated_vehicle["model"] == "Accord"
        assert updated_vehicle["license_plate"] == "DEF5678"
        assert updated_vehicle["price_per_day"] == 60
        assert updated_vehicle["year"] == 2023
        assert updated_vehicle["required_license_type"] == "B2"

        # Kiểm tra thông báo thành công
        mock_success.assert_called_once_with("Thông tin xe đã được cập nhật thành công!")

        # Không cần xóa xe vì dùng mongomock

def test_manage_vehicles_delete_vehicle_success(setup_test_environment):
    with patch("streamlit.button") as mock_button, patch("streamlit.success") as mock_success:
        # Thêm một xe vào database
        vehicle = db.vehicles.insert_one(
            {
                "brand": "Honda",
                "model": "Civic",
                "license_plate": "ABC1234",
                "price_per_day": 40,
                "status": "available",
                "year": 2022,
                "created_at": datetime.datetime.now(),
                "image": ""
            }
        )
        vehicle_id = str(vehicle.inserted_id)

        # Giả lập hành động của người dùng
        mock_button.side_effect = [False, True]  # Lần đầu trả về False để hiển thị nút "Xóa", lần 2 trả về True để click nút "Xóa"

        # Gọi hàm manage_vehicles
        manage_vehicles()

        # Kiểm tra xem xe đã bị xóa chưa
        deleted_vehicle = db.vehicles.find_one({"_id": ObjectId(vehicle_id)})
        assert deleted_vehicle is None

        # Kiểm tra thông báo thành công
        mock_success.assert_called_once_with(f"Xe Honda Civic đã bị xóa.")

        # Không cần xóa xe vì dùng mongomock

def test_manage_vehicles_delete_vehicle_rented(setup_test_environment):
    with patch("streamlit.button") as mock_button, patch("streamlit.error") as mock_error:
        # Thêm một xe vào database
        vehicle = db.vehicles.insert_one(
            {
                "brand": "Honda",
                "model": "Civic",
                "license_plate": "ABC1234",
                "price_per_day": 40,
                "status": "available",
                "year": 2022,
                "created_at": datetime.datetime.now(),
                "image": ""
            }
        )
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
        mock_button.side_effect = [False, True]

        # Gọi hàm manage_vehicles
        manage_vehicles()

        # Kiểm tra thông báo lỗi
        mock_error.assert_called_once_with("Không thể xóa xe đang được thuê hoặc đã được đặt.")

        # Không cần xóa xe và đơn đặt xe vì dùng mongomock