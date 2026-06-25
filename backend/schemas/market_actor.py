
from pydantic import BaseModel


class MarketActorCreate(BaseModel):
    name: str

    actor_type: str

    phone: str | None = None

    location: str

    business_name: str | None = None

    years_in_operation: int | None = None

    credibility_score: float = 50.0

    status: str = "active"