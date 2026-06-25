from pydantic import BaseModel
from datetime import date, datetime


class FarmerCreate(BaseModel):
    full_name: str
    national_id: str | None = None
    phone: str
    gender: str
    date_of_birth: date | None = None
    age: int
    location: str
    village: str | None = None
    sub_county: str | None = None
    county: str | None = None

    farming_type: str
    primary_activity: str

    years_farming: int | None = None

    education_level: str | None = None

    registration_date: datetime

    preferred_language: str = "sw"
    onboarding_channel: str | None = None

    status: str = "active"