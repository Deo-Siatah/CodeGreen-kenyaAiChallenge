
from pydantic import BaseModel
from datetime import datetime

class TestimonialCreate(BaseModel):
    rating: int

    comments: str

    confidence_level: int

    relationship_years: int | None = None

    knows_farmer_personally: bool = True

    recommends_credit: bool

    timestamp: datetime