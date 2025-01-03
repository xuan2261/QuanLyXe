import streamlit as st
import logging
from datetime import datetime
from config import db
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

def process_simulated_payment(card_number, amount, booking_id):
    """Hàm xử lý thanh toán giả lập cho các tình huống khác nhau."""
    payment_cards = db['payment_cards']
    card = payment_cards.find_one({"card_number": card_number})

    # Kiểm tra các điều kiện của thẻ
    if not card:
        logger.error(f"Thanh toán thất bại - Thẻ không tồn tại: {card_number}")
        return {"status": "failed", "message": "Thẻ không tồn tại"}

    if card['account_status'] == 'locked':
        logging.error(f"Thanh toán thất bại - Tài khoản bị khóa: {card_number}")
        return {"status": "failed", "message": "Tài khoản bị khóa"}
    
    try:
        expiry_date = datetime.strptime(card['expiry_date'], "%Y-%m-%d")
    except ValueError:
        logging.error(f"Thanh toán thất bại - Lỗi định dạng ngày hết hạn: {card_number}")
        return {"status": "failed", "message": "Lỗi định dạng ngày hết hạn"}

    if expiry_date < datetime.now():
        logging.error(f"Thanh toán thất bại - Thẻ hết hạn: {card_number}")
        return {"status": "failed", "message": "Thẻ đã hết hạn"}
    
    if card['balance'] < amount:
        logging.error(f"Thanh toán thất bại - Không đủ số dư: {card_number}")
        return {"status": "failed", "message": "Không đủ số dư"}

    # Cập nhật số dư và trạng thái thanh toán
    new_balance = card['balance'] - amount
    payment_cards.update_one({"card_number": card_number}, {"$set": {"balance": new_balance}})
    logger.info(f"Thanh toán thành công: {card_number} - Số dư mới: {new_balance}")

    # Cập nhật trạng thái thanh toán cho đơn đặt xe
    update_payment_status(booking_id, "paid")
    logger.info(f"Trạng thái thanh toán của đơn hàng {booking_id} đã được cập nhật thành công.")

    return {"status": "success", "message": "Thanh toán thành công", "new_balance": new_balance}

def update_payment_status(booking_id, status):
    logger.info(f"Cập nhật trạng thái thanh toán cho booking_id: {booking_id} thành {status}")
    result = db.bookings.update_one({"_id": booking_id}, {"$set": {"payment_status": status}})
    if result.modified_count == 1:
        logger.info(f"Cập nhật thành công.")
    else:
        logger.warning(f"Không tìm thấy đơn đặt xe với booking_id này.")