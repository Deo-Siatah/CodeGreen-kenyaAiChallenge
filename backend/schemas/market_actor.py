from pydantic import BaseModel, ConfigDict


class MarketActorCreate(BaseModel):
    """Request body for POST /trust/market-actors.

    business_name, years_in_operation, credibility_score and status had no column
    and now fail with 422 rather than being dropped.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    actor_type: str
    phone: str | None = None
    location: str
