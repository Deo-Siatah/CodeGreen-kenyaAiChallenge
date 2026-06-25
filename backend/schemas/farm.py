
from pydantic import BaseModel


class FarmCreate(BaseModel):
    acreage: float

    production_type: str

    primary_crop: str | None = None

    secondary_crop: str | None = None

    livestock_type: str | None = None

    livestock_count: int | None = None

    irrigation_available: bool = False

    location: str

    estimated_annual_output: float | None = None

    estimated_annual_revenue: float | None = None