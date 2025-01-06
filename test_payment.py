import pytest
from modules.payment import process_simulated_payment
from config import db
from datetime import datetime
from unittest.mock import patch
import os
from bson.objectid import ObjectId
import mongomock

# Thay thế MongoClient bằng mongomock.MongoClient ở mức function
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    # Sử dụng mongomock.MongoClient thay cho MongoClient
    monkeypatch.setattr("pymongo.MongoClient", mongomock.MongoClient)
    # Nếu bạn không dùng MongoDB Atlas, hãy thay đổi connection string cho phù hợp
    os.environ["MONGODB_CONNECTION_STRING"] = "mongodb://localhost:27017" # Thay đổi connection string
    yield

# Loại bỏ mock_objectid fixture

def test_process_simulated_payment_successful(setup_test_environment):
    # Tạo một thẻ thanh toán giả lập trong database
    payment_cards = db['payment_cards']
    payment_cards.insert_one({
        "card_number": "1234567890123456",
        "card_holder": "Test User",
        "balance": 1000.0,
        "account_status": "active",
        "expiry_date": "2025-12-31",
        "payment_status": "pending",
        "payment_date": None
    })

    result = process_simulated_payment("1234567890123456", 100.0, ObjectId())

    assert result["status"] == "success"
    assert result["message"] == "Thanh toán thành công"
    assert result["new_balance"] == 900.0

    # Kiểm tra số dư trong database
    card = payment_cards.find_one({"card_number": "1234567890123456"})
    assert card["balance"] == 900.0

    # Không cần xóa thẻ vì dùng mongomock

def test_process_simulated_payment_insufficient_funds(setup_test_environment):
    # Tạo một thẻ thanh toán giả lập trong database
    payment_cards = db['payment_cards']
    payment_cards.insert_one({
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

    # Kiểm tra số dư trong database (không thay đổi)
    card = payment_cards.find_one({"card_number": "1111222233334444"})
    assert card["balance"] == 50.0

    # Không cần xóa thẻ vì dùng mongomock

def test_process_simulated_payment_card_not_found(setup_test_environment):
    result = process_simulated_payment("9999999999999999", 100.0, ObjectId())

    assert result["status"] == "failed"
    assert result["message"] == "Thẻ không tồn tại"

def test_process_simulated_payment_account_locked(setup_test_environment):
    # Tạo một thẻ thanh toán giả lập trong database
    payment_cards = db['payment_cards']
    payment_cards.insert_one({
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

    # Không cần xóa thẻ vì dùng mongomock

def test_process_simulated_payment_card_expired(setup_test_environment):
    # Tạo một thẻ thanh toán giả lập trong database
    payment_cards = db['payment_cards']
    payment_cards.insert_one({
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

    # Không cần xóa thẻ vì dùng mongomock