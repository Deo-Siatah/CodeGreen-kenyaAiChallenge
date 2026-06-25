
from pydantic import BaseModel

class SocialGroupCreate(BaseModel):
    name: str

    group_type: str

    location: str

    formation_year: int | None = None

    member_count: int | None = None

    savings_frequency: str | None = None

    average_contribution: float | None = None

    credibility_score: float = 50.0

    status: str = "active"