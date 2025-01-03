from pydantic import BaseModel
from typing import Optional

class VehicleModel(BaseModel):
    brand: str
    model: str
    price_per_day: float
    status: Optional[str] = "available"
    year: Optional[int] = None
    required_license_type: str

    class Config:
        schema_extra = {
            "example": {
                "brand": "Toyota",
                "model": "Camry",
                "license_plate": "ABC123",
                "price_per_day": 50.0,
                "status": "available",
                "year": 2020,
                "required_license_type": "B2"
            }
        }