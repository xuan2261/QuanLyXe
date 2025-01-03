import pytest
from modules.payment import process_simulated_payment
from config import db
from datetime import datetime
from unittest.mock import patch
import os
from bson.objectid import ObjectId

# Thiết lập biến môi trường cho test
@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    os.environ["MONGODB_CONNECTION_STRING"] = "mongodb+srv://thuexedap:thuexedap@clusterthuexedap.g1dbl.mongodb.net/?retryWrites=true&w=majority&appName=ClusterThueXeDap"  # Thay thế bằng connection string của MongoDB test

# Mock ObjectId để tránh lỗi khi so sánh
@pytest.fixture(autouse=True)
def mock_objectid(monkeypatch):
    class MockObjectId:
        def __init__(self, id_str=None):
            self._id_str = id_str or "5f8d04b96f17d6957f47a3f5"  # Giá trị ObjectId giả định

        def __str__(self):
            return self._id_str

        def __eq__(self, other):
            return isinstance(other, MockObjectId) and str(self) == str(other)

    monkeypatch.setattr("bson.objectid.ObjectId", MockObjectId)

def test_process_simulated_payment_successful(mock_objectid, setup_test_environment):
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

    result = process_simulated_payment("1234567890123456", 100.0, "5f8d04b96f17d6957f47a3f5")

    assert result["status"] == "success"
    assert result["message"] == "Thanh toán thành công"
    assert result["new_balance"] == 900.0

    # Kiểm tra số dư trong database
    card = payment_cards.find_one({"card_number": "1234567890123456"})
    assert card["balance"] == 900.0

    # Xóa thẻ đã tạo
    payment_cards.delete_one({"card_number": "1234567890123456"})

def test_process_simulated_payment_insufficient_funds(mock_objectid, setup_test_environment):
    # Tạo một thẻ thanh toán giả lập trong database
    payment_cards = db['payment_cards']
    payment_cards.insert_one({
        "card_number": "1234567890123456",
        "card_holder": "Test User",
        "balance": 50.0,
        "account_status": "active",
        "expiry_date": "2025-12-31",
        "payment_status": "pending",
        "payment_date": None
    })

    result = process_simulated_payment("1234567890123456", 100.0, "5f8d04b96f17d6957f47a3f5")

    assert result["status"] == "failed"
    assert result["message"] == "Không đủ số dư"

    # Kiểm tra số dư trong database (không thay đổi)
    card = payment_cards.find_one({"card_number": "1234567890123456"})
    assert card["balance"] == 50.0

    # Xóa thẻ đã tạo
    payment_cards.delete_one({"card_number": "1234567890123456"})

def test_process_simulated_payment_card_not_found(mock_objectid, setup_test_environment):
    result = process_simulated_payment("9999999999999999", 100.0, "5f8d04b96f17d6957f47a3f5")

    assert result["status"] == "failed"
    assert result["message"] == "Thẻ không tồn tại"

def test_process_simulated_payment_account_locked(mock_objectid, setup_test_environment):
    # Tạo một thẻ thanh toán giả lập trong database
    payment_cards = db['payment_cards']
    payment_cards.insert_one({
        "card_number": "1234567890123456",
        "card_holder": "Test User",
        "balance": 1000.0,
        "account_status": "locked",
        "expiry_date": "2025-12-31",
        "payment_status": "pending",
        "payment_date": None
    })

    result = process_simulated_payment("1234567890123456", 100.0, "5f8d04b96f17d6957f47a3f5")

    assert result["status"] == "failed"
    assert result["message"] == "Tài khoản bị khóa"

    # Xóa thẻ đã tạo
    payment_cards.delete_one({"card_number": "1234567890123456"})

def test_process_simulated_payment_card_expired(mock_objectid, setup_test_environment):
    # Tạo một thẻ thanh toán giả lập trong database
    payment_cards = db['payment_cards']
    payment_cards.insert_one({
        "card_number": "1234567890123456",
        "card_holder": "Test User",
        "balance": 1000.0,
        "account_status": "active",
        "expiry_date": "2020-12-31",  # Thẻ đã hết hạn
        "payment_status": "pending",
        "payment_date": None
    })

    result = process_simulated_payment("1234567890123456", 100.0, "5f8d04b96f17d6957f47a3f5")

    assert result["status"] == "failed"
    assert result["message"] == "Thẻ đã hết hạn"

    # Xóa thẻ đã tạo
    payment_cards.delete_one({"card_number": "1234567890123456"})