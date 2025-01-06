from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import date

class DriverLicense(BaseModel):
    type: str
    expiry_date: date

    class Config:
        schema_extra = {
            "example": {
                "type": "B2",
                "expiry_date": "2025-12-31"
            }
        }

class UserModel(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: str
    address: Optional[str] = None
    role: Optional[str] = "customer"
    driver_license: Optional[DriverLicense] = None
    two_fa_enabled: Optional[bool] = False  # Thêm trường 2fa_enabled
    two_fa_secret: Optional[str] = None  # Thêm trường 2fa_secret

    class Config:
        schema_extra = {
            "example": {
                "full_name": "Nguyen Van A",
                "email": "nguyenvana@gmail.com",
                "password": "strong_password",
                "phone": "0901234567",
                "address": "123 Nguyen Van Linh, Q7, TP.HCM",
                "role": "customer",
                "driver_license": {
                    "type": "B2",
                    "expiry_date": "2025-12-31"
                },
                "two_fa_enabled": False,
                "two_fa_secret": None
            }
        }
    
    @field_validator('email')
    def email_must_be_unique(cls, v):
        from config import db
        existing_user = db.users.find_one({"email": v})
        if existing_user:
            raise ValueError('Email already exists')
        return v

    @field_validator('phone')
    def phone_must_be_unique(cls, v):
        from config import db
        existing_phone = db.users.find_one({"phone": v})
        if existing_phone:
            raise ValueError('Phone number already exists')
        return v