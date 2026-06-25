from pydantic import BaseModel
class TrustSourceCreate(BaseModel):
    name: str

    category: str

    phone: str | None = None

    national_id: str | None = None

    gender: str | None = None

    location: str

    institution_name: str | None = None

    years_known_farmer: int | None = None

    credibility_score: float = 50.0

    verification_count: int = 0

    successful_verifications: int = 0

    failed_verifications: int = 0

    status: str = "active"