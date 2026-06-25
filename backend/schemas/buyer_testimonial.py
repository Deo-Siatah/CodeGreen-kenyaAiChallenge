
from pydantic import BaseModel
from datetime import datetime

class BuyerTestimonialCreate(BaseModel):
    purchase_frequency: str

    years_of_relationship: int

    estimated_volume: float

    reliability_rating: int

    average_transaction_value: float | None = None

    seasonality_pattern: str | None = None

    timestamp: datetime