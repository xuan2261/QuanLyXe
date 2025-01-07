import pytest
from modules.payment import process_simulated_payment
from config import db
from bson.objectid import ObjectId

# Fixture setup môi trường test
@pytest.fixture(autouse=True)
def setup_test_environment():
    # Tạo bảng tạm `temp_payment_cards` cho mỗi lần kiểm thử
    db.create_collection("temp_payment_cards", capped=False)  # Tạo bảng tạm nếu chưa có
    yield
    # Xóa bảng tạm sau mỗi lần kiểm thử
    db.drop_collection("temp_payment_cards")

@pytest.fixture
def reset_temp_table():
    # Đảm bảo xóa dữ liệu trong bảng tạm trước mỗi bài kiểm thử
    db.temp_payment_cards.delete_many({})
    yield

def test_process_simulated_payment_successful(reset_temp_table):
    # Thêm một thẻ thanh toán giả lập vào bảng tạm
    temp_payment_cards = db.temp_payment_cards
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
    result = process_simulated_payment("1234567890123456", 100.0, ObjectId(), collection="temp_payment_cards")

    assert result["status"] == "success"
    assert result["message"] == "Thanh toán thành công"
    assert result["new_balance"] == 900.0

    # Kiểm tra số dư trong bảng tạm
    card = temp_payment_cards.find_one({"card_number": "1234567890123456"})
    assert card["balance"] == 900.0

def test_process_simulated_payment_insufficient_funds(reset_temp_table):
    # Thêm một thẻ thanh toán giả lập vào bảng tạm
    temp_payment_cards = db.temp_payment_cards
    temp_payment_cards.insert_one({
        "card_number": "1111222233334444",
        "card_holder": "Test User",
        "balance": 50.0,
        "account_status": "active",
        "expiry_date": "2025-12-31",
        "payment_status": "pending",
        "payment_date": None
    })

    # Gọi hàm xử lý thanh toán
    result = process_simulated_payment("1111222233334444", 100.0, ObjectId(), collection="temp_payment_cards")

    assert result["status"] == "failed"
    assert result["message"] == "Không đủ số dư"

    # Kiểm tra số dư trong bảng tạm (không thay đổi)
    card = temp_payment_cards.find_one({"card_number": "1111222233334444"})
    assert card["balance"] == 50.0

def test_process_simulated_payment_card_not_found(reset_temp_table):
    result = process_simulated_payment("9999999999999999", 100.0, ObjectId(), collection="temp_payment_cards")

    assert result["status"] == "failed"
    assert result["message"] == "Thẻ không tồn tại"

def test_process_simulated_payment_account_locked(reset_temp_table):
    # Thêm một thẻ thanh toán giả lập vào bảng tạm
    temp_payment_cards = db.temp_payment_cards
    temp_payment_cards.insert_one({
        "card_number": "5555666677778888",
        "card_holder": "Test User",
        "balance": 1000.0,
        "account_status": "locked",
        "expiry_date": "2025-12-31",
        "payment_status": "pending",
        "payment_date": None
    })

    # Gọi hàm xử lý thanh toán
    result = process_simulated_payment("5555666677778888", 100.0, ObjectId(), collection="temp_payment_cards")

    assert result["status"] == "failed"
    assert result["message"] == "Tài khoản bị khóa"

def test_process_simulated_payment_card_expired(reset_temp_table):
    # Thêm một thẻ thanh toán giả lập vào bảng tạm
    temp_payment_cards = db.temp_payment_cards
    temp_payment_cards.insert_one({
        "card_number": "9999888877776666",
        "card_holder": "Test User",
        "balance": 1000.0,
        "account_status": "active",
        "expiry_date": "2020-12-31",  # Thẻ đã hết hạn
        "payment_status": "pending",
        "payment_date": None
    })

    # Gọi hàm xử lý thanh toán
    result = process_simulated_payment("9999888877776666", 100.0, ObjectId(), collection="temp_payment_cards")

    assert result["status"] == "failed"
    assert result["message"] == "Thẻ đã hết hạn"