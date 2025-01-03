from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from cryptography.fernet import Fernet

class PaymentModel(BaseModel):
    card_number: str
    card_holder: str
    balance: float
    account_status: str
    expiry_date: datetime
    payment_status: Optional[str] = "pending"
    payment_date: Optional[datetime] = None

    # Thiết lập mã hóa
    _key = Fernet.generate_key()
    _cipher_suite = Fernet(_key)

    def encrypt_card_number(self):
        """Mã hóa số thẻ"""
        self.card_number = self._cipher_suite.encrypt(self.card_number.encode()).decode()

    def decrypt_card_number(self):
        """Giải mã số thẻ"""
        self.card_number = self._cipher_suite.decrypt(self.card_number.encode()).decode()

    class Config:
        schema_extra = {
            "example": {
                "card_number": "4111111111111111",
                "card_holder": "Nguyen Van A",
                "balance": 1000000,
                "account_status": "active",
                "expiry_date": "2025-12-31",
                "payment_status": "pending",
                "payment_date": None
            }
        }
