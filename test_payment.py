import pytest
from modules.payment import process_simulated_payment
from config import db as original_db
from datetime import datetime
from unittest.mock import patch
from bson.objectid import ObjectId
import mongomock


class DatabaseMock:
    def __init__(self, db, temp_mapping=None):
        self.db = db
        self.temp_mapping = temp_mapping or {}

    def __getitem__(self, collection_name):
        # Ánh xạ collection nếu có trong temp_mapping
        if collection_name in self.temp_mapping:
            return self.db[self.temp_mapping[collection_name]]
        return self.db[collection_name]


# Fixture setup môi trường test và ánh xạ bảng tạm
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    # Tạo kết nối mongomock
    mock_client = mongomock.MongoClient()
    test_db = mock_client['test_database']

    # Ánh xạ bảng tạm sang bảng thực
    temp_mapping = {"temp_payment_cards": "payment_cards"}
    mock_db = DatabaseMock(test_db, temp_mapping)

    # Thay thế db trong config
    monkeypatch.setattr("config.db", mock_db)
    yield


@pytest.fixture
def reset_temp_table():
    # Đảm bảo xóa tất cả các collection trước mỗi bài kiểm thử
    temp_payment_cards = original_db["payment_cards"]
    temp_payment_cards.drop()
    yield


def test_process_simulated_payment_successful(reset_temp_table):
    # Thêm một thẻ thanh toán giả lập vào bảng tạm
    temp_payment_cards = original_db["payment_cards"]
    temp_payment_cards.insert_one({
        "card_number": "1234567890123456",
        "card_holder": "Test User",
        "balance": 1000.0,
        "account_status": "active",
        "expiry_date": "2025-12-31",
        "payment_status": "pending",
        "payment_date": None
    })

    # Gọi hàm xử lý thanh toán
    result = process_simulated_payment("1234567890123456", 100.0, ObjectId())

    assert result["status"] == "success"
    assert result["message"] == "Thanh toán thành công"
    assert result["new_balance"] == 900.0

    # Kiểm tra số dư trong database
    card = temp_payment_cards.find_one({"card_number": "1234567890123456"})
    assert card["balance"] == 900.0


def test_process_simulated_payment_insufficient_funds(reset_temp_table):
    temp_payment_cards = original_db["payment_cards"]
    temp_payment_cards.insert_one({
        "card_number": "1111222233334444",
        "card_holder": "Test User",
        "balance": 50.0,
        "account_status": "active",
        "expiry_date": "2025-12-31",
        "payment_status": "pending",
        "payment_date": None
    })

    result = process_simulated_payment("1111222233334444", 100.0, ObjectId())

    assert result["status"] == "failed"
    assert result["message"] == "Không đủ số dư"

    card = temp_payment_cards.find_one({"card_number": "1111222233334444"})
    assert card["balance"] == 50.0


def test_process_simulated_payment_card_not_found(reset_temp_table):
    result = process_simulated_payment("9999999999999999", 100.0, ObjectId())

    assert result["status"] == "failed"
    assert result["message"] == "Thẻ không tồn tại"


def test_process_simulated_payment_account_locked(reset_temp_table):
    temp_payment_cards = original_db["payment_cards"]
    temp_payment_cards.insert_one({
        "card_number": "5555666677778888",
        "card_holder": "Test User",
        "balance": 1000.0,
        "account_status": "locked",
        "expiry_date": "2025-12-31",
        "payment_status": "pending",
        "payment_date": None
    })

    result = process_simulated_payment("5555666677778888", 100.0, ObjectId())

    assert result["status"] == "failed"
    assert result["message"] == "Tài khoản bị khóa"


def test_process_simulated_payment_card_expired(reset_temp_table):
    temp_payment_cards = original_db["payment_cards"]
    temp_payment_cards.insert_one({
        "card_number": "9999888877776666",
        "card_holder": "Test User",
        "balance": 1000.0,
        "account_status": "active",
        "expiry_date": "2020-12-31",  # Thẻ đã hết hạn
        "payment_status": "pending",
        "payment_date": None
    })

    result = process_simulated_payment("9999888877776666", 100.0, ObjectId())

    assert result["status"] == "failed"
    assert result["message"] == "Thẻ đã hết hạn"
