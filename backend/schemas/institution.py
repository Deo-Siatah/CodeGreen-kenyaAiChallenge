
from pydantic import BaseModel
class InstitutionCreate(BaseModel):
    name: str

    institution_type: str

    registration_number: str | None = None

    location: str

    county: str | None = None

    phone: str | None = None

    email: str | None = None

    established_year: int | None = None

    status: str = "active"