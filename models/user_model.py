from pydantic import BaseModel, EmailStr
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
                }
            }
        }