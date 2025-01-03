from pydantic import BaseModel
from datetime import date
from typing import Optional

class BookingModel(BaseModel):
    user_id: str
    vehicle_id: str
    start_date: date
    end_date: date
    total_price: float
    status: Optional[str] = "pending"

    class Config:
        schema_extra = {
            "example": {
                "user_id": "60c74d3f1f4e4b2a1b8e12f9",
                "vehicle_id": "60c74d3f1f4e4b2a1b8e12fa",
                "start_date": "2024-01-01",
                "end_date": "2024-01-05",
                "total_price": 200.0,
                "status": "pending"
            }
        }
